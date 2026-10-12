# 非 CSV 多步骤文本任务提取：独立静态设计审查

结论：现有持久运行内核可承载本轮有限切片，但当前产品尚不支持所要求的完整链路。建议在同一编译、权限、队列、Worker、Operation、Release 和实例账本内增加一个封闭文本 profile，真实执行 `read → lookup_a / lookup_b → conditional_report`。既可复用现有 DAG 执行路径，也可按 root 后续选定方案在现有 `app_jobs` 中加入局部 adapter 并复用 DAG 纯 helpers；不要求另造队列。不能将单次 literal 的结果包装成四步证明，也不能将 CSV 家族改名后宣称已支持文本。

状态为 **DESIGN_ONLY / NOT_EXECUTED**。本轮测试、探针、真实模型、HTTP/Worker/UI 执行均为 0。以下是实现建议，不是执行 PASS、语义验收或正式发布签收。

## 1. 范围与基线

- 实际只读 checkout：`dev/text-compatible-continuation-20261012`，HEAD `1ab405fa5a413e9812744d39b7c0d51c9265ee3d`。父任务中的短称以这个实际 Git SHA 为准。
- 本轮只读源码和原 V5 文档；产物仅写入 `/tmp/pb-text-multistep-review-20261012`。仓库写入仍由 root 独占。
- 原 V5 产品 §4 P-B 要求从已完成任务的目标、输入输出、工具轨迹和检查识别变量及稳定步骤，去除原会话和路径依赖，再用未见输入、错误输入和冷会话验收；一次成功不能证明通用应用。§5.3–5.7 要求有限类型 DAG、可信引用、逐次权限重核、不可变计划、幂等原 key 和持久状态。原分阶段计划 F2-T03/T04 及 AT-10/11 指向该真实能力，不是单 literal 的名称扩展。
- 现有离线 NoModel 工程证明可以作为有限技术切片；不替代 V5 的真实书生、完整 P-A/P-B、Windows、一般语言理解或发布验收。原已签收链的分母和旧失败证据均独立保留。
- 不包含既已取消的候选安装精确竞态；不包含 socket/native/browser/CI/新环境/旧软件实库迁移/模型或付费 API。

## 2. 可复用内核与实际缺口

| 现有位置 | 可直接复用的能力 | 必须显式补齐的范围 |
| --- | --- | --- |
| `contracts.py` / `preflight.py` | 严格 closed schema、typed FieldSource、声明前驱、eq/in/exists、有限 all/any、完整静态权限和预算并集 | 注册文本纯报告的精确 action/schema/check；增加明确新 profile 分派；不能放宽全局能力目录 |
| `text_apps.py:11,31,83` / `agent_apps.py:232` | TXT/MD literal 的有界执行及独立整行引用 oracle | `compile_text` 硬限一 action、一节点、无前驱/when；此限制保留给旧家族，新家族另作闭集校验 |
| `apps.py:190,257` | 编译与独立来源 marker 核验 | 当前 any literal 会进入单节点编译；新 family 应先识别，独立 marker 必须阻止删字段后降级到旧 literal/CSV |
| `csv_dag.py:345,435,483,595,673,693,776` | 原 key 双记录、冻结 Run、分支决策、Operation/Receipt 前缀核验、fence/lease、预算、提交前后 guard、持久 Worker | plan 输入/source format/expected/read_source/action 分派均有 CSV 假设；文本不能被要求 `data.aggregate_csv` Grant；跳过和状态需要实例适配 |
| `registered_run_extraction.py:45,395` | 从真实成功 AppRun/Release 再核验、目标既有授权域、持久提取身份 | literal 源只认可一个 `instance_result` Operation/typed record，变量只有 term；不构成两检索和报告的证明，不能克隆旧 Goal 签收 |
| `csv_dag_instances.py:47,113,246,350,439,497,530` | 精确 Release/Instance/AppRun 冻结绑定、原子派发、结果 CAS、请求/绑定/event 集合完整性 | 闭集只允许无条件 CSV 两/三节点，拒绝 when；typed 输出投影为聚合而非完整引用报告；文本 FAILED/PARTIAL/skip 历史必须有完整验证路径 |
| `lifecycle.py:86,291,375,492,618` / `app_jobs.py:68` | 不可变 Release、内部实例、typed data、切版/读取入口 | `execution_source` 当前统一分派到 CSV；应按封闭版本枚举区分，未知版本拒绝，不能因删 marker 退回单节点 AppJob |
| `worker.py:316` | 当前普通持久 Worker 的 DAG 优先派发、心跳、重启恢复 | 复用此入口扩展有限 profile；不增加平行队列或另一个执行器框架 |
| `web/internal.js:162,177,276` / `web/csv-dag.js:475` | 持久原 key、只读恢复、真实页/API、当前结果与历史分离 | 当前只有 term/column 输入和 CSV 图形断言；新 profile 要显示两输入、条件、各节点状态和完整引用输出，保持已有 read/edit/workspace/身份代次门 |
| `app_owner_goals.py:46` / `owner_acceptance.py:137` | 自有目标冻结与人工逐项签收的既有单 literal 策略 | 当前不支持该多步家族；不能把已有按钮直接开放或继承来源签收 |

