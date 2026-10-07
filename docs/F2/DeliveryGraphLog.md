# DeliveryGraph 核心切片 Log

2026-10-07，基线 `e700db211378e67ca99529f4a5270f0ea6162769`，独立 `dev/delivery-graph-core`。保留安装分支及已发布提交；没有再次推安装分支。实现和测试契约见 [Plan](DeliveryGraphPlan.md)，原 V5 总设计/阶段 Plan/Log 均不改。

## 实际实现

只新增 `src/sim2act/delivery_graph.py`、`tests/test_delivery_graph.py`、本线 Plan/Log。既有 contracts、preflight、API、worker/runner、数据库、权限、UI、CI、安装说明及工具零差异。

两个接口均为纯函数：现有严格 AppManifest/ActionSpec preflight 后派生图；从当前服务端授权/版本锚规划影响及回执。稳定 ID 由服务端映射提供，内容指纹包含相关上游版本及证据；没有随机重发 ID。CHECK 实现版本与待重验检查区分为 REQUIREMENT/CHECK，声明、实际读取、人工确认、模型候选证据保留来源；声明不被当作实际读取或完备依赖。

规划保存原图和原内容，返回确定/不确定影响、检查和包装失效、原样保留对象、全局不变量及请求/计划指纹。SEMANTIC/模型候选影响不确定；未知读取在没有声明路径时也扩验 APP/PROJECT。整体 MANIFEST/RELEASE 变更扩验 APP，不接受调用者自行声称“仅展示”。影响集命中人工锁返回 LOCK_CONFLICT，未执行任何修改。

回执同键同参复用仍需当前图锚、授权代次、资源范围、节点和外部版本、锁与完整计划逐字段一致。协调改写图/节点并重新计算公开哈希不能替换服务端保存的原始图锚。纯函数没有存储：主线需提供先前回执并序列化持久幂等账本；未提供回执不能检测已用键。

## 发现与修复（保留首发现）

1. 独立复现合法 `ActionSpec.dependencies` 的 check 类型不在 postcheck 时，首版图静默遗漏该版本依赖。修复为所有 checker lock 显式派生 REQUIREMENT/CHECK 及版本/传播关系，永久负例 `test_additional_check_dependency_and_unused_locked_resource_are_not_silently_lost`。所有锁定资源也纳入当前授权/版本范围，不默默忽略。
2. 独立复现 manifest 为 None/list/int 或 actions 为 None/int 时抛裸 AttributeError/TypeError。修为闭合容器入口校验，固定 DomainError，参数化永久负例覆盖。
3. 首修后独立复现既有 preflight 接受未锁定的独立 validation_suite_ref；构图缺 checker REQUIREMENT 而抛裸 KeyError。明确要求全部 checker 有版本锁，缺失返回 INVALID_MANIFEST，永久负例 `test_manifest_suite_requires_explicit_checker_version_lock`。这是图接口的具体收紧，不私改既有 schema/preflight。
4. 本线补充 optional VIEW 没有产物 producer、重复 VIEW 逻辑键的拒绝，避免裸引用错误或合并不同对象。永久负例各一项，Plan 明示这个基线差异。
5. 首次 Mypy 报 5 个局部空集合缺类型注解，补齐后整个 src 检查通过；未改业务逻辑或放宽配置。

首版 77 PASS 不能覆盖以上后续独审发现，最终结果以下述新源为准。不以旧通过数推断漏洞不存在。

## 最终验证与实际用户价值

环境：Linux x86_64、Python 3.12.14，隔离依赖环境 `/workspace/Sim2Act-core-test-env`；显式 `PYTHONPATH=/workspace/Sim2Act/src`，实际 `sim2act.delivery_graph.__file__` 核实为本实现树。31 项 Linux lock 精确包版本已核实，未修改共享 editable 环境或项目依赖锁。

```bash
PYTHONPATH=/workspace/Sim2Act/src /workspace/Sim2Act-core-test-env/bin/python -m pytest -q -p no:cacheprovider tests/test_delivery_graph.py tests/test_contract_semantics.py tests/test_model_protocol.py
/workspace/Sim2Act-core-test-env/bin/python -m ruff check src tests/test_delivery_graph.py
PYTHONPATH=/workspace/Sim2Act/src /workspace/Sim2Act-core-test-env/bin/python -m mypy src
```

最终相关回归 **144 PASS、0 FAIL、0 SKIP、0.60 秒**，其中图专项 83 项、既有契约/模型协议 61 项；1 项既有 Starlette/httpx 弃用警告。Ruff 全 src 与图专项 PASS，Mypy **38 source files** PASS，Git diff whitespace PASS。未扩装依赖或为该警告更改 lock。

独立审查原 77 项、修复后 81 项各实际复跑通过；最终两项 VIEW 负例独立复核 2 PASS/81 DESELECTED/0.03 秒，源码 SHA256 精确匹配；没有新增阻塞。三项独立发现均已修复并有永久覆盖。测试采用真实 CSV 构造器、真实 bounded-agent 清单构造器及手绘双分支 oracle；agent 构造器只生成合成清单，不执行旧测试服务或模型。derive 内置禁止 network/Popen/Store/工具读取派发陷阱未触发；本片没有数据库、网络或模型调用。

实际合成规划示例：左侧 source → left action → left artifact/view → 关联 CHECK → MANIFEST，六个对象受影响；右侧 source/action/artifact/view、目标及工具/checker 实现定义七个对象的 ID、revision、definition、锁和内容指纹原样保留。返回一个明确的重验 CHECK 与失效 MANIFEST，没有执行补丁。完整合成图/回执/摘要已实际生成于本机 `/tmp/sim2act-delivery-graph-demo.json`，临时路径不作为仓库永久验收资产；同一独立 oracle 保存在测试中可复现。

源码 SHA256：`30f40df236697ec129230921a67974706fe67328c202c99baa797387cafbc67a`。最终测试 SHA256：`ff539cab200d19073bd653a2b2b11285168907f79d620d7fa47fc9151535b786`。这里只记录提交前实际事实；精确 commit 和远端普通 push 结果由最终 git 回执提供。

## 主线整合与限制

主线可 cherry-pick 本独立提交；四个文件全部新增，无共享入口冲突。主线负责从真实存储建立稳定 ID/版本/锁映射，对精确 manifest 的权限交集和全部外部快照归属做当前授权检查，保存不可变图锚、回执账本及请求键并发处理。PROJECT 扩验须进一步收集该项目其它应用的图/检查，本单应用返回值不声称已经枚举或执行这些检查。

本图不会核验普通 F1/PREVIEW 来源是否真实成功，不替代现有来源 proof/当前授权网关，不提升 `NOT_ACCEPTED`、semantic UNKNOWN 或 owner PENDING；相关声明只保留为清单定义。ARTIFACT/VIEW 是逻辑产物定义，不冒称已存在业务成果；不生成 Release 或变更正式发布指针。

没有实际补丁、业务写、发布、迁移、收费模型或外部材料发送；没有 Windows CI 竞争，现有 workflow 只监听 `dev/f1-foundation`。真实 Win11/PG/browser/完整产品回归、主线接口适配、项目扩验执行、通用增量修改与 V5 签收 **NOT_RUN**。人工锁及身份关系不能仅靠公开哈希证明，必须使用服务端可信上下文；客户端自报 authorized、版本或 graph_fingerprint 不具有授权效力。
