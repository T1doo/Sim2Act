# 四步骤文本首轮适配器：独立静态审查

**STATIC_ONLY / UNFROZEN / NOT_EXECUTED。** 本轮只读审查 root 未冻结候选，测试、探针、HTTP/JSDOM/Worker 执行均为 0；不签执行 PASS、语义验收、发布或软件最终 FP。准确源码为本目录六份复制文件，`snapshot.json` 保存各文件 SHA256、HEAD、branch 和复制时即时相符核对；不把随后 root 的修改视为同一候选。

整体路线可继续：`text_workflows` 是现有 `app_jobs` 中的封闭 adapter；复用原 Run/AppRun/FrozenContract、事务、Worker 派发、lease/fence 与 DAG 纯解析/分支 helpers，不是新增外围执行框架。已有代码确实逐节点分别创建 Operation/Intent，计算、oracle、VERIFIED Receipt、tools counter 同事务提交；false 报告独立 SKIPPED，最终 PARTIAL 无 typed report。以下完整性缺口仍需修复后冻结验证。

## 阻塞与必要修复

1. **P1：JOIN-only 历史发现隐藏缺失失败任务。** `text_workflows.py:620` 只通过 Run→binding→AppRun JOIN 得到 jobs，最后将成功 AppRun IDs 与 typed rows 比较。缺失 binding、AppRun 或 Run 后，整项会从 JOIN 消失；原本没有 typed row 的 FAILED/CANCELLED 任务最容易不留下集合差异。没有独立比较 accepted event、AppRun、binding/Run metadata 集合，也没有核实例 `data_version == len(records)` 和连续版本。应从独立 metadata 锚发现并对齐整套已接受任务，逐项冷验全部状态、失败/跳过和 typed pointer，不让损坏对象自我从历史中移除。root 已明确接收修复。

2. **P1：持久 JSON 仍有宽等污染通道。** `verify_job:574` 对 AppRun output 用 Python `==`，没有先校验这个实际持久 output 的 schema；Receipt 和 typed row 的严格核验不能补上它。只将 AppRun output 中一个 citation 的 `start_line=1` 改为 `true` 或 `1.0`，按 Python 相等语义仍可与合法 oracle/record 宽等。`verify_origin:236,241,250` 的 metadata response、marker、Goal/proof，`bound:462` 的 text_goal，以及桥接 `app_jobs.load_binding` 的实际 AppRun input 也应全用严格 schema 与规范 fingerprint 比较。原 key/source 提取必须核实际 AppRun JSON，而不能以其他正确副本替代它。root 已明确接收修复；这是假设代码路径的静态推导，本轮未执行污染实验。

3. **P1：scope 门使用未核 seal 的主行投影。** `scope_gate:212` 先从 META 主行取 rid/runtime/pid，再 authorize；双 seal、fingerprint 和严格 ScopeInput 在读取完整 draft 后的 `verify_origin` 才核验。若 runtime 后来拥有另一材料的合法 Grant，单改 META rid 为该材料，可以在原材料已撤权时通过初门，先读原 private draft/后续 body，再冲突。ScopeInput 全部是 metadata，可在门内先读双 seal、严格核 request/response/row FP、绑定 aid/user/pid/runtime，再 authorize；无需先读 protected draft/Goal 内容。还应检查 `text_continuations.job_gate` 经原 binding.app_run_id JOIN 定位权限域：坏指针不能让另一个合法域的授权替代原 Run 域。新 load_binding 的 Run FP 门是有益加固，但 inspect 已先读取 full Run，不能单靠它保证读取顺序。

4. **P2：selected project 的 source 门在 private body 之后。** `options:370` / `create:388` 先完整 `verified_source(source_run_id)`，随后才检查 proof.project_id==目标 pid。用户同时拥有两个项目时，跨项目 source_run_id 会先打开另项目的完整 Run/Goal/成果，再被拒。建议 verified_source 接收 expected_pid，在完整 Run 和其他 private body 读取前，仅查 principal/project metadata 并精确匹配；来源当前授权仍在其独立 scope 门内核验。

5. **P2：无输出状态的一致性检查过宽。** `verify_job:586–587` 允许任何 AppRun 状态配 job RUNNING，只要输出/版本为空；例如 AppRun 被改成 SUCCEEDED 且没有结果仍可通过。FAILED 等无 residue 状态也不比较 AppRun error 与 Run error。首次普通 claim 的 `AppRun QUEUED → job RUNNING` 窗口可有限允许，须明确 0 步、无错误/结果；其他状态及错误严格一致，不能用“无输出”作为免检条件。这与第 1 项历史修复一起完成即可。

## 已有正确边界与待验证点

