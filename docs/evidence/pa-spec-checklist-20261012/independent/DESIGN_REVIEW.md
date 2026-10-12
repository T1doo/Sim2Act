# 技术规格 → 带出处约束清单：有限 P-A 接入独立设计审查

2026-10-12。结论为 **STATIC DESIGN REVIEW / DYNAMIC NOT RUN**。本轮只读当前代码与原提案，未执行产品测试、模型、真实网络或旧数据库升级。可推进显式新家族的有限合成闭环；不能删除旧家族禁用判断来扩大其能力。本报告不签新实现已通过。

实际工作树 `/workspace/Sim2Act-pa-provider`，HEAD `4b227895d9df7347cd11f2b8e4be725bcbe930dd`，分支 `dev/pa-spec-checklist-20261012`，读取时 Git clean。root 是唯一产品写入者。源码/测试/pyproject 425 项和初次直接审查的 20 项文件 SHA 见 `source-before.json`；另核已有 `spec_checklists.py` 与其测试片段的 SHA 见 `source-supplement.json`（两项均在原 425-map 中）。未写仓库、旧 owner 工作树或既存证据。

## 1. 已有合同的明确接入限制

| 真实接口 | 当前行为及不能直接复用为新能力的理由 |
| --- | --- |
| `goal_applications.py:198–226,461–488` | prompt 明确 `one_step=True`、`text.literal_evidence`；候选顶层字段和解析只接受一个固定 literal action/当前材料/完整 Goal。保留这些门。新 selector 必须走自己的 policy 和严格 parser。 |
| `goal_applications.py:357–413,895–929` | 已保存真实 read 回执和失败诊断，可重建发送消息；计数只接受一个 VERIFIED `resource.read`。新 check feedback 会改变阶段和真实 operation 集合，不能冒用旧 approval。 |
| `generation_approvals.py:36–40,61–119` | 现 namespace、scope、consent、3 requests/1 read/1 repair 和 charge index 都被精确封印。新版本 scope 必须包括新 family、工具/检查 registry 和阶段预算，旧 approval 不得激活新 family。本轮 LIVE allowance 始终 0。 |
| `contracts.py:45–52,450–568; preflight.py:19–173` | Limits 的工具硬上限 4；executor/check/dependency registry 封闭；图已有类型边、有限条件、拓扑和预算检查。增加新操作须精确注册并核 effect/permission/check，不以忽略 registry 或扩大所有 registered tools 绕过。 |
| `apps.py:190–250` | 显式 family 已先分流，普通路线只允许单 CSV/literal/agent。可在其前加一个独立有限 family 分流，保留旧路线。 |
| `text_workflows.py:57,165–191` | 只支持完整 canonical read→lookup_a→lookup_b→report，不是可选 DAG。可以复用其回执、binding、current-head/lease/CAS 模式，不能把 canonical factory 生成的图称为模型决定的图。 |
| `app_jobs.py:637–652,927–994; lifecycle.py:44–90` | 普通 compute/preview 不运行任意声明式多节点图；分别按 literal/agent/CSV 处理。需要新 family 的小 step adapter 与 preview/worker hook，不能只新增 manifest 后让旧 compute 误执行。 |
| `tools.py:333–431` | `write_text_artifact` 在 caller 事务内授权 project `artifact.save_text`，真实插入 resource、内容 hash、派生 read grants，回读内容；generic save 没有清单 quote/schema 检查，且 artifact 的 format 目前固定 `md`。JSON 文本持久化可复用，但格式和内容类型应诚实标明，若要 `json` 格式必须显式有限适配。 |
| `pa_material_bindings.py:61–101` | 现适配只封印 model literal 来源，独立 task kind/namespace/binding marker 防降级。新图和新材料需要自己的来源证明与相同强度的标识门，不能改 namespace 就取得执行权。 |
| `spec_checklists.py:25–125,152–237,240–332; api.py:765–773` | 已有显式 `synthetic_` header 与 `[label] MUST/MUST_NOT` 规范整行检查、完整 quote/覆盖、严格 candidate FP、真实 artifact 冷回读和安全 MD renderer，可以复用纯 oracle。其 POST 仍要求 caller `candidate_json` 并同步写 task 行，没有模型/DAG/Worker/app 证明；不把这条旧 route 的 SUCCEEDED 当本轮新 P-A 闭环。 |

