# 四步骤文本 r10：独立有限静态复核

结论：**STATIC_LIMITED_REVIEW — 五项原静态发现的修复路径均已闭合；本轮未见新增核心阻塞。** 这是源码静态复核，不是实际 API/HTTP/冷 Worker/JSDOM 测试 PASS，不是模型、语义、人工签收、发布或旧软件升级签收。

准确来源为 root 的 `frozen-r10.json`：414 source/tests map `8315e4f02df120c2b066c12e58dd2299e5dbbe52062d8b53fcfd4514512253fa`，68 Python implementation map `ccf4ffd41ff45ccf5d46d12ebb659c1ea930b9f75dd45922ec84781806d0c70a`，pyproject SHA256 `49f68cb7901e719cd014141c69e5fa9ea562f51e9b9c40acd122ace6f2085d81`。HEAD `1ab405fa5a413e9812744d39b7c0d51c9265ee3d`，branch `dev/pb-text-multistep-20261012`。

本轮范围严格为原②⑤残留和全部五项原发现，以及这些局部修复的封闭契约；测试 0、探针 0、仓库写入 0。旧未冻结/r8 源码、报告、r8 末尾 source mismatch 与失败历史均原样保留，不用 r10 结果重签它们。

## 五项修复

| 原发现 | r10 静态结论 | 准确路径 |
| --- | --- | --- |
| ① JOIN-only 漏失败任务与 typed 版本 | 已闭合 | text_workflows.verify_instance_records 对 AppRun、binding/Run、ACCEPTED event、两边 RunScope metadata 集合逐项对齐，缺任何独立锚不能因 JOIN 消失；全部状态重新核验，typed 成功双向集合、严格 data_version 与连续版本一起检查 |
| ② 持久 JSON Python 宽等 | 已闭合原残留 | app_jobs.load_binding:313 现在比较 fingerprint(a.input) 与 fingerprint(snapshot.input)；实际 output 另有严格 schema+FP；Goal/proof/marker/text_goal 规范 FP。实际 AppRun emit_report 的 true→1/float 单边污染不再与原输入宽等。只比较原请求 FP 保留了 schema-invalid 原请求的准确 FAILED 历史，不需为原坏输入额外强行 schema 拒绝 |
| ③ 未核 Scope seal 与坏 binding 指针门 | 已闭合 | scope_gate 先核 identifier-only ScopeInput 双 seal、request/response FP、aid/user/pid/runtime 与 draft rid 投影，再 authorize，之后才读取 protected body；job_scope_gate 以独立 RunScope/Run identity/ACCEPTED/Instance metadata确定原 scope，不依赖可变 full binding/context |
| ④ 跨项目源先读 body 后拒 | 已闭合 | verified_source expected_pid 在 source full body 前拒绝不同 pid；options/create/已存 verify_origin 都传选定 pid；initial_only 也先限制原 source metadata |
| ⑤ 无输出状态/error 与 CLAIMED 例外 | 已闭合原残留 | AppRun/Run error 用规范 FP；FAILED 保留错误；current fence 的 CLAIMED 只有在本 fence 尚无 TEXT_WORKFLOW_STEP_VERIFIED 时才能解释 QUEUED→RUNNING。每实际 step event 写当前 fence，WORKER_LOST gap 也必须对应当前 fence |

第⑤采用当前执行区间，而非整个历史 `not proved`，是合理校准：Pause→Resume 后新 claim 的 AppRun 可以暂为 QUEUED，而旧 fence 的 verified prefix 合法存在；一旦本 fence 已提交任何真实步骤，就不能再以这个区间的初始 claim 解释 QUEUED。先前的“所有 proved 必须为空”建议过严，r10 的有限规则保留合法前缀恢复。

## 同范围附加修复

- bound 除严格 int0 requests/repair/reserved counters 外，还要求该 Run 实际 Attempt 表为空；零模型声明不靠 context counter 单独自证。
- both RunScope seals 与 ACCEPTED 同时缺失时，job_scope_gate 用独立 Run runtime 及 `internal:+原AppRun.id` 查 metadata 还原原 app scope，在 full Run/binding/Goal/result 前 fail closed；不能因为所有主 marker 一起删除而降级。
- 正常 RunScope pair 也核 `Run.request_key == internal:+meta.app_run_id`。现有 fresh runtime、Instance/source_app 和 AppDraft 范围一起约束身份，不用损坏 binding 指针替代原权限域。
- 原创建 key 的回执现在带严格 request/key/request_fingerprint/runtime；App 返回独立 sealed origin。页面读回后交叉核 key、原请求 body/hash、appid/project/runtime/name/candidate FP、资源/hash、Goal version/FP 和 source proof FP。未知回执仍保留原 pending，只 GET 原 key，不自动重 POST；这些是静态路径确认，本轮没有运行页面。
- commit_guard 明确拒绝非 mock 或 live_enabled 的 Worker；与闭集 compute 无 provider/Replay 派发及实际 Attempt 空账本一起构成有限离线范围。

## 有限契约维持

新 adapter 仍在既有 app_jobs/Run/AppRun/Worker/事务中派发，复用 DAG 纯解析/分支 helpers；没有新增外部运行框架、通用 DSL、动态工具或任意用户代码。private compiler 的严格 models/schema 与 whole canonical FP 固定四节点、三引用、完整输入/输出/接线/when/permissions/locks/check/预算。旧全局 pure compiler/kernel 没有因此被扩成任意文本图。

read/A/B/report 各有实际独立 Operation/Intent/Receipt 和计数，cold receipts 重建前缀及引用 oracle；false 保留三个 VERIFIED+单 SKIPPED，PARTIAL 不追加 typed 成功报告；来源只认可完整 SUCCEEDED 四步。每步和最终 typed CAS 前后仍重新核 live lease/fence/cancel、当前 Grant/source bytes/current Goal、精确 Instance revision/Release/runtime/project/app 和三者最小工具/时间 cap。

GoalSpec 真实 card_id/完整 goal/constraints/unresolved 最后版本 FP 锚，加 accepted binding 完整 text_goal，仍与当前 native head/body和独立 Run FP 对照；source_goal_card=None 明确属于内部 AppRun 合同，不冒充普通 GoalRun。source 审计依赖、current Goal/权限变化使历史读取失败关闭的限制保持可见，不宣称原材料删除后数据无关运行。

提取只允许初始 source 一 hop：expected_pid/initial_only 在原 source body 前执行，已存 derived origin 同样过此门。新资料不同 ID/hash、绑定其自己的当前 Goal，不继承原源签收。owner PENDING、逐项提交 UNSUPPORTED、semantic UNKNOWN、formal publication false 保持；不签完整 F2-T03/T04、完整 P-A/P-B 或自主模型规划。

## 来源核对与不执行范围

本目录 `source-before.json` / `source-after.json` 保存完整 414 source/tests、68 implementation map、pyproject、HEAD/branch 前后核对；核心桥接与 UI 文件也有准确复制。`manifest.json` 逐项封存本轮文件。文档允许 root 修改，不在 source/tests map 中；不借用另一独审或 root 的实际测试分母。

本轮没有运行 pytest、Node、HTTP/Worker/JSDOM 驱动、模型、socket、native browser、CI、数据库迁移或任何原已取消精确安装竞态。实际链路、软件桥接回归、真实红/绿与最终业务有限签收依赖另一个独审及作者的独立执行证据。本静态复核已结束，无活动测试，无额外核心修复请求。
