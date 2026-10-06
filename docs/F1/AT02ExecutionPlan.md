# AT-02 执行记录与历史两次 HTTP 准备（2026-10-06）

当前状态：2026-10-06明确授权4次已执行用尽，详见本文末节及[冻结要求逐条核对](AT02Review.md)。以下最多两次方案及PREPARED_OFFLINE / LIVE_BLOCKED为批准前历史，不代表当前仍等待这项预算。

历史准备状态 **PREPARED_OFFLINE / LIVE_BLOCKED**。基线产品b91e4e3（产品源码c16cbae），用户尚未批准父线程申请的新增最多2次 Intern API、每次2048输出token上界、仅合成材料、无自动重试。当前真实请求预算仍 **0**；没有读真实token、请求models或调用官方接口。本轮只创建并删除一份本地test_only双主体fixture/离线公共响应形状回放；不实现新feature、不触发CI、不改冻结[AT-02 V5-1](../../tests/cases/AT-02.json)、V5、历史LIVE/AT02或原AT05。

依据原V5阶段计划§4.1/§11.2、[既有核对及独立结论](AT02Review.md)、[历史42链](../evidence/LIVE-20261005/README.md)。旧dd195681短任务确为两次真实Intern响应、一次resource.read VERIFIED、feedback后答案trim=42、最终PARTIAL/LIVE；初态仅一owner/项目，清理后不能补造双fixture。旧另一数据库FAILED不能和此成功拼成同一完整初态。此次未来执行必须是从初态完整的**新独立数据库、新Run**，历史记录保持原样。

## 两次预算可以和不能覆盖的范围

| 子项 | 最多2次的精确安排 / 判断 |
| --- | --- |
| 完整双主体/项目初态、调用用户/runtime独立、隔离Grant | 在同一个新独立PG数据库预建A/PA/RA与B/PB/RB；两用户和两runtime共4 principals，两个项目/两TXT。先后导出脱敏初态/授权/资源版本hash，不能用别的数据库补齐 |
| A真实目标→工具选择→工具反馈→后续修订 | 请求1：A的`Read; echo.`/唯一资源42；Intern选resource.read。真实既有gateway验证/执行只读工具、独立回读VERIFIED回执。请求2：原assistant+完整tool反馈送回同一InternModel，产生trim=42。未要求先故意答错，按冻结“反馈后的修订”判定 |
| 双向身份/项目/资源/runtime隔离 | 同一fixture内实际API/gateway本地负例，无需模型：B读A资源/Run/历史403；A读B403；在A项目引用B资源提交403；混用RB调用A资源拒绝；用户或runtime任一read Grant撤回拒绝。负例不能产生model attempt或Operation；B自有资源84仍可读且不变；A所有模型发送体不可出现B资源/内容 |
| 两主体各完成一条真实选择+反馈链 | **不够，最少4次HTTP**（每主体两次）。把预算拆成A/B各一次只能证明选择，不能证明任一方收到反馈后修订；不能在一个上下文合并两个项目来假装两条隔离任务。是否要求B也真实闭环需验收方明确；冻结AT02写双初态但未写两条对称LIVE链，不擅加也不擅省 |
| 实际Run结果、usage/model身份/持久化和清理 | 两次都正常且oracle成立时可完整归档单A链 + 同库B隔离观察；F1仍PARTIAL/goal_acceptance NOT_RUN，不改SUCCEEDED。Win11属于AT01；其他任务族/真实材料/发布和广泛语义属于另门，不用本案代替 |

**两次是上限，不是成功承诺**。当前旧公共响应形状序列化恰好1170/1958字符，第二轮距原2000字符上限仅42字符。新的assistant content、tool-call ID、额外工具或参数可能更长；发送前越界时阻止请求2，保留第一次真实请求/失败/未消费反馈，不压缩必要schema/回执、不篡改响应或降低oracle。截断/错误模型/错误工具/授权错误/HTTP错误/timeout/第三轮需求都停止，max_repairs=0，无重试、追加、models探测或自动重新提交Run。未发送预约与真实HTTP/usage分开计；未知usage保留unknown/partial，不能填零。

## 获批准后才可执行的有限协议