## 3. 最小封闭图与输入

建议稳定四个 step ID，四个独立 action binding（现有回执循环将 workflow/actions 严格 zip；不能用未实现的一 action 多节点重用假设）。图为：

```text
                        ┌─ lookup_a(term_a) ─┐
read(resource_id) ──────┤                    ├─ report  when emit_report == true
                        └─ lookup_b(term_b) ─┘
```

运行输入精确为 `{term_a, term_b, emit_report}`，两个检索词均为非空、已 trim、≤80 字符的字符串，条件必须是真 JSON boolean，拒绝数字 0/1、未知字段、缺项和隐含旧默认值。两个输入槽和检索节点独立；即使词值相同，也不能共用一个 Operation/Receipt。资料由服务器绑定的新资源 ID 进入 data binding，不能让运行输入指定任意路径或扩大资源域。

延续现有 TXT/MD 边界：UTF-8 ≤4096 bytes、≤64 行，每个检索 ≤16 个完整匹配行，case-sensitive，零匹配是有效空集合。schema 的 maxLength 不等于 UTF-8 bytes，也不能表达所有非空/trim 要求，因此保留运行时限额核验。严格继承平台上限；四个执行节点能在现有 max_tools≤4 内完成，不为本轮抬高全局限额。model requests/repair/reserved tokens 实际计数为 0。

`read` 是实际授权读取及不可变源快照回执；两 `lookup` 分别从 read 的 resource_id 类型边和各自显式词输入解析，前驱 hash 绑定 read，独立计算并核验完整引用。可以沿用 `text.literal_evidence` v1 的精确 action/schema 和 `compute/check_evidence`，但由新图 profile 接收两次真实派发；不能改变旧 v1 的输入含义。每步重新读取/核权时，actual_reads 应记录真实 `resource.read`，而非虚构新 Grant 或把纯计算的 action ref 当作 I/O 工具。

`report` 为一个新增可信纯注册动作，消费两检索的完整 typed evidence（term、resource/hash/revision、ordered citations）或与其完全等价的完整类型边，依赖两检索回执。输出固定结构的两组引用和确定性文本，明确 `semantic_status=UNKNOWN`。报告检查应从源行及两个实际检索输入/回执独立重建，再核全部输出；只比较自身文本 hash 不足以证明引用正确。不得让客户端提供任意模板、HTML、代码、URL、模型提示或 write scope。不能复用 CSV 的 sum/count 报告 schema 掩盖引用。

`emit_report=false` 仍执行 read 和两检索，报告持久 `SKIPPED`，记录条件、观察值、理由、input FP、前驱 Receipt FP。若完整报告为必需 sink，沿用 DAG 的 `PARTIAL` 终态，typed report 版本增加 0；保留三项真实成果和跳过证明，不能返回上一份报告或把跳过算成功提取源。成功源必须是 true 分支四个 VERIFIED 节点和 SUCCEEDED。若产品希望 false 分支也算完整业务结果，必须事先定义并审核另一种完整输出契约，不能事后改成功标签。

