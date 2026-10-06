# 下一最小生成主线切片（只读设计草稿）

基线：`518223f2c0493ecebd7237956ac3f6f1303c7c7c`，2026-10-06。工作区仅已有 `scripts/browser-ci/agent-ui.cjs` 未提交修改；本审查不改它，不执行 CI、网络、LIVE、provider、外部发布。本文是实施建议，未实施/未运行测试，不是 PB 完成证据。

## 结论和不能跨过的事实

推荐切片：**已成功的内部 registered-tool CSV AppRun → 服务端依据可信回执自动生成同一已注册 CSV 求和声明式模板的新草案 → 用新 CSV、新 column 在冷会话中运行**。用户只选“已存在的目标 CSV app 授权域”和名字，不供 candidate、不供 wireReplay。目标 CSV app 必须已存在且其 runtime 已获授目标 CSV；新草案共享该既有授权域，不产生 Principal/Grant。此切片贯通一个真实持久任务来源入口，仍是内部工程 CSV 能力；不代表从任意业务任务自主归纳，也不代表模型生成主线/完整 PB。

如果要求来源必须是当前项目指令区的普通 F1 任务，则**不能直接实施提取**：`worker.py:359-374` 正常工具链完成固定写 `PARTIAL`、`goal_acceptance=NOT_RUN`。仅凭 VERIFIED 工具回执不能把这个 Run 提升为已成功真实任务。此需求必须先补具体成功验收接口，而不能在 extractor 中做状态解释。当前明确的 SUCCEEDED 来源是 `app_jobs.commit_result()` 的内部 AppRun；本切片使用它。

原 V5 产品设计 §4 P-B（119-127 行）要求明确目标、调用、输入输出和检查、新材料/错误输入/冷会话，不能仅重放旧答案；分阶段计划 F2-T03（95 行）、111-113 行和 AT-10/11（340-341 行）分别要求来源、未见输入和新 AppRun。这里仅落实已有可信 CSV 能力的这些机制，保留语义验收范围和正式发布关闭。

## 真实现状：生成缺口在哪里

- `apps.py:36-117` 的 `csv_candidate()` 是现有可信单节点模板；`compile_preview():190-236` 除合法 ID、来源标记、goal 外逐项比较接线/schema/能力，只允许 `registered_tool data.aggregate_csv@1` 或受限 agent 家族。
- `planning.py:1,23-80` 是明确 MOCK 的目标卡 + 用户选择 csv.sum/resource 组装，不是实际书生选择候选的生成证据。GoalCard 有版本/材料 hash，但普通 F1 GoalSpec 仍无可把整体任务判成功的实现。
- `extraction.py:62-236` 只接 PREVIEW 成功回执；`local_tasks.py` 是 `synthetic_fixture=True` 的固定 CSV 本地任务，已能自动组装模板。本切片不再复制这些固定入口。
- `agent_apps.py:189-223,506-590` 的持久化/提取仍要调用者提供完整 candidate、runtime；可信来源校验虽严格，候选尚不是服务端从源回执产生。测试中的 `candidate()` 和 `scripts/agent-ui/fixture.py` 供给它，生产 HTTP 无此生成/提取入口。
- `agent_apps.py:47-68`、`internal_api.py:24,39,72-77,210-225`、`web/internal.js:272-286` 要显式两条 offline_replay/wire 数据；没有自动生成答复或 provider fallback。UI 的 agent 原始/衍生草案展示不等于生成入口。
- `app_jobs.py:236-295` 已有冻结队列绑定与 release 校验；`commit_result():571-757` 对注册 CSV 输出跑独立 exact_sum_oracle，原子保存 `internal_instance_data`、VERIFIED operation/intent、`internal_app_runs=SUCCEEDED`、`runs=SUCCEEDED`。这是足够接入一个可靠来源服务的数据。
- `apps.py:149-186` 的 `persist_csv_candidate()` 会新建 runtime Principal 和两条 Grant；本切片禁止调用它。来源 app runtime 通常仅授权原 CSV，不能无授权直接重绑新 CSV；选择已有目标 app runtime 是必要而可审计的范围约束。UI 要写清“沿用 X 的既有授权；授权撤回同时影响共享此域的草案”。

## 唯一新增入口与参数边界

放在现有 `internal_api.mount()`，沿用 bearer identity、`scope_run()` 的 iid/rid 所属校验和 `INTERNAL_ENGINEERING_ONLY` envelope。