1. **准入核对**：父线程保存明确授权、最多2次全局HTTP上界、合成资料范围、输出上界、无自动重试及验收方对“B为同库隔离观察者”的解释。只用获授权的同一provider账号/quota_subject；本地两用户不等于两个API账号，不拆配额绕RPM。没有批准仍0请求。若要求两条对称LIVE链，先回报4次最小需求，不消耗2次去制造半链。
2. **新环境初态**：显式迁移角色建新独立临时PG数据库/表，再分配无SUPERUSER/CREATEDB/CREATEROLE/schema CREATE、仅USAGE+业务表CRUD的应用角色。正常独立API/worker（同现有源码/依赖锁，loopback），不由API建表。仅两owner/两project/两runtime/两TXT，A42/B84，无任意路径。标准资源接收会授予`data.aggregate_csv`；在此授权测试fixture显式撤回多余能力，保留四个活动owner/runtime `resource.read`交集，无artifact写权限。固定ids/hash/Grant revision/expiry、数据库与运行角色权限、创建时间、源码hash、配置白名单在LIVE前保存；凭据和DSN不可进入报告。
3. **零网络本地前置**：同一fixture双向API/gateway拒绝、任一交集撤回拒绝、B自有读取/无串数据、未产生attempt/Operation；撤回负例在回滚TX完成，重新核初态授权完全一致。确认仅A一个新Run QUEUED、B无任务、独立worker只处理该fixture。源42独立hash/oracle冻结。若角色/初态/权限/源码/hash不通过，不启动provider发送。
4. **预算与发送边界**：`max_requests=2,max_tools=1,max_repairs=0,max_output_tokens=512,max_total_tokens=5000,run_seconds<=300`；单个全局发送守卫跨所有Run/错误计数，发送前原子保守占额并记录安全request fingerprint/完整合成体字符及UTF8大小。只允许固定官方chat/completions、intern-s2、stream=false，不查models；不得改正文/响应/TLS/代理。维持原完整体<=2000字符、相邻请求从前个响应结束至少6秒的限制。工具schema/反馈/回执保留全字段。只有已批准才给正常InternModel外部transport；本轮没有生产LIVE执行器或凭据配置。
5. **输出token差异**：拟议2048为用户上界，但当前`Settings.from_env`及Frozen `Limits`均 **<=1024**，旧成功是512；本方案使用更紧的512，保持源码/配置契约不变。不要通过直接dataclass绕冻结Limits或提高平台cap。若用户要求实际设2048，需要另行批准产品限额变更/验证，此准备不实现。离线两预约保守byte-envelope=4206，5000仅安全占额上界，不是provider tokenizer估算；本次0 provider调用，无真实usage账。未来provider返回input/output/total分别记录并检验加法，缺失unknown/partial，不折算费用。
6. **两请求及oracle**：正常API一次接受新intent/冻结合成goal与资源；第一次真实响应只能严格受限调用已授权read。保存RECEIVED attempt/raw/canonical identity、policy版本、usage、耗时/request fingerprint；原gateway持久Operation与真实回读receipt；第二次包含与tool_call_id一致的反馈，最终答案trim=42。请求模型intern-s2，返回只接受已验证intern-s2/Intern-S2及`intern-s2-returned-name.v1`，不能任意casefold或用开发模型。权重版本unknown保持。第二次不能是另一个平台identity/项目；如仍请求工具或第三轮，不把它改作final。
7. **同库终态与冷核对**：独立新Store/连接读取两RECEIVED attempts（或如实失败）、reservations、唯一VERIFIED Operation、events、角色system/user/assistant/tool/assistant、模型身份/真实用量、result receipts/资源hash和答案。导出同库完整脱敏principals/projects/grants/resources初态及终态，A模型body中无B资源；B接口对A history/Run/resource拒绝、B内容84/权限不变。保存所有失败/unknown和未发送账，不补签历史。独立验收者决定AT02子项/完整冻结验收，开发方不预写PASS。
8. **清理与扫描**：先写仅合成/脱敏的repo证据与文件长度SHA manifest（不含配置、请求头、真实token、含密码DSN、私有reasoning）。再停止仅owned API/worker/临时PG，验证PID/loopback端口关闭，清理仅此case数据库/临时目录；不能清理用户数据或其他任务。保存实际cleanup/error；有未知发送用量仍保守占额，不因删DB归零预算。

## 当前离线准备实际结果

[26检查及完整合成trace](../evidence/AT02-budget-preparation-20261006/offline-results.json)：单test_only SQLite独立DB两owner/两project/两runtime/两TXT；四活动read授权交集、八双向HTTP拒绝、foreign-runtime/任一read交集撤回拒绝、A本地真实API→Worker→只读VERIFIED→两MOCK形状→PARTIAL42、B资源84可读不变且无模型体引用、Grant不变、cold Store回读、纯model身份policy与清理通过。无socket/provider transport/真实token读取，`live_enabled=False`、MOCK attempts `NOT_ENFORCED_SYNTHETIC`、usage unknown，不把回放算LIVE。12旧归档长度/SHA全匹配；两发送形状1170/1958字符，reservation envelope4206。该SQLite结果不证明PG CRUD角色/独立进程/真实账号；这些必须在获批准的新PG fixture中真实核对后才可发送。初离线helper错误及修复保留，原文件均未改。

当前最小门槛：用户批准新增预算及发送范围；验收方明确同库B观察是否足以符合冻结条款；新PG/最小应用角色/独立API-worker及硬全局守卫的零发送预检。其余正式F1/Win11/AT02签收维持未完成。

## 2026-10-06 newly authorized dual-owner LIVE execution

The parent relayed explicit user approval of **at most four requests, 512 output tokens each, synthetic-only, no automatic retry**. The earlier zero-budget/offline preparation remains historical; this approval permits one fresh same-DB two-owner/two-project fixture, each a two-request resource.read→feedback→answer chain. See [frozen scope and gates](../evidence/AT02-dual-live-20261006/README.md). Minimum-role PG preflight23PASS and guard MOCK4PASS/0network precede actual sends; persistent global four-send ledger and fail-stop controller prohibit restart/retry. Product/schema/history unchanged. Final outcome remains pending before execution; this is not full F1 signoff.

Execution result: `PASS_BOUNDED_DUAL_LIVE_SLICE`; exactly4 sends, A/A/B/B, each PARTIAL42/84 with two RECEIVED enforced identities and one VERIFIED read. All23 preflight+26 execution assertions passed. Reported input2506/output299/total2805 tokens; unused authorization0. Owned API/workers/PG/temp cleanup confirmed. This does not retrospectively repair historical single-owner evidence or confer formal signoff. Independent final evidence audit follows in the evidence folder; no model calls remain authorized.

Final independent archive audit:58 executed assertions PASS, complete request bytes/hashes and receipt/feedback/source/account/isolation chain consistent; independent network0. This is archive verification, not repeat LIVE or re-query removed PG. Normal Runs still have semantic goal acceptance NOT_RUN; no formal signoff inferred.