原 `docs/F2/NonCSVTaskProposal.md` 与 `NonCSVExecutionPlan.md` 的关键约束仍成立：JSON 是唯一保存成果，MD 从其确定性派生；实际引用定位与语义正确分开；gold 不给模型；通用 save 回执不能证明语义；新材料重新授权；真实 V5 外发没有从本轮合成授权中取得许可。历史文档的真实预算、gold 和 PG 前置不作为本轮合成 allowance，也不阻止已授权的独立 SQLite 实现。

## 2. 建议冻结的新家族和预算

建议新显式 selector，例如 `spec-checklist-dag.v1`，新 generation policy/scope 版本和独立 task origin kind。名称为建议，不是既有实现。只处理项目内授权 UTF-8 TXT/MD，建议沿原同族候选约束 ≤4096 bytes、≤40 行；只有明确规范语句、有限标识词汇、确定的句子边界。路径、URL、源码、动态代码、自由 SQL、OCR、外部业务写入不支持。

首片最好只支持无歧义句子/规范段。若支持多句一行或跨行，必须先定义版本化切分和精确 offset，而不是将任意 regex 的结果宣称完整语义。原换行、空白、Unicode 原字节/字符映射、起止行及起止 offset 必须可核对。文档级 version/hash/原行映射只有真实 source manifest 提供时才能写入；普通上传资源没有整个原文档 SHA 时不能补造该字段。

最小选择是直接保持 `spec_checklists.source_checklist` 已支持的 labelled 合成 Markdown 范围（LF、每条完整规范整行、显式 MUST/MUST_NOT、≤16 条、header 自带 synthetic 文档版本），重用其 quote/覆盖 oracle，先把真实模型形状反馈/DAG/Worker/新材料闭环接起来。若当前产品目标明确要求无 label、自然标点句子，必须新 checker/version，保留旧 CHECK 行为；不能在旧函数里放宽 grammar 后让旧校验编号继续表示相同合同。即便 labelled source，模型仍须自主选择图/分支，并有真实检查反馈；不能只是服务端直接调用 source_checklist 然后存一个 canonical 单节点 app。

可在现全局工具上限内冻结以下独立计数：generation 最多 3 个 synthetic provider responses，最多 1 次实际 source read 和 1 次实际 candidate-check operation，最多 1 次失败后的修订；冷 runtime 最多 4 个本地节点操作、0 Attempt/0 request/0 repair。read/check/纯变换也产生真实 operation/intent/check 回执并计入所在 Run 的工具数；不能只计 write 来隐藏实际步骤。最终保存事务的内部 schema/quote/readback 检查是该已计数操作的固定 postcheck，不能伪装成另一次模型工具调用。

保持现输出 ≤1024 tokens、总 envelope ≤64000、Run ≤300s 等平台硬界。它们是拒绝上限，不保证三个 response 足够容纳完整图。应在后续离线序列化测完整 schema/Goal/read receipt/candidate/check feedback；超过 cap 即停止，不删除回执字段或默默涨额度。原 literal provider cap/consent 不变。真实 provider 分支本轮不启用；synthetic façade 与真实 Intern 结果须不同标签。

## 3. 让模型真正选择有限图，而不是选择固定图的名字

新 compiler 验证有限属性：仅封闭 operator refs/version；1 个 bound source；节点 ≤4；唯一 action/step/binding；类型/依赖边精确；无环、无悬空或未用节点；唯一成果 sink；每个必需分支产出都到达 sink；source 全部来自实际 read 及其 sealed metadata；所有写只能最终受控 JSON artifact；不得把源码、quote 答案、材料正文或自由表达式放进 action 常量。

四份完整 ActionSpec + manifest 可能容不下现 1024 输出 token cap，不能预先承诺该形状可生成。建议模型返回版本化、封闭的 compact DAG recipe，只含节点/operator/有限 kind/类型化输入边/输出；服务端仅展开已注册 schema、server IDs 与预算。保存原 response recipe FP 和其确定性唯一展开的 candidate FP，重新展开必须一致。模型决定 graph，服务端不能替换、补齐失败分支或挑 canonical 图。`check_candidate` 工具可收受限 `candidate_json` 字符串并 strict_json 解码，保留 `tools.validate_call` 的 string-only 既有假设；如采用 object args，只在新 scoped parser 明确支持，不放宽所有旧工具。