1. `GET /api/internal/instances/{iid}/runs/{rid}/extraction-options`
   - 服务端重新验证源，不只看展示 status；返回 source proof + fingerprint、tool/template/check 版本、来源范围、parameter_scope。
   - 返回同项目当前已授权的、初始 `origin=goal` registered CSV app 的 ID/name/draft fingerprint、绑定 resource ID/hash、共享 runtime 的简短说明。每项调用现有 load_draft 重新验证，只列现有 `resource.read ∩ data.aggregate_csv` 授权域，不调用创建/授权服务。
   - 源/目标必须内容 hash 不同（同 ID/hash 或原答案重绑不能作为新资料）。没有可用已有授权域则 `NEEDS_INPUT`，说明“需要一个已存在且已获授权的不同 CSV app”；不创建 Grant 来满足它。
2. `POST /api/internal/instances/{iid}/runs/{rid}/extract`，201；严格闭合 body：

   ```json
   {
     "expected_proof_fingerprint": "<64 hex>",
     "target_app_id": "app_<32 hex>",
     "expected_target_draft_fingerprint": "<64 hex>",
     "name": "<1..200 chars>",
     "request_key": "<1..100 chars>"
   }
   ```

   不接受 manifest/actions/candidate/runtime/resource_id/column/goal/limits/executor/replay/protocol/provider 字段；extra field 严格拒绝。源参数取冻结 source input；目标 rid、runtime 取目标已有 draft，调用者不能越权指定。column 作为新 app 的**运行输入**保留，不固化成源 column；目标资源绑定是**本次生成配置**，运行接口不能任意改 resource。

   返回新 app ID/fingerprint、source proof fingerprint、target resource hash、authorization domain、`generator=TRUSTED_REGISTERED_CSV_FROM_APPRUN.v1`、`model_requests=0`、`semantic_goal_acceptance=NOT_RUN`、`publishable=false`。模板自动识别严格由 source executor+receipt 决定，无能力自由选择字段。

## 最小来源验证与独立 oracle

建议一个聚焦文件 `src/sim2act/registered_run_extraction.py`，只实现这一注册 CSV 来源，不抽象新 worker/通用生成器。GET、POST、草案运行前均复用同一 `verified_csv_source()`。

- 定位 Run，锁 source 所属 project，重核 owner；`load_binding()` 串接 `runs → internal_run_bindings → internal_app_runs` 和 FrozenRunContract、request_fingerprint。iid 必须来自同一 binding；拒绝普通 F1/legacy/unbound。
- `runs.status` 与 `internal_app_runs.status` 均须 `SUCCEEDED`，两者 error 为 None，cancel_intent 为 false；拒绝 FAILED/PARTIAL/WAITING/PAUSED/CANCELLED/unknown/prepared 状态。不要接受“有部分 VERIFIED effect”作为替代。
- `read_release()` 核 consumed release approval/immutable snapshot/dependency lock；source candidate 必须 `origin=goal`、单节点 `data.aggregate_csv@1`、合法闭合接线，避免从已提取来源再提取造成递归依赖/循环。source goal 用 release 中 candidate.goal；队列通用 GoalSpec 的“Internal fixed Release result run”只记为执行 envelope，不能伪称用户目标。
- `data_rows()` 现有校验之外，精确选 a.id 对应单条 record，核 record release/version/schema fingerprint/data.result 与 a.output；核 a.result_version。核 `runs.result` 精确包含同 app_run/instance/release/version/receipt_ref。
- 唯一 `operations(run_id=rid, call_id=instance_result)` 必须 VERIFIED 且 tool_ref=data.aggregate_csv；intent 必须等于 `{tool: data.aggregate_csv, args:{resource_id:<source rid>, column:<frozen input column>}}`，operation fingerprint 必须等于 intent fingerprint。
- receipt **精确形状**与 `app_jobs.py:717-730` 相同：operation_id/status/app_run_id/instance_id/release_id/result_version/output_fingerprint/data/artifact_refs=[]/check_results=[csv.exact_integer_sum.v1 PASS]，不得出现 agent protocol、额外 artifact、替换 ID。不能只挑一个 PASS 字段。
- 在 source 原 runtime 和 current user 的已有授权交集中重新读取 source CSV；hash 与冻结资源合同、候选、output.source_hash 全相同；revision 仅现有逻辑版本 1。output.resource_id、column/count/sum schema、冻结 input 全相合。
- 工具重新计算读回须等于输出，再调用 `extraction.exact_sum_oracle(content,column,output)`：独立 csv.reader + 整数缩放 Decimal；不复用缓存/工具同算法当 oracle。保留现有 ≤1000 rows、每数 digits/exponent≤1000 和拒绝舍入规则，并沿用 read_data 的 CSV 资源限制。
- 冻结 proof 的 kind=`completed_registered_csv_apprun.v1`，含 source rid/iid/app_run/release IDs、Run version/fingerprint、binding/contract/release/candidate/input/output/receipt/record fingerprints、source resource/hash/revision、tool/check/template versions、`parameter_scope={creation:[new_csv_binding_in_existing_authorization_domain],runtime:[column]}`；目标 app ID/fingerprint/rid/hash/runtime 是接受请求配置，另存独立快照。不存模型私有推理或源旧答案为执行缓存。

