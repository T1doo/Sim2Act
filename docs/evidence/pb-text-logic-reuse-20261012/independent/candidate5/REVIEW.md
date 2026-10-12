# 候选5独立复验：新版本列表仍读旧Release

独审`/root/text_logic_review`，2026-10-12，基线`e2b856bb453fc74452583fa10843148758e2d9b9`、分支`dev/pb-text-logic-reuse-20261012`的未提交候选5。两轮运行前后都匹配`candidate5-freeze.json`的全部378个src/tests文件，零哈希变化或缺失；精确freeze SHA见各before/after文件及`results-summary.json`。

结论：**需要修复，不能签通过。** 新29项+原独立API9项共38：34 PASS、4 FAIL、exit1，160.55秒；小目录兼容回归2 PASS、exit0，7.84秒。38项的4FAIL全部是正常可见JSDOM冷链；原独立3个单边bool/float污染红例与6个坏授权/双binding seal负例全部PASS。

## 真实剩余缺陷

四个可见场景`valid`、`authorization-lost`、`binding-lost`、`revoked-retained`已经越过候选4失败的冷boot目录，但在打开新app的内部版本目录触发原Release私有单元。`internal_api.py:161`的releases当前先SELECT同project/user全部`internal_releases.id,snapshot`，然后在Python按snapshot.draft.app_id筛选。实际SQL屏障完整错误保留在`new-and-independent.log`/XML：

```text
SELECT private_read_internal_releases.id, private_read_internal_releases.snapshot
FROM private_read_internal_releases
WHERE project_id = ? AND principal_id = ? ORDER BY id
sqlite3.OperationalError: user-defined function raised exception
```

后端未将旧snapshot返回给页面，但实际读取已违反无旧内容合同。不能吞错误、放宽屏障、换扫描方法或用API/Worker绿项替代这四项。此错误是测试屏障主动检测应用读取，不是工具/平台授权拒绝。

## 修复方案静态建议

同意root提出仅为新文本逻辑家族增加独立Release metadata索引、复用graph_requests双seal、不新增表或迁移的方案：

- `commit_release_tx`插入新Release、approval consumed及新index双seal在同项目锁同事务提交；任一失败全回滚。缓存分支只核既有index，不给旧Release补数据或导入旧候选。
- 索引以owner/app/release精确身份保存project、新Release/approval/candidate指纹等metadata，不存snapshot。新家族`read_release`核双seal、闭集和当前candidate/独立logic/目标权限。
- 新家族列表先从已完整验证的draft/独立task marker识别家族，再只取该app索引IDs后严格read_release；先核索引及公开身份范围再读取指定新snapshot。索引缺失/单seal坏/版本冲突拒绝，不能退全项目扫描、旧家族或JSON WHERE过滤旧snapshot。
- 保留普通Release列表兼容；新家族缺marker不得降级。下一候选普通可见四页/整段SQL屏障和index事务/污染负例应独立验证。

## 本候选已修复并验证到的部分

静态确认普通Run metadata模式只SELECT id/status/created_at，固定摘要和mode UNKNOWN，UI冷目录调用新模式；resource目录先读id/name/format并授权后才读取对应hash；app目录还按独立初始literal marker排除CSV Grant hint，避免初始literal额外CSV grant导致冷发现打开旧source。

实际四个UI已穿过这些路径，包括新增原resource内容/hash保留但撤权的场景，并最终在更后的旧Release读取处失败。这说明前段修复已被运行覆盖，但不是四个完整流程PASS。所有API/Worker/真实64上限/expiry最终写回滚与原独立API完整性用例通过。

两个小回归仅执行`test_catalog_instance_routing.py`（默认目录API兼容）及`test_catalog_use_routing_ui.py`（无socket synthesized DOM，24个发现/显式open检查）；两者通过。本轮未扩大其他回归。

## 完整性、失败历史与范围

完整命令/退出结果见`*-command.json`、`*-result.json`；完整原始日志与逐项JUnit见`new-and-independent.log/.xml`及`catalog-small.log/.xml`。每轮1个既有Starlette/httpx deprecation warning。所有测试数据各自/tmp SQLite，真实模型0；上游仅已有MockTransport准备来源fixture，字面Worker NoModel。

独审只写自己的/tmp，没有产品/作者tests修改、push、部署、凭据/权限变更、socket绑定、native、PG/Windows或旧源码升级动作。本轮全部测试/Node/runner已结束，前后378文件一致，已向root明确解除src/tests编辑等待；不再启动候选5动作。

候选3/4的全部红日志和报告原样保留。候选4两个误选socket历史项保持`OUT_OF_SCOPE_EXECUTED_NO_ACCEPTANCE`及真实P/F记录，没有改写为NOT_RUN或计为本轮通过；本候选未重跑或变通。

已取消精确候选安装竞态对照永久NOT_VERIFIED，本轮无执行/实现/替代probe。完整P-A/P-B/AT-10、真实人工语义/owner、原生平台、真实设备崩溃、真实模型/付费、PG/应用角色、全旧源码升级、正式发布/部署及远端CI保持NOT_RUN；owner PENDING、semantic UNKNOWN、LIVE0、formal publication false不变。