可供反驳的四节点内最小设计是：

* 图 A：read → extract_all_normative → assemble → checked_save。
* 图 B：read → extract_kind_A 与 read → extract_kind_B → checked_merge_save。

图 B 是 read、两提取节点、一个 sink 共四节点；sink 内固定做合并/去重、schema、完整 quote 与范围/覆盖检查及真实保存回读。图 A 的 sink 做同一检查。operator 列表、kind 词汇、输入输出 schema 是注册合同，模型决定节点数、分支组合、类型选择和边，不是服务端替它产生完整 canonical graph。允许的不同图必须有不同真实依赖结构，至少两种合格图与拒绝循环/漏边/未用节点证据；仅换 ID、标题、排序或 canonical template 的一个 enum 不足以证明本任务要求。

另一可行实现可以更窄，但必须仍满足上述真实选择标准。不要求引入一般 DSL 或大 executor。可直接复用 `csv_dag.resolve/decision` 等类型化边帮助函数；新 step runner 按实际拓扑就绪集合运行，不能沿 `text_workflows.STEPS` 或固定数组索引冒充 DAG。必需提取/检查/保存不得通过条件 SKIPPED 而取得 whole-task PASS。

冷执行的 operator 对新 read 结果按模型保存的有限规则重新提取。规则可以是注册词汇/句子类型/合并策略，不能是训练材料的固定 line numbers、段落→gold 义务映射或旧 quote 常量。模型在实际 read/check feedback 后决定并修订这套结构；服务端只验证其有限能力和结果，不用 gold 替模型写 candidate。

## 4. 生成与反馈的最短有界闭环

建议三阶段：

1. 第一次 response 从新 family 工具目录选 bound `resource.read`；当前权限与 FrozenGoal/source 校验后产生真实读回执。只允许冻结目标资源。
2. 第二次 response 消费这份真实回执，提交自己的 compact DAG recipe 到版本化 `check_candidate`。check 执行有限编译与该图在已读 source 上的 dry evaluation（save sink 只算待存 JSON，不执行写），保存 operation、recipe/candidate FP、输入 source FP、版本化检查结果和失败诊断。禁止写 artifact，也不泄露 gold。
3. 第三次 response 消费实际 check receipt/diagnostic，给最终完整 recipe（或停止），修订后服务端重新机器检查和唯一展开。最多一次修订，不再第 4 次发送。最终 candidate 的模型 Attempt 与 check 依据必须精确关联，不能把没有读第二轮 feedback 的预置模板记作修订。

compiler/check 不把 semantic gold 当提示内容、工具输出或纠错诊断。quote/schema/公开词汇/图结构错误可以给具体诊断；gold 的正确义务/分组/遗漏答案留在独立 evaluator。失败后的 provider raw、check red、修订记录均保留，不能只留最后 candidate。

本轮 synthetic model façade 可以根据实际收到的 messages/tool receipt 选择不同图并对实际失败诊断修订，测试应证明它没有候选 JSON 作为用户输入。它仍只是离线受控 response 行为，不等于真实模型质量/自主语义判断。没有真实模型运行时，真实模型能力为 NOT_RUN。

最终候选保存为 PREVIEW/PENDING 小应用，经用户对精确 candidate FP/完整 Goal/新 family/读写权限批准，才能形成内部 Release/Instance。不要把 generation 的 PARTIAL/candidate-ready 当 source task SUCCEEDED 或 P-B 可信完成证明。原家族 owner 状态不继承，新家族不追加 owner 外围能力。

## 5. 完整 quote、机器检查、语义 gold 与实际保存

机器合同建议冻结 JSON 顶层版本/source/rules，exact keys、严格类型、duplicate-key 拒绝、数量/大小界、稳定 rule IDs、唯一 spans/确定顺序。source 绑定实际资源 ID/version/hash、实际文档映射；每项完整 quote 必须等于真实已读源的完整句子/规范段切片，不能只验证 quote 是 substring。遗漏、截断、错 offset/hash、重复句子、无来源义务、未知 schema/额外字段、旧答案均拒绝。