## 4. 最小 P-B 链路及每步证明

先通过同一普通 DAG/Worker 入口真实完成这四步任务。服务器封闭 canonical profile 可以提供有限工程入口，但必须披露人工目标/图范围，不能称作通用模型规划或用静态样例替代真实执行。

| 阶段 | 最小持久证明 | 禁止的捷径 |
| --- | --- | --- |
| 初始真实任务 | exact Goal/Run contract、plan/graph/wiring/action revisions、resource hash、4 actual Operation/Intent/Receipt、各自 oracle、condition、counters、最终 full report | 单 literal 旧输出复制四次、只检查最终字符串、4 个静态列表充当真实工具轨迹 |
| 提取来源核验 | 当前所属 project/principal/runtime；精确 source Run/AppRun/Release/Instance/typed record；4 个回执的完整集合和顺序；source/contract/Goal/version/fence/accepted FP；模型实际 0、无 UNKNOWN | 只验某个成功 typed record，不核 FAILED/UNKNOWN 或缺失 Run 锚点；接受另一个 Release 的报告 |
| 生成有限新应用 | 从实际已核验图识别两词和条件变量；新 app/action/binding ID；显式新目标绑定和既有授权 runtime；来源 provenance 与执行变量分离 | 克隆旧答案、固定旧词、原会话缓存、任意节点/条件注入、自动新 Grant |
| 新 Release / Instance | 审核新候选的闭集、schema/dependency/budget；不可变 snapshot 双绑定；精确 original key、revision、Release FP；新实例无旧 typed data | 删除 execution_source 或来源 marker 后降级；导入源实例结果冒充当前结果 |
| 冷普通 Worker | 新进程/新 Run/新词；完全从保存计划与绑定恢复；fresh 授权读取，分步 Receipt/oracle；每步及最终 typed CAS 前后重核 | 浏览器先算答案、ReplayModel 旧响应、source 会话对象、旧 checkpoint 绕授权 |

新任务提取的存储 kind、plan profile、Release execution_source version 和 Run namespace 必须有闭集识别，独立持久来源 marker 不能只由 candidate 中可删的字段决定。同一内核中的小 profile adapter 足够；无须新数据库表/新外围框架，但也不能套用不匹配的旧 proof kind。

若目标是更换资料，绑定必须先验证目标 metadata、当前用户/项目/runtime 权限及 TXT/MD 限额，再读取目标 private bytes。新 Worker 必须用新绑定 resource/hash；不能要求目标拥有 CSV capability。自动授权、新 runtime/Principal 创建和独立无原材料 authority 是否纳入本轮，应由 root 的具体合同明确；不能从此前已签收的单 literal authority 推断本次也获准。

本轮授权只明确多步骤提取/冷 Worker。若还要求原材料撤权或删除后完整验源并运行，需要显式采用数据无关独立逻辑授权与不可逆来源承诺；现有 CSV source_snapshot/validate_snapshot 会重读来源，不能默许这一额外行为或宣称它已经成立。

## 5. 必须防守的完整性边界

