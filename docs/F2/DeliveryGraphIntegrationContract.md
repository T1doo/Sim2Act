# DeliveryGraph 服务接线合同

这是独立集成支持，不是产品 API 或 UI 实现。核心基线 `e66a437be14d40ff7ad70bad2a96e30a1d3db572`；同时整合核心修复 `0836bf7518e4e175d228bd5c0be28fae8ac83463`，详见 [历史回执类型修复](DeliveryGraphReceiptTypeFix.md)。新增辅助器只操作受信任本地测试 driver 及合成 fixture；不建数据库、不调用模型、不改 API/UI/Store。

## 必须遵守的调用顺序

1. 从当前服务端会话解析 principal，严格校验项目、应用、请求字段和归属。`project_id/app_id` 由服务端授权，不接受客户端上下文、历史回执或 authorized 声明。授权到确切操作与全部资源；登录成功本身不够。
2. 在一致快照中读取 FrozenGoalSpec 全部内容、确切 manifest/actions、资源版本、工具/提示/检查实现源码或不可变发布内容、锁及实际依赖。版本指纹必须由这些内容生成；协调更改标签不能替代实现/内容绑定。正整数使用严格类型，true/false 不能充当 1/0。
3. 派生并持久化不可变 graph、服务端 graph_fingerprint 锚及依赖快照。客户端 expected_graph_fingerprint 仅用于并发条件，不能替代可信锚。人工锁、身份和项目归属不能靠公开哈希自证。
4. 从服务端加载 `(principal_id, project_id, app_id, request_key)` 账本；调用 `plan_change(saved_graph, expected_anchor, closed_request, current_context, stored_core_receipt)`。**重放也先检查当前权限、资源、版本、依赖和锁**，禁止直接返回缓存回执。
5. 根据 NODES/APP/PROJECT 扩验：PROJECT 必须枚举当前项目全部相关应用的可信图和检查，核对每个应用的权限、图锚与人工锁。禁止只验目标应用、过滤未授权应用后声称完整、包含其它项目或用 node_id 单独混合不同应用。至少按 `(project_id, app_id, node_id)` 定位。
6. 保存完整外层回执：核心回执 + 扩验应用集合、每个图锚、授权 revision、锁快照 + 集合快照指纹 + 外层指纹。比较回执用类型敏感规范 JSON，不能用 Python dict 相等。集合成员变化、相关应用撤权/版本/锁变化须使旧外层回执失效。哈希完整性不能替代可信服务端来源。
7. 并发控制以事务/锁/CAS 等保证读取、扩验、账本保存的同一状态；提交或返回前复核权限与快照，任一步失败既不改业务数据，也不新增或覆写任何账本行。相同键不同参数冲突；成功重放不得增加账本行。
8. 后续 patch/验收/发布另行重验当前授权、全部图锚/成员、检查与锁。plan 的 patch_executed/business_write_performed/publishable 均为 false，不授予执行或发布资格。UI 接受响应前比对当前选中项目/应用与请求 generation；旧导航响应不能填入新项目画布，也不能自动重发写请求。

步骤 2/3/5/6/7 是服务端责任。单应用纯模块不能枚举另一个应用、证明 DB 持久性、绑定未提供的源码内容或防止一个不可信调用方同时伪造 graph/context/anchor。

## 可执行黑盒辅助器

`tests/delivery_graph_adapter_contract.py --driver MODULE:FACTORY`。factory(scenario) 返回隔离合成 driver。对真实服务写薄适配器，将 API 响应正规化即可；测试 fixture 控制必须与公开请求通道分开，不能暴露给产品客户端。MODULE:FACTORY 为受信任本地 Python 代码，此工具不是代码沙箱。

Driver 方法：

- `info`：project_id、app_id、related_app_id、foreign_project_id、request、alternate_changes；全部为合成公开身份/条件。request 闭合字段为 project_id、app_id、request_key、changes、expected_graph_fingerprint。
- `plan(body)`：成功 `{status:200,data:{core,expansion,outer_fingerprint}}`；拒绝 `{status:400|403|409,error:CODE}`，无 data。
- `observe()`：domain_fingerprint、receipt_count、ledger_fingerprint；后者覆盖账本**全部内容**，防计数不变的覆写漏检。不得返回原始秘密/业务内容。快照必须独立可比较。
- `transition(event)`：测试控制撤权、版本变更、相关应用锁/成员变化及持久回执篡改。scenario 为 normal/project/target_locked/project_locked；事件见 CASES。
- `cold()`：从已提交状态建立新的 client/session/storage reader，验证重放；真实适配器应使用真实持久层与冷启动能力。`close()` 清理隔离合成 fixture。

外层 expansion 的闭合字段：scope、applications、snapshot_fingerprint。applications 按 app_id 排序且不重复，每项闭合字段 project_id、app_id、graph_fingerprint、authorization_revision（严格正整数）、locked_nodes。snapshot_fingerprint 为规范 JSON applications SHA-256；outer_fingerprint 为 data 去掉 outer_fingerprint 的规范 JSON SHA-256。规范编码：sort_keys=True、separators=(",",":"), ensure_ascii=False, allow_nan=False, UTF-8。这是**测试正规化格式**，不要求主线原生 wire schema 同名。

运行参考 double：

```bash
PYTHONPATH=src:tests python tests/delivery_graph_adapter_contract.py --driver test_delivery_graph_adapter_contract:MemoryDriver
python -m pytest -q tests/test_delivery_graph_adapter_contract.py
```

替换为真实 driver 后同一 runner 验证服务边界。报告只含案例名、PASS/FAIL、异常类型，不输出异常消息；CLI 导入错误也固定 JSON 脱敏。MemoryDriver 的 cold 只是 JSON 重建内存状态，不是 DB/进程重启。`check_selection_response` 是独立 UI oracle，只有实际 UI 被驱动并比对才构成 UI 证据。报告 product_acceptance 固定 NOT_IMPLIED，不能拿参考 double PASS 宣称产品接受。


17 个场景覆盖冷重放、同键异参、项目切换、客户端权限注入、主应用撤权/版本变化、目标锁、PROJECT 完整枚举、相关应用初始锁及撤权/版本/成员/锁变化、协调截断与重签外层回执、协调重签后的核心/外层类型篡改、持久图 bool revision。这里只验证计划是否正确拒绝/扩验并保存完整回执，不执行检查器或补丁。并发竞态、跨 principal 同键、真实源码/目标内容绑定还需产品专属集成测试，本辅助器不声称覆盖。
