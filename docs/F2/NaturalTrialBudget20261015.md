# 自然试验跨 Run 不可退还总账（工程 primitive）

输入基线 `ce6a0595c47dde0c5561265c3dbfa2ccc9b8721d`；本切片只新增预算模块及测试，不接 HTTP、provider，不调用 Worker transport，不建立可执行 LIVE 批准。7槽提案仅P-A；P-B合成工程不授予真实试验范围。

## 输入和集成合同

`scope_for(contract, approval_key)`从严格 canonical TrialContract 投影真实 trial/project/principal/project-runtime/quota-subject/独立 expiry 与完整合同指纹。这里只保存标识与散列，不存完整材料、Goal、token、秘密或 wire/response 正文。合同必须由 `natural_live_admission` 完整审批；API 用户 `approved/free` bool 或字典不能作为 Permit。

`reserve(store,user,scope,contract,Reservation,admission=...)`在既有 `Store.tx` 中按项目→实际 Run→统一 quota 行锁顺序，调用安装在控制器内的准入依赖，核真实 Run version/fence/lease/status/cancel-intent 与原创建时间≤300秒。Permit 必须精确匹配合同、阶段、Run、version、fence、runtime 与 expiry；Generate runtime 等于项目 runtime，Source/Cold 的真实 app runtime 与明确阶段审批指纹由 admission 校验后提供。默认无 admission 拒绝。当前仅 test-only SQLite 和 `SYNTHETIC_ONLY/live_allowed=false` 可进入，生产 LIVE 一律拒绝。

同事务使用 `delivery_graph_requests` 原表的独立 paired ledger，不增加 schema。Generate 3、Source 2、Cold 2，合计最多7；每阶段首次合法 Run 绑定后不能换 Run，三个阶段不能共用 Run。每次完整 wire≤32768 bytes 加1024输出额度计入不可退款预留，每 Run≤64000、跨 Run≤192000。模型输出≤1024/次、总输出≤7168、归档 ASCII response≤32768。原契约固定 lease30、Run≤300秒、独立不可延期 expiry、paid cap0，不借用未用阶段槽。

统一 quota_subject 散列索引行以原表唯一键创建，SQLite/PG 的 dialect insert-on-conflict 不覆盖旧状态；transaction 内锁 paired 行串行化跨项目、跨 trial 的账户≤1请求/分钟。拒绝回滚包括新 quota 行，禁止 partial ledger。PG 路径未经实际验证。quota_subject 真实性必须由 server admission/fee authority绑定；用户字符串不证明免费。

`settle`精确原 request key 记录真实 response hash/ASCII长度及 known 或 unknown usage。取消、撤权、过期、version/fence变化、超量、unknown 之后仍保留已扣槽与真实数值；accepted=false 并停止后续 reservation。未知总用量为 null，绝不当0；known_total_tokens仅表示已经收到的已知分量。迟到回执不能成为保存授权。相同 settlement 重复读取；唯一可变更路径是原slot、同response hash和bytes、原已知分量逐个相等的 UNKNOWN→KNOWN。账本保存 initial/current 两条完整 settlement history，accepted 永远false、halt 永远true，无新slot或发送。冲突hash/bytes/已知分量拒绝无部分修改。未知公开状态优先 RECONCILING，halt字段独立保留；已核known后状态HALTED。没有 transport、retry、refund、删除、重新初始化或发放发送许可。

`read`只在原项目 owner/runtime 与原 scope 下读取账本历史，无新扣额、不发请求。顶层 `dispatch_authorized=false`、`live_admission=NOT_VERIFIED` 始终成立。controller必须另外保护原 Run/资源的读取权限。新 trial 必须明确新 key 与新批准，不能继承或扩大旧批准。

集成依赖：root 同时集成 admission 与 budget；真实 AppRun 的 StageApprove 和 Permit.runtime_id/stage_authority_fingerprint；发送前**重新**完整准入并消费 fresh Run fence/version，不能把 reserve 返回值当发送授权。Permit截止必须finite、当前未过期且≤原trial expiry，admission给出的min(trial expiry,Run原300s截止)合法，预算仍核原Run deadline和lease。公开 `audit(store,c,user,scope)` 在调用者既有事务内只读paired账本；admission阶段审批要证明原Generate的三条真实attempt（reservation.request_key=attempt.id）、wire/raw hash、bytes、known usage与实际完整model_source都一致，缺ledger或unbound accounting不授予phase。发送/保存时实际 wire 与 response 上限及 ASCII序列化必须由受信 transport hook 检查，本 primitive只接收已量测的长度与散列。未知发送结果仅原 key GET恢复。免费账户权益及强制零收费仍 NOT_VERIFIED；真实模型不执行。