1. **当前授权与后写核验。** 执行前、每次真实 read、每个 Operation 提交和最终 typed append/CAS 前后核同一 project/principal/runtime/source/hash、current Grant/撤权版本、当前预算、lease/fence/cancel/实例 revision/Release。纯 report 也不能绕过其资料 lineage 授权。source/hash、scope 或预算变化必须确定失效；中途失败保留已核 prefix，不产生部分 typed report。
2. **原 key 不成为重新执行指令。** 同 key+严格规范 body 返回同原 Run/结果，body 变化冲突；canonical FP 比较而不是 Python `True==1`/`1.0==1`。未知 POST 的恢复只 GET 原 key，不能清 pending、自动换 key/重 POST。GET 必须核该 key、对象身份、Release FP、完整冻结合同和双 seal，合格当前错误可见。
3. **Goal 与 owner。** 初始任务冻结真实声明的 GoalCard version/content/ref/FP 和资料范围；当前 CSV DAG 的合成 GoalSpec 不能冒充完整来源目标卡。源 Goal 只作为 provenance，旧 ACCEPT/签收不迁移。新应用保持 owner PENDING、semantic UNKNOWN、publication false；新家族 owner API 先明确 UNSUPPORTED。若本轮要支持新自有目标，需新应用自有卡/独立 scope/绑定，再冻结其 ref 于新 Run，并复用当前目标变更使旧 PREPARE/DECIDE STALE、历史 frozen read 与 live execution 分开的已有规则。
4. **完整终态历史。** 对 SUCCEEDED、FAILED、PARTIAL、CANCELLED、UNKNOWN、queued/running 都核原请求/双 seal、accepted event、Run+contract、AppRun+binding、Release+Goal、Operation/skip 集合和状态一致。保留 CoreR8 的 FAILED 绑定/frozenContract/Release/Goal/CAS 完整性防线；不能只检查成功记录或拿无数据终态作为免检例外。typed data version 必须连续，成功 full report 与对应 AppRun 互为闭集；失败或跳过不能新添版本。
5. **Receipt 独立性。** 重建每节点解析 args、typed persisted output、实际读取、前驱 FP、计划/图/输入/action revision、引用整行跨度/字节和条件观察值；拒绝丢节点、重复/伪造节点、错 step ID、跨 branch 替换、输出串换、bool/float 污染。两个 lookup 独立前驱都仅 read，report 同时消费两者；不能仅重做一检索然后拷贝另一结果。
6. **家族及软件边界。** 未知 profile/version、missing/conflicting independent marker 应 fail closed。新增 all-Python 软件 fingerprint 不得自动重签旧 data-free literal/continuation authority 或静默扩大允许软件集合。若新局部 adapter 纳入既有 CHANGED bridge，须明文登记准确文件范围、保持旧 pure bytes、确认新的当前软件目标 FP 并重新 qualify 旧有限续接链；不能将新文本家族冒充旧 literal authority。旧已签收兼容 continuation 的来源身份和历史保持原策略；新多步 profile 必须显式隔离，不能因第一 action 是 literal 被视作旧家族。
7. **可见页面和目录。** metadata-only 列表只读必要 metadata，不整项目扫描旧 candidate/Run contract/Release snapshot/GoalCard private 内容。页面显示本次 input、每一步 VERIFIED/SKIPPED/失败、完整引用与 source hash；新 typed report 和历史报告分别显示。身份/connection/project/workspace/edit ABA 后迟到 POST/GET 不得跟旧 iid/key 用新 global token 读回、不覆盖当前状态或清原 pending；保持正常 polling，不以停止产品 interval 规避问题。

## 6. 实现冻结后的有限验收建议（尚未执行）

- 真正四步成功源：同一来源两不同词各有可区分引用，report 含两组完整跨度；查 SQLite 实际四个 Operation、四个 Receipt、tools=4、model=0、无 UNKNOWN；服务器独立 oracle 逐项核验。
- 冷新实例：从这个成功源提取规范变量/图，绑定另一现有授权 TXT/MD，关闭旧进程，以普通 Worker 用两未见词运行；新 output/record/Receipt 必须按新源重算，旧 key 可只读，旧 output 不变。
- 真条件 false：三 VERIFIED + 一 SKIPPED，typed version 不变，完整 branch/input/predecessor proof，按冻结合同为 PARTIAL；不允许作为成功提取源。
- 有限输入和授权失败：错 format、边界 bytes/lines/citations、空/未 trim 词、缺项/多字段、emit bool 污染；项目/主体隔离、无 resource.read Grant、排队后撤权、read 后/结果提交前资料或授权改变，证明无新 typed append。只使用普通授权/数据失效测试，不触及既已取消竞态。
- 原 key/完整性：same key same body、changed body conflict、未知 POST 只 GET、精确 Release/Instance/Goal；逐项缺失或单边污染 seal/accepted event/Run/AppRun/contract/binding/Receipt/skip/typed pointer 的冷 GET 必須 fail closed，特别保留 FAILED/PARTIAL 终态覆盖。
- 一组正常可见页面：真实本地进程内 HTTP+JSDOM+NoModel Worker，实际 HTML/CSS/all scripts 资产证明，正常 intervals，新成功/false branch/错误与原 key 读取。受控离线 promise 资格测试独立标注，不能充当实际 HTTP/Worker。

