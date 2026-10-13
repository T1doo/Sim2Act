# 非CSV最小源任务：技术规格Markdown→带出处清单

2026-10-06，状态PREPARED_OFFLINE / REAL_TASK_NOT_RUN。只准备合同、离线oracle和执行协议，不新增产品feature。本轮AT02四次授权已用尽，当前模型预算0；下列未来模型/输入/写入上界均待单独批准，不查询models或凭据。源自[单项提案](NonCSVTaskProposal.md)，离线资产见[准备证据](../evidence/noncsv-execution-preparation-20261006/README.md)。

## 范围与原设计对应

首批只处理原V5《平台产品设计》§10.1原450—458行，9行/822UTF8字节，四规范段原452/454/456/458。输出一份保存的checklist JSON；MD报告由已校验JSON确定性渲染，仅是派生视图，无第二保存回执。先完成这一真实源任务，才能讨论应用提取。不给未见输入通用成功承诺，不生成网站/代码/外部发布/通用writer。

原设计§1.3资料整理与带来源内容生成，§4 P-B先完成任务再保存输入/输出/工具/检查，§7真实书生选择工具并消费反馈，§10.1发布/实例/版本/数据边界，§12引用定位不等于语义正确；阶段计划F2-T03/AT10要求从已成功任务抽取并在新材料冷会话运行。这份源任务准备对应这些要求的前置，**不等于P-A生成、P-B提取/复用、发布或整个AT10完成**。

## 固定输入与输出合同

输入是项目内授权的逻辑resource_ref；资源内容精确等于选段原文，format=md/version1。控制器本地验证完整文档SHA、选段SHA、原行号映射与来源版本，保存来源manifest；模型只读该822字节选段，不发送整份V5或其余repo材料。首批范围不扩至原提案4096字节/40行；后续扩大另冻gold和完整发送体。绝对路径/URL/凭据目录/跨项目资料/扫描OCR/外网检索一律不支持。

保存JSON顶层仅contract_version/source/rules；source精确绑定resource_ref、document_id、document_version、document_sha256、selection_sha256和line_start/end。四rules各仅rule_key、单段原line_start/end、完整逐字quote、obligations。版本、字段、类型、顺序、数量与允许标识严格校验；未知字段/重复JSON键/多义务/漏义务/旧答案均拒绝。MD由版本化固定模板从通过JSON渲染，不接受模型附带HTML/脚本/URL或任意模板。

`contract.json`为**开发方gold草案**：四规则必须覆盖不可变Release/实例数据历史/预览隔离；发布依赖版本/CAS/Run固定版本/逐动作动态权限；升级与回退兼容/破坏迁移拒绝；发布回退与数据回退及补偿分离。材料owner/验收者需在模型发送前确认这些原文义务及禁止推断。模型只收到源绑定、输出schema和未分组受控标识词汇，不收到gold的段落→义务分组、引用答案或离线成品。词汇约束是验收合同，不能以手工gold作品当模型提取。

## 严格oracle与负例

机器oracle先拒绝未知字段/版本/类型及重复键；绑定同项目/当前source/version/hash/原span；四项无遗漏/重复/乱序，quote逐字等原段，obligations精确匹配预冻gold，MD逐字等确定性renderer。保存工具的VERIFIED仅证明持久写入/readback，不证明语义成功。

语义oracle由材料owner/独立验收者先冻结gold，再逐项核对模型是否从正确原段提取完整义务、没有扩大权限/承诺、没有把回退说成数据恢复或外部效果撤销。仅quote存在/JSON结构正确不计语义通过；机器通过后仍须记录owner确认及检查版本、执行者/时间、输入/输出hash和失败项。新文档/新版本必须重新冻结独立gold，不能用本段gold去判断所有技术规格。

实际离线1正28负通过：错误resource/document/version/hash/选段hash/范围、bool假整数、额外source字段、漏规则/重复/乱序/未知rule、错误quote/span、漏/多义务、虚构quote、额外输出字段、MD不一致/脚本、缓存42、空规则、错合同version、重复JSON键、非法/超长JSON。此结果只校验开发gold合同，不是模型提取或owner语义验收。

未来执行还要真实本地负例：无token、另一owner/project/runtime、撤销source或artifact任一交集、过期grant、读后source version/hash变化、退休source、save call_id重复同body/不同body、预算越界、错误模型/残缺JSON/模型第三轮要求。拒绝必须发生在相关外发/写入前；重复保存只一成果，篡改拒绝，失败/unknown不转成功。当前这些非CSV产品集成负例NOT_RUN，不能用离线JSON负例冒充。

## 请求数、发送范围与未来预算