## 候选生成、版本、授权与幂等

POST 在 project 锁内重核 source proof 与 expected_proof、目标 load_draft 与 expected_target fingerprint；目标 project 必须等于源 project，target runtime 必须是已存在非 project 的 appruntime，目标 rid 必须 CSV、hash 不同。用 `authorize_source()` 检查 current user+project runtime+目标 app runtime 的已有 resource.read/data.aggregate_csv Grant；检查包括当前撤权/过期/退休状态。

调用已有 `csv_candidate(target_rid,target_hash,"",source_manifest.runtime_limits)`，重用源合法声明式 contract/limits，目标 hash/resource lock 更新，生成新的 app/action ID，revision=1。candidate.goal 从可信源 release 冻结；manifest.goal_ref沿用可信源值，origin=task_run/source_run_ref=rid。用现有 task_proof 标记装 proof/目标绑定信息。精确校验 output schema、schema version、注册 tool/check version不漂移，预算不能增加。仅 insert app_drafts(runtime_id=target runtime) 与现有 task_extractions；不调用 persist_csv_candidate，不插 Grant/Principal/Release/Instance/Run/业务结果。

复用 `task_extractions` 的复合 PK(task_id=source rid,principal_id,request_key) 和唯一 app_id，不迁移/新增表。snapshot 用显式 `kind=registered_csv_source.v1` + proof + target/accepted_name + candidate fingerprint；apps.validate_source_family 增加这一受注册工具约束的分支。compile_preview 复用现有 task_proof 模板比较；validate_frozen_candidate 的 task_origin 分派按已验证 snapshot kind 精确走新 validator（其余仍走 local_tasks），拒绝 kind/executor 跨家族替换。新 validator 从独立请求/来源记录重构候选逐字段比较，不能仅重新 hash 自证。

请求指纹为 `{source rid,iid,expected_proof_fingerprint,target_app_id,expected_target_draft_fingerprint,name}`，不包含 key 和随机 app/action ID。同 source/user/key+同接受配置重试返回唯一 app/cached=true；同 key 改目标/name/proof/target version拒绝 VERSION_CONFLICT。缓存返回前仍重核来源和目标权限/版本、load_draft；撤权后不可通过 cached 放行。project 锁串行首次生成，事务回滚无孤儿 app，丢 HTTP 回执保留原 key 重试。默认候选不依赖原 model messages/session/replay；新执行通过现有内部 release审批→instance→enqueue→worker，生成新 AppRun/operation/结果版本。

共享现有 runtime 是本切片的明确限制：它不等于独立新授权域；撤销该域已有 Grant 会一起影响目标 app 和衍生 app。若产品要求每个衍生 app 独立 identity，则在“不新Grant/Principal”的边界下无法实现，需要另行授权范围，不能声称本切片已提供。

## UI 最小变化

在 `web/internal.js` 的成功 CSV run详情新增“将这次任务保存为可复用草案”；仅 options 验证成功后显示目标已有 CSV app 选择、名称和来源/目标 hash、参数/检查范围。agent、非 SUCCEEDED、普通F1 PARTIAL不显示按钮；API仍独立拒绝。POST 成功使用既有 refreshApps/showApp，不创建额外工作区。`app.js` task_proof展示按明确 proof.kind显示“来源：已成功内部 CSV AppRun；可信求和/独立精确数值核查；新 CSV 绑定+column运行参数；0模型请求；目标语义条件NOT_RUN；未发布”，不落入旧“本地合成固定任务”文案。