## 实际证据和保留失败

证据仅新目录 `/workspace/natural-trial-budget-evidence-20261015/author`，每次命令完整stdout/stderr/XML及执行源码bytes、before/after散列均保留。共享venv只读，独立 SQLite fixture，未安装依赖、未改 credentials/network、安全权限或原 Run/lease时钟。

- `first`：17 PASS，1 deselected；当时源码的短套件。
- `final-short`：21 PASS、1 FAIL、1 deselected。失败为新合成两槽上限夹具把旧 settlement.request_key复制到第二槽，账本正确拒绝。改夹具精确原槽key。
- `final-seven`：1 FAIL、22 deselected。失败为合成claimant为synthetic-worker而heartbeat误用worker-generate，既有ownership fencing正确拒绝。终态已在拟SIGINT检查前结束，未发送信号、未中断或延长任何lease。
- `corrected-short`：22 PASS、0 FAIL、1 deselected，执行源码before/after相同。新增两Store实际并发、原key幂等和冷读取、拒绝不同fp、真实Run version/fence/取消、准入拒绝、expiry后迟到用量、unknown和超量、不退款、跨trial账户限速、严格固定caps、篡改pair、不授权boolean/字典、不同阶段不能共Run。64000 cap边界使用明确owned synthetic history，未伪称实际7槽大wire发送。
- `corrected-seven`：1 PASS、22 deselected，约364.2秒实际终态。合成实际Store.submit/claim三个Run，每次真实60.05秒间隔，既有真实claimant的30秒普通heartbeat，原Run创建时间+300秒deadline不变；对7次实际 reservation/settlement和每阶段第cap+1拒绝核对。无provider或外网请求。该结果是旧冻结module `ffa5bafe74127b1d468a2d1b1c8c622a819c178104914ff34dcc951bc1973dc0`，不充当新模块完整28用例通过。
- `recovery-combination`：26 PASS、1 FAIL、1 deselected。真实Worker.reserve组合未注入显式MockTransport，被既有零LIVE allowance拒绝；完整失败保留，测试补never_send断言型MockTransport，实际调用0，不放宽任何产品门。
- `corrected-combination`：27 PASS、0 FAIL、1 deselected，最新module `b372708a3da4c0f8176189f8bf7f8de5cef0deee851b5c392b37cfd4df1e56ce`、tests `27ca25b48c358319035da4e09181c7b24ed59071ececf89651f4197a86e28935`，before/after相同。包含严格核账恢复和3种冲突拒绝；组合使用真实审批Goal-card Generate Run、actual Worker.reserve/GA_WIRE_RESERVED、实际admission的有限min expiry Permit，不自造Permit。原Run取消后settle保持真实合成用量、无accepted。Worker transport调用0。已封存外部admission module及helper实际origin/import路径、bytes和hash，root最终集成后还需同一闭包复验含7槽，不能把旧1 PASS+新27 PASS宣称同源码28全绿。
- `final-combination`：测试局部imports-only Ruff排序后实际27 PASS、0 FAIL、0 ERROR、0 SKIP、1 deselected；module仍 `b372708a3da4c0f8176189f8bf7f8de5cef0deee851b5c392b37cfd4df1e56ce`、最终tests `5ea3ec7017136c55207e3fbf31dafd788ab55d3a42dafcb5dd7af3a55c79b798`。约38秒，source before/after相同。最终28用例统一源码验收仍由root执行，不拿不同源码的七槽结果补全。

新模块与新测试 Ruff 实际 PASS。live_gates_review只读独审无P1：`/workspace/natural-live-gates-review-20261015/BUDGET_FINAL.md`，报告SHA `af89e9aa655bf9de452ee13568a60b4a1409b295831acbc4686542d0034eb4dc`，manifest SHA `9e5c54c08863ff9e63a75ca72144a72e7e328716a3a7cba8cf54ff44c0921599`。独审没有运行测试，root仍须统一闭包集成验收；不把本报告当独立审查结论。

NOT RUN：PG、Windows、原生浏览器、Worker真实transport、真实/付费模型、账户免费权益证明、人工语义验收、完整P-A/P-B、部署、远端CI。合成预算PASS不等于LIVE门、正式参赛项目或语义验收PASS。
