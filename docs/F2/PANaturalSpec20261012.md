# P-A 未标注短规范：目标驱动模型节点与待验清单

接续 `259f583eba6dd6c5580834878da6bd3cb1f648a7`，独立开发分支 `dev/pa-natural-spec-20261012`。原标记规范家族保持；本切片不要求 synthetic 标题、规则标签或 MUST/MUST_NOT。只使用自造中性 TXT/MD 与合成传输，真实请求/费用均0，未读取凭据。main/core/CSV/原owner草案不写。

## 有限产品合同

来源为单个已授权项目逻辑资源 TXT/MD，UTF8≤2048字节、≤40行，不接收文件路径或远程URL。源文本按原字节/hash冻结，语义分类不由关键词、正则、开发gold或源预标签提供。完整当前原生GoalCard（约束与最多16人工未决项）由模型节点实际消费。

新生成家族 `goal-natural-spec-application.v1`，应用 namespace `pa-natural-spec-app.v1`，recipe `natural-spec-recipe.v1`。真实P-A sender的合成响应先选择实际resource.read，再提出完整节点/边及样例抽取，调用实际spec.check_candidate消费引用/结构反馈，最终同一候选或一次修订。用户不写候选JSON。样例答案只留在受保护模型历史；应用定义只保留recipe、声明的schema/prompt依赖与样例指纹。

注册节点为 resource.read、model.spec.all/model.spec.requirements/model.spec.qualifiers、spec.merge_evidence、spec.verify_citations、artifact.save_text。模型选择1或2个抽取节点、其任意有限稳定ID、依赖与端口；可选择单节点覆盖，或2节点并行/后一节点读取前一抽取及真实检查反馈后补充。两个节点须经合并且保留两个原结果；模型负责结构化事实和关系，服务端只展开固定工具/schema/caps。没有任意代码或自由工具。DAG至多6步；模型节点单次请求、最多2节点，纯工具最多4，global4请求/4工具/1024输出/64000总封顶/300秒与原lease不提高。

每个模型事实有稳定ID、kind（requirement/condition/exception/open_question/unclassified）、说明、一个或多个原文char span+quote及目标ID关系。条件/例外引用相应requirement，无法确认关系保留UNASSIGNED；open_question没有自动resolved状态。模型输出完整保留，合并不可删除首节点中的条件/例外/未决项。未覆盖的原文片段显式列出，完整原文始终进入待验成果。因此出处、结构和原文保留可以核验；含义、遗漏、错误分类和scope关系准确性仍UNKNOWN/NOT_RUN，不以引用覆盖冒称语义完整。

最终JSON保存 source/hash/坐标、全部原文、模型事实及关系、未覆盖片段、原生人工未决项、机器引用/结构状态、语义UNKNOWN与owner PENDING。8个合并事实封顶；最终JSON≤既有8000字符，超出不截断、不丢项、不写部分制品。MD只从核验JSON派生、安全转义，不有第二保存动作。

## 默认关闭的实际模型节点

运行不使用旧样例答案。每个新材料的模型节点从实际resource.read回执和该目标完整Goal构造完整请求，复用Worker的Attempt/不可退款reservation/quota/fence/绝对deadline机制与Intern实际序列化sender。当前仅store.test_only+mock模式+显式httpx.MockTransport注入可执行；无注入默认关闭，拒绝先于模型reservation/dispatch，不以普通MockModel或客户端offline_replay兜底。当前测试中的requests是合成协议槽，真实请求和费用0。

每次发送前重验当前身份/项目/runtime、源/hash、GoalHead、完整绑定/Release/instance、预算、worker/fence/lease/stop；STARTED/unknown仅读恢复不重发。原始响应/usage/model identity/精确wire与独立事件锚保留，再解析和验证；错误quote、错模型/usage、截断、未知工具、取消/撤权/版本/迟到响应不能成为VERIFIED或保存。节点语义不能由机器追认为正确。

最终resource JSON、局部grants、effect、完整receipt/intent、typed data、instance CAS、Run/AppRun终态保持原同事务。入口与最终原生成审计byte digest比较保留；还核本次模型Attempt/响应/锚及实际receipt，不放宽旧防私有读取、旧未知结果、预算或租约。无关对象/原数据不修改。

## 页面与新材料复用

页面选择自然规范家族，展示完整Goal、模型计划、实际样例事实/条件/例外/问题和机器/语义状态；明确预览与仅此app在本项目保存出处核验、语义待验JSON的同意。样例预览仅读已收到的历史，无新模型/业务写。新材料绑定仅替换明确源/Goal/身份slots，保留原模型recipe；绑定预览明确MODEL_EXECUTION_REQUIRED，不能假算自然抽取。保存后实际模型节点重新抽取，结果与旧源不同；旧答案不进入新prompt。POST未知只原key GET恢复，保留原编辑/身份/项目fence。

## 实现复用与验证

新业务codec/引用核验在 natural_specs.py；runtime sender/模型历史在 natural_spec_runtime.py。扩pa_spec_apps现有保存与scope/receipt框架的显式family分派，沿goal_applications与Worker现有ledger，不另写通用执行器。旧labelled业务算法、原anchor/CHANGED及资格算法保持；完整源变化后只追加精确新软件资格，未知来源和旧approval不自动迁移。

正测采用至少两份中性无标签短规范（条件、例外、未定决定变体）、至少两种模型recipe（单/双节点、并行/顺序）与新材料冷worker；人工固定gold仅外部断言，不进prompt/检查器。负测包括引用错误反馈修订、语义漏项但不得语义PASS、遗漏片段显示、关系无分配、合并删项、错schema/工具、预算/identity/usage/unknown、前后Goal/资源/授权/fence变化、末保存审计和rollback、完整16人工项及页面原key/迟到。

独审只写本任务workspace证据目录；作者/独审原失败/中断与源码前后图完整保留。使用SQLite实际worker、TestClient HTTP与离线JSDOM，不跑PG/Windows/native/已拒browser/CI/真实升级/真实模型/费用/完整P-A/P-B。所有新临时夹具直接在本任务workspace root，不自行escalate或删除未知临时数据。

完成后单独给最小真实验收授权提案：精确Intern模型/官方端点、仅中性合成材料类别、完整wire上限/请求及token上限、零付费前提、合法凭据入口的已核事实与未核状态。当前只提案；不读取凭据、不触发请求、不借已用AT02授权、不购买或配置账单。

## 已实施的审计末门补充

新Run的created_at和原绝对deadline另封在accepted binding（指纹仍受Run与独立scope保护），模型reservation再绑定run_version/created_at/deadline。收到原始响应后先只写owned Attempt及接收锚，保持parameters不变；当前授权失败时错误收尾只投影标识与状态。操作写与失败历史写均精确限定原Run、instance、Release与request指纹，错误链接只记录原Run错误，不污染另一scope。

模型节点最后一个回调后再重读live合同、精确version、原deadline、原审计和本次完整账本；VERIFIED不允许有REJECTED锚。最终保存入口与出口比较本次Attempt/参数/完整raw/usage/所有NS事件及未发生自身变化的Run metadata/context。SQLite事务边界及发送/收到后的既有heartbeat保持30秒lease；过期lease不续，原绝对deadline不延。页面用candidate内opaque sample seal核实际sample_nodes，再独立重算完整来源SHA、Unicode scalar出处、保留项和固定UNKNOWN/PENDING展示。
