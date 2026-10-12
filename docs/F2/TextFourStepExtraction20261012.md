# F2-T03/T04：有限四步文本任务与 P-B 提取（2026-10-12）

## 实际范围

在既有 AppDraft → 内部 Release → 独立实例 → Run/Worker 上新增封闭文本家族。合同为 `read → lookup_a / lookup_b → report`，稳定节点 ID、每步输入来源、两个独立检索词和 `emit_report` 布尔条件全部冻结。不是任意 DAG、脚本执行器或真实模型生成；全局旧执行器、contracts/preflight、Worker/db/tools、CSV 内核及原单字面检索实现均保持原字节。

初始任务从用户明确选择的当前 native GoalCard 和授权 TXT/MD 建立可信有限模板，通过实际 Worker 形成四个真实 Operation/Intent/Receipt。P-B 仅从该初始任务的完整 SUCCEEDED AppRun 提取一次；目标是不同 ID 且不同内容 hash 的新 TXT/MD，并明确绑定新材料自己的当前 GoalCard。没有从单检索包装四条回执，也没有把旧输出复制为新结果。源数据/目标/权限仍是可核查审计依赖，不是无旧内容独立逻辑。

边界：TXT/MD ≤1536 UTF-8 字节、32 行；检索词必须已经去除首尾空白，1–80 字符、单行；每次检索 ≤8 个完整命中行。GoalCard JSON ≤6000 UTF-8 字节，有非空 constraints/acceptance_checks，unresolved ≤15；拒绝超限，不截断。四步逻辑工具预算为4，实际模型请求/repair/token 为0，runtime 上限为当前/冻结/声明三者最小值。纯检索与报告消费已核 read 快照，每步还有当前权限和字节读取 guard，回执明确区分 business read 与 guard read，不宣称后续步骤完全无材料读取。

## 合同和核验

`src/sim2act/text_workflows.py` 的私有 compiler 先严格 AppManifest/ActionSpec 模型与 schema/value 校验，再与整个 canonical graph/schema/when/lock/permission/effect/idempotency/error/budget 指纹比对。仅 resource.read、既有 text.literal_evidence 和私有 text.citation_report；新 ref 不进入全局 registry。原全局 preflight 仍拒绝这些私有检查/ref。`text_continuations.CHANGED` 仅明文登记这一闭集桥接模块；旧 literal pure 文件不变，两个已接纳旧 SQLite 续用合同必须重新实测。

GoalSpec 冻结真实 card_id/goal/constraints/unresolved，并追加 card version+fingerprint 锚；完整 native snapshot 冻结在 accepted AppRun binding.text_goal（独立 Run fingerprint 密封）。source_goal_card=None：该字段属于原普通 GoalRun 的另一种 accepted 格式，不伪称内部 AppRun 是普通 GoalRun。每步、终态前以及历史读取核当前 native head、原完整快照和此锚；Goal/材料/权限变化失败关闭。完整唯一 ACCEPTED header 还必须与冻结实例/AppRun/Release/精确 request fingerprint 逐字段一致，不能只核ID集合。审批仍是原精确内部 snapshot/grant version/TTL 协议。

读取、A、B、报告各用一个短事务，真实 Operation/Intent/Receipt 与 check 写入，支持已核前缀冷恢复。报告条件 false 则保留三个 VERIFIED 节点与独立 SKIPPED 事件，Run/AppRun 为 PARTIAL，无 typed success row，不能充作提取来源。无命中是合法空引用，true 报告明确显示无字面匹配；语义仍 UNKNOWN。任何错误、取消、当前版本/CAS/lease/fence/预算竞争，不追加部分成功 typed 结果，已有真实步骤与失败留档。

作用域门先核封闭 ScopeInput 双 seal、draft 的最小 resource/runtime/project metadata，再授权；Run 另有双 sealed identifier-only RunScopeInput，不靠可变 binding 指针或读取 Run.context 后才授权。跨项目 source 在完整 body 前拒绝。历史集合由 AppRun、binding/Run、ACCEPTED event、独立 RunScope 四个 metadata 锚对齐，逐项重验全部状态/实际 receipts，typed 成功双向集合与连续 data_version 一并核对。持久 JSON 使用 schema+规范 fingerprint，避免 Python 的 True==1/1.0 宽等。模型0还要求实际 Attempt 表为空；不能只信 context 计数。RunScope/ACCEPTED 同时缺失时，仍以 fresh app runtime 与 internal:+原AppRun ID 的独立最小 metadata 找原材料 scope，先授权再失败关闭，不回退到读完整 Run 才判断。

## 页面与签收

在既有项目目标卡页提供完整预览、独立明确确认、当前 Goal/材料/完整源证明和新只读运行身份授权。独立应用由普通内部快照确认/实例控件执行两次检索和条件报告。创建/新运行回执未知时只以原 key GET 恢复，不自动重新 POST。回执 original key/完整 request fingerprint 与实际 app 独立 origin 双锚一致，并核新 Goal/材料/源证明/运行身份。身份/连接/项目/工作区/目标/应用/编辑 generation 隔离迟到结果。已提交 POST 后 await request hash 的窄窗可能再发一次只读 GET，后续 current 门先于 receipt/Open/清 pending；未签“所有异步窗无只读请求”。沿用20静态资产与原三工作区。

新应用 owner PENDING，不继承源声明；该新四步家族当前逐项人工提交明确 UNSUPPORTED，页面直说待签收，不把技术 PASS 显示为人工语义通过。发布始终 false。本次不提升完整 F2-T03/T04、完整 P-A/P-B、真实模型/客户材料/人工语义门。

## 证据

最终冻结、实际作者/独立结果及失败历史以 [本轮证据](../evidence/pb-text-multistep-20261012/README.md) 为准。原前轮证据、b244/1ab 工作与既有失败原字节保留。

Windows、PostgreSQL、原生浏览器、实际旧源码升级、真实模型/付费 API、真实 owner/语义、部署和完整 P-A/P-B：NOT RUN。Forbidden CI 保持停止；历史精确取消候选安装窗口永久 NOT_VERIFIED，未重试、改名、替代或导入该候选。本次新家族常规 queued cancellation、节点间撤权与租约恢复不签该历史窗口。