这些是后续冻结验证的建议分组，不是本轮已运行数量。无需扩大到新外围功能、网络 provider、native 浏览器、CI、socket、部署或旧软件实库迁移。先完成闭集纵向链并保留真实红，再按证据修复。

## 7. root 选定的局部路线与附加门槛

root 在静态审查期间明确采纳四节点与 false→SKIPPED/PARTIAL，选定 `text_workflows` 局部闭集 adapter 从 `app_jobs.process_job` 分派，复用 Run/AppRun/binding/FrozenContract、lock_live/state_write/stop/fencing 及 `csv_dag.decision/resolve/skip` 纯 helpers，不修改 Worker/db/全局 contracts/preflight pure bytes。该路线可作为更局部的实现方案，不必为本轮扩大 CSV 实例适配器；前文 CSV 适配器限制是当前能力缺口，不是必须改该模块的指令。

专用 compiler 可以将三固定 action ref 登记限制在这个 profile 内，而不扩大全局 trusted registry，但需满足以下可审核契约：

- 原 `ActionSpec` / `AppManifest` 严格 models、`schema_check` / `validate_value` 仍使用。对全部 canonical 结构、字段集合、固定 node IDs/前驱/typed port、when、输出、views、action revision、dependency locks、permissions、effect/idempotency/reconcile/check/error contract 与预算做严格规范 FP 比较。模型结构校验自身不会解析可信 executor/check 引用，私有 registry 必须独立完成这一步。
- 私有只允许 read、literal、citation-report 三固定引用，实际四 bindings；没有任意 workflow/when/schema/script/prompt/allowTools 输入。旧全局 preflight 对未登记的新 report ref 继续拒绝，报告要披露这是封闭编译器校验而非声称任意 AppManifest 已获得全局支持。
- `app_jobs` 路由基于独立持久 family marker 和冻结版本，不能仅看用户 candidate 字段。新 branch 检查需早于单 literal prepare/commit 假设；load_binding/inspect/fail/command/history 同样必须分派，尤其 terminal FAILED 原 key 的完整核验不能遗漏。
- `app_jobs` 的单次 prepare_dispatch/compute/commit 不能先运行整图、最后合成四回执。各节点独立实际派发、Intent/Operation/Receipt 与 counters 原子提交，恢复时冷核 prefix、重新取得当前授权；最终 full typed report append 单次 CAS，提交后再核验，失败整事务回滚。
- root 的来源入口为显式当前 GoalCard+已授权 TXT/MD 的固定模板普通 AppDraft，经正常预检批准/Release/Instance，真实四步 AppRun 后才提取；新应用另选未见资料+显式当前 target GoalCard，精确确认完整 source proof，source 只留 provenance，不继承签收。该有限人工声明入口可接受为工程切片，不可称自主规划已完成。
- 当前多步 owner 扩展仍属研究选项。若纳入候选 freeze，必须增加新家族当前 Goal 与完整多步新输入 evidence 的独立逐项签收验证；若不纳入，owner PENDING/旧接口明确拒绝即可，不能只打开既有按钮。

## 8. 本轮交付

本文件给出最小实现建议和阻断点；`provenance.json` 记录实际 HEAD/branch/worktree 状态、审查相关文件 SHA256，以及末尾来源核对窗口内文件无差异核对。该核对不是后续实现 source freeze，也不是把作者或先前执行结果借作本轮 PASS。