按明确词汇和切分规则检查“覆盖该有限形式的规范句子”属于机器合同；检查技术含义、隐含义务、遗漏风险、禁止推断或现实可用性属于 semantic gold。若输出只是原规范句子的完整 verbatim constraint，可以声明出处/有限抽取通过；不能把其称为语义完整技术规格理解。每份 unseen 合成输入有单独冻结的独立 gold，gold 不传给 façade。结果至少分为 provenance/schema/persistence/semantic/owner 五项，semantic UNKNOWN 或 NOT_RUN 不自动改为 PASS。

`checked_save` 必须先用真实 source 复核完整 JSON，再在已有 project artifact 写授权的同一事务中复用 `tools.write_text_artifact`，核真实保存内容、资源 hash、JSON 解析后 canonical FP、检查 refs、local_effect/operation/intent 和 artifact pointer。保存 receipt 数据不只是 caller 传来的预期值；独立 verifier 必须能重新读该资源并复算内容/检查。MD 只由此已验 JSON 渲染，无第二保存回执。

现 helper 会派生新 artifact 的 owner/runtime read grants，这是现有 artifact 的受控效果，不是任意旧源授权。必须只对该次操作真实创建的 artifact 加必要 readback，不能用 caller 自报 ID 替代 local effect。save-and-readback 过程中和事务末尾再次核当前 grants、native Goal/source、instance revision/data CAS、lease/fence/deadline/cancel；任何末门失败回滚该事务内 artifact/grant/effect/typed append。先前完整已 VERIFIED 步骤可以保留审计，但不得产生 terminal SUCCEEDED/typed-success 或让 prefix 看作整图通过。

对 Outcome Unknown 不重发相同效果，更不换 key 重新保存。原 key GET + 已有 receipt/reconcile_readback 恢复；同 call_id+同 body 至多一效果，不同 body 冲突。FINAL 阶段新的 UI intent 必须绑定原 request/key/fp/identity/Goal/material，并核独立 app origin；所有 async 后上下文代次失效则忽略 late outcome。

## 6. 冷新材料、授权前私有读取与持久来源

新源绑定是一个新精确批准：已保存图 FP/原生成来源元数据 + 当前 target resource/hash/version/新完整 native Goal + 项目/owner/runtime + requested `resource.read`/project `artifact.save_text` + 预算/软件 FP。旧 scope 既不能带来新源 read，也不能带来写 permission。现交集不足时明确新批准/拒绝，不能自动加用户 grant；只有显式批准的 app runtime 可以获得精确派生目标权限。

持久化新来源 metadata/seal 使用既有 namespace/paired ledger，不必加一般业务表。图/版本/完整 Goal/target scope/current grant seals 不可变；保存 origin 中训练 source/hash 是来源历史，不能被作为 cold operator 的结果输入。cold job 应从 target 的实际 read 重算；检查 Run resource refs/contract/独立 ACCEPTED header/current binding/Release/AppRun/typed 对应关系，而非只看 candidate 自报 namespace。

和已验来源门相同：先按 owned 项目/instance/run 的 ID/JSON scalar 标识获取 target scope，authorize 当前 owner+runtime，再读取完整 source content、FrozenContract、Goal、model raw/history/candidate。分别覆盖 prepare、confirm、preview、create Release/Instance、enqueue、claim、inspect GET、cold history、worker node、final commit。独立 ACCEPTED/ledger kind 提供防 marker stripping 的另一个锚；缺全部标识不能降到普通 CSV/literal fallback。未知或损坏来源拒绝；停止/撤销只能用无 body 的 metadata 路径，不借恢复读取正文。

cold 证明应关闭原 TestClient/Store/model façade，创建新会话/Worker，仅给新 target source。至少一个未见文本的内容、hash、规范句子位置/数量与训练 source 不同，逐项核实际新 quote 和新 artifact content，actual Attempt 表为空，旧结果/typed/artifact 字节不变。若宣称旧材料删除后仍可复用，还需要真实 SQL private-cell 屏障证明旧 resource/Run.context/result/intent/receipt 未读取；未做该额外声明时也不能让 cold job 使用旧输出回放。fixture answer 缓存、Replay.responses、fallback_42 或 training gold 均不得作为 cold 输入。