UI 绑定 token/project/source rid/iid/source version/target app+fingerprint 的 generation token；切换 app/project/identity 或轮询刷新不自动改用户当前选择/原请求 key。目标/名称改变生成新的 accepted-input key；请求已接受但回执丢失保留原 key 和选择，可重试，不能自动重发。源/目标失去授权清理可保护内容，用户重新打开才能继续。

## 验收：真正证明新输入执行

正例只经真实本地 HTTP + 已有 durable worker路径：已存在授权 A/B 两个 CSV app；A 内部 release/instance运行 column 得 SUCCEEDED；GET source options→POST仅填上述小body→新 app。关闭会话/重开并删前端状态，仅凭新app打开；B内容与 A 不同，用不同数字列的新输入实际后台跑到 SUCCEEDED，新 Run/AppRun/Operation/result_version，结果等于独立手算 gold和exact oracle，且不等于A源结果。检查 app/action ID 新、executor/schema/check/limits稳定，source_run_ref可信，target hash正确，Principal/Grant数量和全部既有Grant内容完全不变；生成阶段 Run/Instance/Data/attempt数量不变，model/provider调用计数0。

必须验的负例（不是镜像实现字段的测试）：

1. F1真实PARTIAL有VERIFIED求和回执、源 FAILED/UNKNOWN/OUTCOME_UNKNOWN/PARTIAL/已cancel，均不能提取；伪造status但无record/receipt也拒绝。
2. receipt换output/ID/version/check、intent改column/resource、源binding/contract/release approval或source hash变，错误来源重核失败；extra receipt/artifact/protocol拒绝。
3. 源/目标跨user或跨project、目标runtime只有read缺aggregate、任何一侧Grant撤销/过期、目标材料退休→拒绝且不写app/Grant。GET已列出后撤权，再POST/幂等重试/冷运行仍拒绝。
4. 旧expected proof/target draft fingerprint、新目标同源hash、agent目标/来源、递归task_run来源、非法空/非数值column/NaN/CSV错误。生成失败无孤儿；错误新执行留FAILED历史且结果表不追加。
5. 同key同body两次/并发/HTTP回执丢失只产一个app；同key改任一接受参数拒绝；丢回执后改名称不覆盖原请求。kind marker移除/替换agent或修改schema/tools/permission/limits不得让自改candidate通过。

所需测试可扩充现有 test_internal_api / test_internal_lifecycle / executor_family_provenance 并增加一个聚焦 registered来源HTTP模块；使用sqlite做快速事务/接口验证，PostgreSQL跑必要并发/回滚验证，不为这个只读同步生成接口再建worker或恢复模型路径。浏览器验收只需一次真实服务截图+DOM证据（成功入口、新草案来源、新输入结果、撤权隐藏），不得通过fixture直接insert衍生候选伪装UI生成证据。

## 可独立并行与剩余缺口

后端源proof/extractor/schema/幂等实现和HTTP负例可与 UI布局/文案草图并行，先定以上接口；已有browser导航修复/CI环境维护可独立工作，不改其脚本。最终真实服务浏览器验证须等接口合并、使用服务生成候选，不与该依赖并行伪称完成。此审查不执行这些工作。

更宽“真实任务→app”的关键缺口仍在普通F1：没有可信的整体成功验收版本/结果，正常完成是PARTIAL。若不接受内部CSV AppRun来源，下一步应先在原 Run contract范围内，为明确csv.sum任务加受限验收声明（资源/column/schema/check version），worker按可信intent+receipt+独立oracle记录具名验收PASS后才写SUCCEEDED；自由文本goal及混合/多工具任务继续PARTIAL。这需要单独具体接口和验收设计，不可在本提取器中推断自然语言成功，更不可为了提取改全局finish(PARTIAL)为SUCCEEDED。本推荐切片不做它。

## 本轮授权与并行实施安排

这是一份未实施的接口/验收范围，预算0不阻塞上述确定性来源驱动生成的本地实现；预算0仍阻塞实际模型自主生成/自由语义签收。先冻结API及shared-authorization-domain说明，再并行后端proof/extractor+负例与UI；集成后的UI必须由真实HTTP生成候选，不能seed新app绕开产品入口。当前浏览器导航修复与图像诊断另行闭合，不让fixedfixture循环代替此主线。若选普通F1来源，需先实现具名有限成功验收接口；不能把PARTIAL改成成功绕过它。
