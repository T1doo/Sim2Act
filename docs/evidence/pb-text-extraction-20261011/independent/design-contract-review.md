# 有限非 CSV P-B 只读合同独审

本轮仅设计/源码读审，未执行新候选、pytest、Worker 或页面测试。基线 e17d7c44098492745b23a57adaa715adb490119d，22 个所读路径与 HEAD 同字节；没有读取旧证据树。根代理为唯一产品写者。

V5 §4 P-B 与 F2-T03/AT-10 要求独立来源入口、明确输入/输出/工具/检查、清除会话及一次性路径依赖、未见与错误输入和冷会话。一次成功只能证明有限已声明逻辑，不能证明一般语义泛化。本轮可认领 `registered_tool text.literal_evidence` 的 TXT/MD 完整字面匹配行引用：资源≤4096 UTF-8 bytes、≤64行，trimmed 非空 term≤80字符，匹配≤16行；模型请求0、LIVE allowance0、正式发布false、semantic UNKNOWN、真实人工语义 NOT_RUN。不能关闭完整 P-B、AT-10 全平台或原 F2。

## 最小合同与复用

1. 来源仅本人同项目真实持久 `INTERNAL_APPRUN`，Job 与 AppRun 均 SUCCEEDED、error=None、cancel_intent=False；明确没有 UNKNOWN/PREPARED 未完成效果。来源 Release 冻结 draft 必须为已独立核验的 P-A `goal_application` 文本应用，不接受预览、PARTIAL、普通 F1、Replay/agent、CSV、DAG、导入手工清单或已提取应用递归形成来源。当前来源读权限仍有效。
2. `app_jobs.load_binding` 可复用 Job/AppRun/请求/RunContract/Release 关系；`text_run_checks.verify` 可复用 input、完整 literal output、typed record、exact operation intent、完整 VERIFIED receipt 和当前 source oracle。另在提取边界检查取消/所有未知操作及纯工具计数。纯文本 AppRun 实际不创建模型 Attempt，要求所选 Job 的 Attempt 数=0，而非伪造模型执行证据；其上游 P-A 的实际 Attempt/wire/read-receipt/event/history 由 `text_apps.verify_origin`/`goal_applications.verified_candidate` 正常验证。
3. 先以实例/Run 归属元数据定位和锁本人项目，再核当前源和目标 `resource.read` 的主体+runtime权限，才读取受保护 Attempt、input/output、receipt、record、来源证明。所有选择局限精确请求对象；拒绝外主体、外项目、错实例/Run/Release 的读操作，不扫描旧私有历史。拒绝日志只保留公开错误/元数据。
4. 目标使用同项目一个已有授权文本应用的既有 runtime；`existing_runtime` 与 `authorized_read(...resource.read...)` 可复用。`apps.authorize_source` 是 CSV 专用，不能复用其额外 `data.aggregate_csv` 需求。新资源 ID 与新内容 hash 均不同于原源；TXT/MD 范围满足同一有限工具。不新增 Principal/Grant、不扩大权限或算子。沿用同一授权域意味着撤销共享 Grant 将同时影响所有使用该域的应用，应在页面说明。
5. 新 app/action ID 由服务端分配。复制已验单步字面逻辑、schemas、映射、check 与 limits；只替换明确声明的数据 binding、permission resource、resource dependency/hash、ID 和 `origin=task_run/source_run_ref`。独立 task marker 与 candidate 在同事务写入。不得复制 `goal_application` 生成 marker、旧 app ID、旧 owner/Release 批准、旧 result/output/原文缓存或 Replay。
6. 完整原 GoalCard 作为来源冻结记录保留，包括约束/验收/未决项。其原 resource_refs 是原任务 provenance；新运行材料来自新 manifest binding，不能静默改写原目标或把新材料说成原 GoalCard 已验收。若新目标合同需要改材料/版本，必须另行版本记录。新 app/Release/instance 的 owner=PENDING，不继承任何旧 ACCEPT。现 `owner_acceptance.base` 只支持 goal_application，可以明确新 P-B 不支持该人工入口而保持 PENDING；无需在此扩大 owner 实现。
7. POST 绑定 source proof FP、target draft FP、名称与原 key，取得项目锁后重验全部实际来源/当前授权再提交；同 key 同完整意图只产生一个 app，同 key 改意图409。即使缓存命中也重新核验已创建 app 的独立来源与当前权限。确认损失或未知不自动重发；新增精确原 key GET 恢复，未知 key 不建立应用。GET 必须只读，历史回执不自动恢复失效许可。
8. 冷 Store/Worker/新 AppInstance 使用既有 normal `app_jobs`，创建新的 Job/AppRun/operation/typed result_version；新 TXT/MD 与不同 term 得到新 hash/引用行，空匹配可正常成功。错误输入保留 FAILED history，不能返回原结果。隔离证明：提取本身除 app+独立来源记录之外没有 Run/Attempt/业务结果/Grant/Principal 写入，源实例的数据与 owner ledger 不变。

