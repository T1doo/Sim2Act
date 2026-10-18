# 生产策略内核有限独审结论

**有限通过；当前未发现阻止普通开发分支交付的确定 P1/P2。** 生产冻结 `c62bfb90d23234c6ce56c78bf6c441d6ca1a7703`；最终测试冻结 `20a43aba27e6276046cd9ae25ac090f02bff89ba`。后者仅补强取消测试函数，全部 135 个生产输入逐字一致。最终资格为 18 个未改变节点的首轮结果，加补强取消节点；19 unique、20 executions、20 PASS、0 FAIL，不能称最终测试 SHA 全套重新运行。

我只做非作者源码静审和纯文件/Git 核验，没有亲跑产品/pytest/HTTP/Worker/model，没有 SQL 或数据库打开/重算，也未联网、写仓库或修改作者封存目录。自己的两份纯文件 audit 脚本实际 exit0，stdout/stderr、结构化 verification 均在本目录。

## 代码和历史发现

最小产品变化是 `natural_live_admission.py` 提取原 Run/phase/approval/frozen-generation 校验，及未安装 `production_trial_policy.py`。旧 admit 顺序、exact SyntheticOnly/test_only SQLite 门及原 Permit 保持；新 kernel 复用固定 caps、原身份、canonical account quota 和纯用量规则，不改旧 budget._active/存储算法。新 reserve/record_attempt 在 caller TX 重新检查真实当前上下文；settle 保留原正确 usage，当前失效只降 accepted/halt。Transition 恒 UNINSTALLED_POLICY_ONLY/live=false/dispatch=false/real_source_verified=false。生产 API/Worker 无 import 安装，未新增 source/issuer/有效 LIVE Permit/sender、Grant、executor 或持久化 namespace。

WIP P2 原件保留：恢复入口曾接受多个未决槽和同秒历史。最终源码增加非末槽必须 accepted、相邻 reserved_at≥60；负测分开 prefix 与同秒 RPM。冻结前另纠正精确 GRANT_REVOKED oracle。上述为静审发现/修复，不冒称已运行旧错误源码。随后父级发现首轮取消测试的未 attempted 槽不能单独证明 fresh cancel 拒收，故仅补强该测试：先 marked，再取消后 settle；原首轮 19 PASS 原件保留。没有产品源码修正或重跑其它 18 节点。

## 独立核对的闭合原件

- 首轮作者目录 `/workspace/production-policy-kernel-20261018`：封存 manifest SHA `92928b53e06c1b4fc12c0b8cdb584f314a1b4cbaa587a73643dfc6460c91fe79`；36 个非 DB 路径、983794 bytes 全 SHA/size 匹配；19 个物理 fixture DB 仅 stat。JUnit/stdout 19 named unique PASS，0 failure/error/skipped，JUnit 51.382s、外层 54.792128842s。7 新 policy 节点 + 12 原 context 节点。
- 补强目录 `/workspace/production-policy-kernel-followup-20261018`：manifest SHA `f73291ab1749d7e98d90ec08f93bdf4745010e35a48636ad84330ef2ead803c8`；19 个非 DB 路径、316310 bytes 全 SHA/size 匹配；1 个 fixture DB 仅 stat。取消单节点 PASS，JUnit 3.145s、外层 5.68968525s；新回执 attempted=true、accepted=false、halt=true、usage total=8，quota/原槽保留。
- 两轮各 701 执行输入前后相同、各 135 生产输入；全部输入核到各自 Git blob。两轮差异仅测试文件，AST 仅取消函数；runner/guard before/after 及封存副本 bytes/hash 一致，3 份首轮 frozen-source 与 Git 相同。13 个保护文件（原 budget/API/Worker/production resolver/model/runtime/dispatch/archives/Goal/P-B source/两资格 anchors）与输入基线 `842a5b46d52131581edcbfa235ef067cc44b809b` 全字节相同；生产 Python AST 无新 kernel importer。
- 首轮 46、补强 5 个操作窗口，各 55 表的 before/after FP 相等。测试代码实际执行 strict full-row equality，原件只保存 rowcounts/FP/执行断言；我独立复算的是这些保存字段，**没有凭 FP 重算原 55 表数据**。首轮取消窗口与补强窗口分别保留，不能作为新增 unique case。
- guard 所监控的 HTTPTransport、Settings.from_env 和 InternModel 请求入口 attempts=[]；测试选择及源码无模型/Worker调用。合成 SourceVerificationResult、wire 和 usage 为明确测试输入；AttemptID 仅内核 reservation 身份，不是实际模型 Attempt 记录。

## 保留范围

内核未 durable 安装、无全局 DB/CAS/RPM 并发资格；JSON roundtrip 仅可序列化。当前无可信真实来源 producer/免费权益/强制不收费证据、有效 LIVE 许可或 sender；resolver 仍 NoReturn 拒绝。现合同仍锁旧 intern-s2/chat endpoint，官方/赛事截图不补 source proof；未来合法新渠道需新合同和独审。没有把 30 秒工程诊断上限转成 provider 续签要求。

真实模型/费用/人工语义、Windows、PostgreSQL、远端 CI、完整 UI/P-A/P-B、旧取消安装窗口和 durable controller 均未执行或安装。本结论不背书未来 push/部署，也不称整体 F2 或生产 LIVE 通过。此次未重跑任何旧长链、未扩大矩阵或旧归档。

本目录保留早期工具定位错误来源说明（见 design-review.md），没有将缺失路径/权限拒绝或静态发现计作 pytest FAIL。两次独立纯文件 audit 均一次完成，无新增解析失败。封存后停止本目录全部写入。