- **whole canonical 校验确实存在。** `compile_candidate:155` 先用严格 AppManifest/ActionSpec/GoalCardInput，再对整个 candidate 与 server canonical 的规范 fingerprint 比较，并 schema_check 全部端口。固定四 steps、三个引用、一个 boolean eq、两独立检索前驱和两个 report 前驱被一起约束；不会因为 schema 通过而接受任意 workflow。不存在用户脚本/模型/动态工具输入。
- **这属于私有闭集编译。** 私有 literal action 使用更窄 1536 bytes/32 lines/8 citations 和新 check；并不是原 global literal action 全契约的另一次普通 preflight。必须在合同/页面声明此有限 profile。全局 contracts/preflight 保持原 bytes，旧 family 没有因此得到私有 ref。
- **预算 metadata 需说明。** 当前每 action nominal max_requests=1、max_total_tokens=1、run_seconds=整个 runtime cap，而 app 分别为 1、1、一个总 cap，不能声称满足旧 global preflight 的逐 action 预算求和规则。实际固定实现无模型请求且普通 Worker 用 tools≤4 和总 wall deadline 重核，没有据此发现实际预算越权；应明确私有 profile 的有效零模型预算/全 Run 时间语义，或使声明与承诺的合计规则一致。
- **四步实际账本具备基本结构。** `advance:660` 每次只执行下一个节点；Intent 绑定 args/wiring/predecessor FP/branch，Receipt 绑定输入/输出/source/action、真实 read 与额外授权 guard read。Oracle 从实际 source 分别重建两组完整引用和报告，持久 output 有严格 schema。失败不应补造后续 Receipt。
- **final CAS 与后写重核具备基本结构。** `commit_guard:635` 重新锁 live fence/lease、原 binding/current Goal/resource/授权/current limits，核实例 revision/release/runtime/project；每步提交前后 guard，typed insert+instance data_version CAS+AppRun output 后再次 guard，再终态写入同事务。源码存在该防线，不等于本轮已证明回滚/撤权/租约/取消执行行为。
- **模型 0 是实际实现路线。** 新 process 不构造 Replay/模型、不调用 provider；bound 强核 request/repair/reserved counters 为严格 int 0。仍应冻结后用实际 counters/NoModel 与普通 Worker 核验，不借用旧 literal 结果。
- **GoalSpec 替代锚可接受。** `source_goal_card=None` 避免触发普通 GoalRun accepted 格式核验，并未声称该内部 AppRun 就是 GoalRun。GoalSpec 中 card_id、完整 goal/constraints 和 appended version/fingerprint 文本锚，加 accepted binding 中完整 `text_goal`，可以形成明确新家族契约；必须以严格 fingerprint 对照当前 native snapshot 与 independently accepted Run FP。≤15 unresolved 留最后一项，拒绝超限而不截断，符合有限声明。完整 known/assumptions/acceptance 等依靠 binding 而非 GoalSpec 自身承载，应公开这个区别。
- **finite 1-hop 的创建限制已有。** options/create 拒绝 extraction_depth!=0；但 verify_origin 对已保存来源没有同等 depth0 重核，来源核验会递归进入 bound/verify_origin。建议在来源 metadata/封闭 family 门先确认初始 source，并设显式最大验证深度，坏历史不能形成无界递归。不能只在创建时限制而读取时假设它永久有效。
- **当前仍依赖原 source availability。** 提取后的 verify_origin 会完整重新核原 successful Run、原 source/current Goal/权限；这不是数据无关独立 logic authority。来源撤权、删除或 Goal 变更会阻断后续验源。未见新资料的冷 Worker 技术切片与“原材料消失仍运行”应分开声明，不借用旧 data-free literal 签收。
- **历史 live/frozen 分界需合同明确。** 当前 bound 总调用 current_goal，Goal head 改动后原 key/历史读也会 STALE，且 schema-invalid 输入的 FAILED Run 在 bound 再验证时可能无法读出其 FAILED 摘要。这是 fail-closed，但若承诺原 key 可回读完整失败历史，则需要只读 frozen-history 检查与 live dispatch 门分开；不可为历史读取放宽 live 执行。
- **owner 策略未扩展。** 目前初始 first action=resource.read，现有 owner base 会明确拒绝该新家族；保持 owner PENDING、semantic UNKNOWN、pubfalse 正确。若 root 后续把 owner 功能纳入候选，另核新 target Goal、精确 Release/Instance/新输入全四步 evidence 和原 ledger STALE，不能继承 source ACCEPT。
- **旧软件桥接。** text_workflows 明确加入 CHANGED，旧 global pure kernel 尚未在这份桥接 diff 中修改。必须以最终 source map/pure hashes 和旧 literal/有限 continuation 实际回归重新 qualify；本轮未签软件兼容。

## 交付与后续

六份源复制、snapshot.json、本报告及结束来源差异记录/manifest 全部位于本目录。root 在工作期间仍可改 UI；这些静态发现以本目录准确 bytes 为依据，不是最终候选的全 source freeze。root 已确认前两项将在作者活动测试结束后修复，并保留本候选及红轮。

本轮没有执行任何测试/探针，没有产品修改，没有活动测试要等待。完成必要修复和 UI 支持后，待 root 提供准确 freeze 再做普通独立 API/冷 Worker/可见页面验收；不扩大到原已取消竞态、socket/native/CI/真实模型/新环境。