现有F1 `resource.read`与`artifact.save_text`正常最短成功链为 **3次真实模型请求**：1选read→实际read反馈；2基于原文提取完整JSON并选save→实际save反馈；3消费保存反馈并报告精确artifact_ref。至少两工具，0repair/0自动retry，失败即停，不预先保证三次内成功。若首轮多余工具/第二轮仍要求read/第三轮仍调用工具或回复无效，按已批上限停止；不能偷加第四次。完整P-A/P-B生成与冷会话复用没有现成非CSV注册接口，预算尚不能据此定为3，应在接口和新fixture明确后另预检/申请。

离线使用原真实链的公开system消息、当前完整工具schema、合成固定IDs及开发gold模拟正常三轮，实际httpx.Request纯序列化大小为：

| 请求 | 完整字符 | UTF8字节 | 性质 |
| --- | ---: | ---: | --- |
| 1 目标/合同/工具目录 | 2530 | 2782 | MOCK发送体，尚无模型结果 |
| 2 加原文及真实格式的read回执 | 3613 | 4357 | MOCK发送体，无真实read Operation |
| 3 加完整JSON保存调用及save回执 | 6184 | 7400 | MOCK发送体，无实际保存或推理 |

JSON模型成果1529字符；当前artifact.save_text上限8000字符可容纳本草案。三轮worker保守byte-envelope合计17719，不是tokenizer或真实费用。实际模型content/call_id/JSON可能更长，发送前仍按完整体检查。

建议未来一次明确申请：仅此9行原文/目标/source metadata/schema/实际回执与模型公开消息；**最多3次Intern-S2请求、每次最多1024输出tokens、max_tools2、max_repairs0、max_total_tokens24000保守envelope、run_seconds300**；固定endpoint/模型身份及≥6秒间隔；完整体最多8000字符且UTF8最多10000字节，必要字段不省略。当前平台输出cap1024不变；是否足够完成JSON不能在无模型测试时确认。原AT02的2000字符/512输出许可不适用，第一轮已超旧输入上界，必须单独批准这些明确变化后才可发送。上限不是用量承诺；未知usage继续占额并停发，全球跨所有Run的3-slot持久flock/fsync守卫不重置，无models查询、无自动重试、不变代理/TLS/身份。

## 有界执行步骤与最小实现依赖

1. 本地确认scope/gold/材料外发与预算、最小artifact写授权；准备新owned PG+显式controller迁移，API/worker CRUD角色，不在API建表。主体/runtime/项目隔离；只保留目标source.read和项目内artifact.save_text交集及必要成果readback，禁止生产业务写入。保存脱敏source/权限/版本、当前源码与初态，先做零模型本地授权负例。
2. 正常API接受一次新intent，来源只含精确选段resource_ref；独立worker使用有限预算，持续核source与receipt授权。记录前三个发送前安全形状/hash/次数，模型返回严格验证再派发注册工具；真实输入发生变化或来源无法绑定即拒绝，不靠补写gold继续。
3. 输出JSON必须先由严格检查器验证再作为可信成果保存。**现有generic F1 save_text只验证文本/权限，不做此oracle**：若先保存未经语义验收的候选，只能标待验候选，不能声称可信成功源。最小后续实现需注册固定checklist检查与renderer/来源依赖，输出绑定source proof并持久化检查结果；复用现有受限执行器，拒绝任意代码/自由SQL/外部插件。是否需要新增持久表先核当前存储；如确需表，必须显式迁移及CRUD角色授权，不由API隐式创建。
4. 三轮完后保存两工具真实回执、实际JSON与规范MD派生视图、来源hash/version及独立oracle结果；新Store冷读，另一owner403、source授权不被扩大，同call_id幂等/篡改负例真实执行。真实使用输出/receipt/hash匹配，usage/report/失败和unused预算如实记录。
5. 源任务只有可核查检查通过并形成可信成功证明才可进入P-B。现有F1 PARTIAL/semantic NOT_RUN不满足该P-B成功源门；不能据AT02操作通过把这两Run包装成来源成功。之后另阶段提取source参数/range/rule类别/输出格式/稳定逻辑/model节点和版本化dependencies，在真正未见材料与冷会话创建新结果、坏输入/撤权拒绝；不回放旧清单、不手工替模型拼候选、不自动发布。
6. 独立审计实际trace与oracle/来源证明，owned cleanup/PID/端口/PG/temp及证据hash；原V5/历史LIVE/失败不改。当前无真实执行/no feature/no新增Grant/无发布；工程实现、输入发送与剩余预算均仍BLOCKED/NOT_RUN。

当前可审阅交付是计划、开发gold合同和离线检查，需确认项是独立gold/具体材料外发/未来预算与发送上限/最小写权限及最小注册接口实现范围。文档正常本地保存，不push或重跑CI；当前真实请求新增0。
