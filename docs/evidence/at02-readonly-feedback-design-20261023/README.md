# AT-02 最小真实只读工具反馈子链：待审设计

基线 `1ac06f565441c1c308e4c74767b3243340bf0abe`。本轮只冻结设计、合成材料和原工具schema，
**真实请求0，当前执行授权0**。已结束的3请求探针窗口不复用；它实际只用1次，余量不转移。
本设计对应 V5阶段计划 AT-02 的“真实书生选工具、收到反馈并修订”子链；不改冻结AT-02，
不声称完整双主体/PG/Run/Operation/Windows验收，也不重复连通性或G0。
2026-10-06的双主体真实反馈链已在AT02Review/AcceptanceMatrix/Log认账，本次是当前基线的
窄只读网关复核设计，不声称发现必须追加真实调用才能补齐的历史AT-02缺口。

## 固定输入与边界

- 原端点 `https://chat.intern-ai.org.cn/api/v1/chat/completions`，模型 `intern-s2`。
  仅使用现有环境配置的同一凭据及原优先级，不探测models、不切换模型/端点、不付费回退。
- 费用依据保留 `USER_CONFIRMED_NO_COST_NOT_OFFICIAL_VERIFICATION`。
  不把用户确认转换为官方账户事实，不调用或修改生产resolver/admission。
- 材料是本目录固定12字节 `S2A-RO-2947\n`；原字节及SHA见 `contract.json`。
  首次模型请求仅给合成resource_id和目标，**不包含材料正文或预期答案**。
- 唯一工具schema逐字段来自当前 `tools.definitions()` 的 `resource.read` 条目，见原JSON。
  不提供其他工具，`tool_choice`保持默认auto，不伪造模型选择，不强制已写好的tool call。
  不向模型开放路径、SQL、模块、URL、代码、注册器或用户输入的回调。
- 原system prompt及唯一user模板冻结在 `contract.json`。只有准备库的原resource_id可以替换占位符；
  实现与准备完成后还须冻结最终fixture、具体messages/body及执行源码，设计包不冒充这份最终冻结。

## 准备与真正只读的执行

后续实现先在离线准备阶段建立一份自有、隔离、test_only合成SQLite数据源：一个合成用户、
项目和独立runtime、一个TXT资源、仅该resource.read的两主体交集授权。不得调用实际业务API，
不创建Run/Attempt/Operation/App或真实账户/权限。合成fixture初始化会有DDL/测试数据DML，
必须单列为离线准备，不能算成网络执行零写入；本轮尚未创建该fixture。
允许的准备数据严格为 `principals` 2行（user及项目runtime）、`projects` 1行、`resources` 1行、
`grants` 2行（user/runtime各一条resource.read），以及 `Store.initialize` 创建的 `quotas` 1行；
其他业务表0行。仅初始化当前完整schema，不改schema或创建数据库角色/权限。
`Store.resource` 会自动授予aggregate_csv，不能使用它后删除额外Grant来声称从未扩大授权；
必须显式插入固定合成resource行并通过原add_grants只建立两条read授权。

准备结束后关闭写连接，冻结文件SHA、完整表向量、resource_id、正文hash、用户/runtime/project
和原始授权期限，不人为延长过期fixture。网络执行仅以SQLite `mode=ro` 加连接 `query_only=ON`
打开该冻结文件。使用原 `Store` 的engine读连接，**不用会BEGIN IMMEDIATE的Store.tx()**。
封存前用自有准备连接完成checkpoint并关闭全部写连接，确保没有未合并WAL；冻结DB及
`-wal/-shm/-journal`的精确存在性/字节清单。执行时出现新sidecar或任何变更均停止。
写SQL/ATTACH拒绝必须在任何读取或HTTP之前装好，而非只看事后统计；
每次检查退出读连接后才HTTP，不复用旧事务快照。
只调用原 `tools.authorized_read(store,c,principal,runtime,project_id,"resource.read",args)`，
保留原 `Store.authorize` 当前项目/资源/两主体授权及期限检查和 `read_data` 原内容hash检查。
连接初始化仅允许query_only=ON及其状态读取，其余变更PRAGMA、任何DML/DDL/ATTACH均拒绝。
SQL观测只记录语句类别和摘要，执行前后fixture DB、sidecar及材料文件/表向量一致。
诊断grant/ledger/安全报告写在独立证据目录，明确属于技术记录写入，不声称全进程零文件写入。
不能用裸 `read_data`、直接返常量、伪VERIFIED回执或跳过授权来代替该实际工具读取。