## 7. 最小 hooks 与后续必要验收

建议小范围修改：新 family module 承担 compiler/check/step adapter/source bindings，并尽量复用既有 spec_checklists 纯 oracle/renderer；contracts 精确 policy/registry schema；goal_applications/generation_approvals/API/Worker 的显式版本分流；apps.compile_preview/source family + lifecycle.execute/read/run/record verification + app_jobs.enqueue/load_binding/process 的新家族 hook；复用现实际 operation、intent、resources、internal Release/Instance/typed 和 grants。tools 保持 generic 三个工具语义，纯 family check 不获取额外资源权限。避免复制完整 provider、覆盖旧同步 labelled task route 或重写全局 DAG 执行器。

后续有限实际验收至少包含：

* 模型 façade 得到真实 read/check 回执、一次实际失败→修订；保存两种不同合格 DAG；所有候选从 response 来，用户输入没有候选 JSON；失败 history 完整。
* 严格 quote/span/hash/schema/duplicate-key/截句/漏句/外部 ref/错误类型/循环/漏边/隐藏节点/超 cap 拒绝；真实检查输出与 counter/Attempt/operation 账本一致。semantic gold 与 façade 输入/feedback 隔离。
* 真 SQLite/HTTP/NoModel cold unseen 输入实际 read→多节点→checked save→回读→typed append；独立复算；旧结果/对象/人工锁保留；原 key GET 冷恢复不重发。
* source 或写 grant 撤销、Goal/source 版本竞争、lease/deadline 临界、取消和迟到结果在 node 与最终保存/typed 之间拒绝且无本事务部分修改；unknown 不能错误通过。
* 权限前私有 cell 校准：故意整列读命中、限定 ID 投影许可、foreign/revoked 路径相关 private cell 0；分别剥离 candidate/ledger/ACCEPTED markers，全部剥离仍不得降级。
* generation Request/Charge/Settlement 旧合同回归；旧 literal 与 fixed four-step 图行为不变；新权限不能扩大已有 LIVE scope。

## 8. 当前可推进事项与未验证边界

没有发现阻止已授权合成实现的设备前置。真正必须先冻结的选择是句子切分/规范词汇、可接受非 canonical 图集合、read/check/repair 阶段及真实计数、最终 checked artifact 效果/权限、semantic 标签与原 key 恢复。它们属于当前核心合同，root 可在本授权范围内收敛后实现，不需要因历史真实外发计划重新请求同一合成授权。

`csv_logic_reuse.implementation()` 仍 hash 全部实现 Python 原字节。新增/改变任何 Python 将使现 `text_software_qualification.json` 的精确 70-map 资格失效；必须按明确有限 delta 重审并维护完整精确 target map/qualification pin，保留原 old anchor/CHANGED 字节和逐 instance 明确批准。不能把 4b 的旧审查结果迁移为新源码的动态 PASS，也不能扩大按文件名 CHANGED。该维护仅保障已批准旧兼容门，不扩 owner 能力。

本轮未执行测试，PASS/FAIL/SKIP 不适用（动态计数 0）。REAL provider/model/费用、真实 V5 外发、现实业务效果、人工语义验收、PG、Windows、native browser、wheel build/install、旧源码升级为 **NOT_RUN**。setuptools 缺失的历史包装失败保留；不安装依赖来掩盖。CI/永久禁止 browser 路径/原取消精确安装窗口没有尝试，后者仍 NOT_VERIFIED。后续 SQLite、进程内 HTTP、离线 JSDOM 和 synthetic 模型形状可独立完成允许的核心，不提升上述边界。

审查封存时再次核 425 项源码/测试/pyproject：差异 0；HEAD/分支/Git 状态与初核一致。实际实现 70 个 Python 文件原字节 fingerprint `f3ae7559431c110462fa43aa433e7e16a81750f1c90a4b756b9c1964c0bbf95d`。只读设计证据见 source-before/source-supplement/source-after/review-result；没有启动任何测试进程。
