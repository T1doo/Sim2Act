# 通用协议 Store / HTTP / worker 离线闭环

此阶段从本地 `7beb20d` 实施；只本地交付。实际认证 HTTP → 持久 source Run → Worker/InternModel MockTransport → 真实授权 resource.read/VERIFIED Operation → 待验结果 → 注册独立语义 checker → source proof → 模型 extraction receipt → 有限声明式计划 → 新材料 cold Run → 新待验结果 → 独立 proof 已接通。技术完成先 WAITING_APPROVAL/UNKNOWN；只有四个冻结合成包的精确 JSON oracle 检查通过才提升新协议 Run。原 F1 PARTIAL/FAILED/UNKNOWN 历史不修改、不作为成功来源。

注册 oracle 的 gold/rubric 在独立评估资产中，模型请求只含公开目标/schema/已授权材料；客户不能提交 candidate、gold、Replay、PASS 或改验收标准。owner 只有发起检查权。候选绑定实际响应、Attempt、版本、当前授权和参数范围；冷运行编译步骤绑定独立 Operation 身份。该内部计划并非正式 CSV AppManifest/Release，未增加前端或正式发布。

## 实现与审查

事前范围见 [ProtocolStoreLoopPlan](../../F2/ProtocolStoreLoopPlan.md)，HTTP 接线见 [契约](../../F2/ProtocolHttpWorkerContract.md)。新增 protocol_jobs/protocol_reviews 仅原 controller 显式 migration 建表；API construction 不建表，业务角色 CRUD 已另测且 DDL 拒绝。未新增产品身份、权限或部署。

独立审查真实发现并修复：Operation tool_ref/receipt 检查及身份篡改；通用 Run GET 绕过协议核验；持久 review 的 bool/int/额外字段；cold 实际响应与 frozen result 不一致；cold 调用 ID 与步骤失联；有 STARTED 未知 Attempt 时二次取消错误变 CANCELLED。修前事实保留在独立报告，不将这些缺口抹成原本通过。修后完成独立 13 个拒绝负例和永久产品回归。另有开发中 GoalSpec literal、review tuple 解包及两项 pytest 错误消息 regex 失败，修后实际复验；首次系统 Python 缺 SQLAlchemy 为环境失败，改用既有 venv。初次格式检查发现 import 及既有未格式化文件；仅当前修改文件格式化。

## 实际边界

Provider 接线严格 test-only + httpx.MockTransport；默认缺 provider 等待资源，LIVE 明确拒绝。固定测试响应证明工程接线；有限合成 oracle PASS 不证明真实模型规划、一般自然语言语义或材料外泛化。实际外部模型请求为 0，当前批准真实预算为 0，费用未发生。本轮 Windows/原生浏览器/CI 未运行，未 push。

每 job scope 的文件预算与 DB Attempt 双账先写后发；STARTED/未知不自动重试或恢复。跨三个 job 共用 14 次/64k 总预算尚未集成，完整持久 continuation 未实现，均是未来 LIVE 的前置。不能将旧独立预算单测冒充该集成。未测全部 DBA 同时改全部可信记录的攻击；当前核验检测受测持久字段/事件/回执篡改及权限撤回。

完整结果、代码 SHA 和 owned PG 清理见 result.json；独立最终审查另存 independent-review.json。此前原生 CSV 切片及其 CI 成果独立保留，不能替代本轮 browser 或 LIVE 验收。


最终 root 完整 SQLite 为 **704 PASS / 26 SKIP / 1 FAIL**（325.10s），失败为旧 registered-generation actual HTTP DOM 冷运行 helper 最终读 engineering.run.id / instance.id 时 null（日志不足判定具体对象）。独立单测复跑 **1 PASS**（26.99s），未改 UI/DOM 测试或伪称根因已确认；原失败日志保存、完整回归 NOT_ACCEPTED，待后续定位。PG 专项 **131 PASS**（92.90s）含两表显式迁移/受限CRUD与原F1，非完整PG全套。Ruff全src/tests、修改文件format、mypy29、diff均PASS；独立格式化后52PASS+F1 61PASS且hash不变。该未闭合旧DOM失败是交付明确边界，单项重跑不覆盖它。

临时真实HTTP诊断保留正常poll，只hold两个实际回执顺序，确实观察到manual refresh返回时run/instance同时null、释放实例回执后原IID/RID恢复SUCCEEDED（exit0，owned server/Node已清理）。这是受控注入时序的可行性证据，不能倒推完整测试原失败原因；旧产品/UI/harness未修改，原完整NOT_ACCEPTED保留。见dom-injected-timing-diagnostic.txt。