## 实现必达接缝与风险

- `apps.py:validate_source_family` 当前只识 CSV/agent task marker；必须新增明确文本 kind，拒独立表 marker 删除/改 kind/冲突/候选 marker 剥离和自重签后降级。
- `text_apps.py:compile_text` 当前只允许 goal 且 source_run_ref=None、闭集无 task_proof；P-B 应有独立闭集分支而非放宽任意 origin/多 marker。
- `apps.py:validate_frozen_candidate` 当前 literal 总调用 `text_apps.verify_origin`。需根据独立 marker 决定 P-A/P-B 验证，不能靠可改 candidate 表面字段决定信任家族；同时覆盖 load_draft、freeze Release、cold AppRun、inspect、恢复缓存。
- `text_run_checks.verify` 本身没有拒 cancel_intent 或附加 UNKNOWN Operation；不要把其返回当作完整提取资格。它检查选中 output 的 oracle，但要在外层证明实际该 Job 为零模型纯工具。
- `registered_run_extraction.py` 的框架可复用项目锁、请求/target FP、事务和来源重验，不可直接复用 CSV oracle、aggregate permission、候选生成、marker kind 或 proof scope。
- `web/internal.js` 旧 registered 恢复通过再次 POST、只比较当前字段值且 showApp 未传 selectionCurrent；新文本入口应 GET-only 原key恢复，单调 read/selection/edit 代次保护 source Run/instance、target/name、project/token、workspace/app/nav ABA。每个 await 与外层 catch 都核资格，精确响应 appId/FP 与恢复记录关联后再显示；不能迟到夺焦点或覆盖新选择。
- 现面板 CSV 文案与 app origin 展示只认识 completed_registered_csv_apprun。应明确新类型/范围/PENDING/无新增权限，真 HTTP GET 加载的全部 JS/CSS/HTML 源哈希要与封版源码一致。

## 应测拒绝矩阵（建议，尚非测试结果）

| 类别 | 有限注入 | 应有结果 |
|---|---|---|
| 任务完成资格 | QUEUED/RUNNING/PARTIAL/FAILED/CANCELLED/RECONCILING；Job或AppRun error；cancel=True | 明确拒绝，不生成 app 或来源记录 |
| 未知效果 | 附加 UNKNOWN/PREPARED Op、STARTED/RECEIVED模型Attempt、非零模型计数 | 不提取、不重发、不伪造纯工具证据 |
| 身份范围 | 外 owner/project；错 iid/rid/AppRun/Release 指针；target为外项目 | 拒绝，SQL不读取外对象保护内容 |
| 来源家族 | 预览、F1结果、bounded_agent、CSV/DAG、多step、手工清单、P-B递归源 | 范围拒绝，不启用兜底 |
| 来源证据 | RunContract/binding/job/input/result pointers、完整 receipt/intent、typed record/schema/version、source bytes/hash、check/citation被改且自重签 | 精确来源重验失败；新与缓存路径一致拒绝 |
| 上游生成 | 删除/更改GoalCard source、独立generation marker、Attempt wire/raw/read-receipt/GA seal 或计数 | 拒绝，不信任候选表面指纹 |
| 新材料 | 原resource、同hash不同resource、CSV/JSON、过4096bytes/64lines、未授权/撤销/过期、runtime不属于既有同项目域 | 拒绝；source与target授权均必要 |
| 时间与并发 | options后源/target版本或Grant改变；两个同key并发；同key名称或target改变 | stale拒绝或唯一一个精确 app；无重复写入 |
| 来源防降级 | task marker删一侧/改kind、candidate task_proof删/改origin、自改executor/goal/binding/permission并重签 | load/Release/Worker/inspect/恢复均拒绝 |
| 原key恢复 | unknownkey、其他owner/instance/source key、错回执app/FP；源/target后撤权 | GET无副作用，不恢复授权，不自动POST |
| 冷输入 | term缺字段/错误类型/空白/超长/额外键/>16匹配行 | 新 FAILED history，源与已有结果不变 |
| 冷有效输入 | 新content/newterm/零匹配 | 新Run/Op/record及准确source hash，非旧缓存 |
| owner隔离 | 源已ACCEPT、新app/Release/instance、后换新材料/版本 | 新owner PENDING/不支持旧合同；不复制旧记录 |
| 真页面 | source/target/name编辑撤销ABA；导航/instance/run切换ABA；旧成功/旧错误；丢POST响应后GET恢复 | 精确当前app可见；旧请求失去资格；零自动POST |

最终验收分列实际 SQLite/Worker/API、真 HTTP 资产/JSDOM可见动作、受控坏响应与调度。模型仅已有显式合成来源，不把 mock 变成真实模型或人工语义证明。PG、Windows/native、真实语义/owner、完整 P-B、完整F2与完整256历史耐久/性能不在本轮；不扩大既有执行器。