每次模型发送前，重新核fixture/hash/当前两主体授权、固定schema及精确body；变化或撤权停止。
原项目owner必须等于冻结user，且传入runtime必须等于该项目原 `projects.runtime_id`；
不能仅靠authorize对传入runtime的Grant检查来替代这个关联验证。
不跨HTTP持有数据库事务，不缓存权限PASS。固定合成资源不能被模型重指向；其他resource_id、
额外参数、未知工具、多个tool call均拒绝，且不进入下一次模型请求。

## 两次请求的顺序与oracle

1. 请求1：原 `InternModel.request_serialized_captured`，精确body guard返回预先固定deadline。
   原严格JSON、模型身份及 `parse_response` 全部通过后，必须恰有一次 `resource.read`，
   参数严格等于冻结resource_id。直接给答案、错误工具/模型、截断或缺usage均停止。
2. 用原只读网关实际读取一次，保存安全完整工具结果（resource_id/content/hash/format）并核hash。
   它是只读工具结果，**不是Operation VERIFIED回执**。没有补写Operation或业务账本。
3. 请求2：保留原safe assistant的tool call id、函数名、arguments及必要content，不重写模型行为；
   附 `role=tool`、相同tool_call_id、实际工具结果，第二次tools为空。至少在首响应结束6秒后发送，仍用原适配器。
   第二请求正文超限则停止，不能删字段/截断反馈来塞进预算。
4. 响应2必须是原身份接受、finish_reason=stop、无tool_calls的文本，严格比较答案去除外围空白后
   等于材料内容去除最终LF；没有第三次请求或“修复”。此处“修订”按AT-02原口径指反馈后续答，
   不声称模型先答错再纠错，也不把该字符串oracle升格广泛语义验收。

第二次请求必须确实含第一次原工具调用与实际读取反馈，证据分别绑定两次wire摘要、
返回模型身份、call id、工具输入/输出hash及安全assistant消息；无工具或未消费反馈不能通过。

## 拟议新执行预算（当前未批准执行）

两次请求上限；每次512输出token，共1024输出；一次工具读取；零修复、零重试。
完整body每次至多1988 UTF8字节，保守预约 `len(body)+512`，两次累计最多5000。
逐次累加原规范usage，总reported tokens超过5000、单次超过预约或输出超过512均停止，
保留真实超额值；usage unknown/partial停止并保留占额，不能填零或发送第二次。
**字节预约不是官方tokenizer证明或上游输入token硬配额**；实际provider用量以收到的usage为准，
输入隐藏开销不能先验精确限制。发送体与次数、输出上限是本地可执行边界。

新一次性技术grant绑定最终执行源码、schema/材料/fixture摘要和绝对截止时间；全链600秒，
每次请求至多120秒且不超过全链截止，结束后清理至多10秒。预约先持久化才进adapter，
STARTED/UNKNOWN、崩溃、拒绝或预算失败后不重发、不换目录重置本次grant，不沿用旧探针余量。
`Settings.max_requests`自身不执行计数，须跨两次请求共用同一小型一次性诊断账本。
不复用当前 `BudgetedProvider.call`：其固定1024输出且不传递deadline guard返回值，
不能仅套它便宣称本方案512/120秒流式边界成立；也不修改其产品语义。

## 实现前/执行后必要证明与证据

下一片实现后先做少量Mock反例：正确两轮、直接答案/错工具/错资源/多call/错模型拒绝、
未知usage/超限/第二轮越界不发送、fixture变化/撤权拒绝、失败后grant不可复用。
必须观察工具执行前后SQL零DML/DDL、全部表和文件不漂移，错误与异常亦关闭读连接及HTTP client。
不跑旧后台大套件、真实模型、Edge、PG或G0来证明设计。

未来真实窗口只保存安全投影、最小合成请求/工具反馈/响应、用量、期限与清理；
写入前检查不含当前凭据，禁止header/Settings/异常repr或私有reasoning落盘。
先检查原始body，再遍历严格解析后全部JSON key及字符串值检查解码后的凭据反射，
防止JSON转义绕过字节子串检查。命中后停止，不保存安全消息也不hash该body；
无法严格解析的body不保存/不hash，以固定错误码、长度和完整性状态保留失败。
没有原始响应时明确摘要不可独立重算。
执行失败保全原件，零自动重试。完成后独审实际覆盖，不能由设计ACK推导链路成功。
