# 通用模型协议：统一离线结果与执行门

2026-10-06；前置[V5差距评审](V5ModelExperimentGapReview.md)。本轮按用户授权完成离线代码/材料/负例与独立审查；只本地提交，不push/CI/LIVE。不是一份可立刻外发的脚本许可。

**后续实现口径**：本文以下预算与缺口清单记录最初独立协议阶段。
现离线 HTTP/Worker 已接持久源、注册独立 checker、受限编译、共享 DB
14/64000 总额和状态恢复；本次又补离线 controller handoff、完整固定冷模板
oracle、项目协议入口和双形态零网络预演。文件 sidecar 按 Run/scope 独立，
六阶段/6 秒限制不能称 DB 全局策略；精确出站 body 校验与统一实验策略仍缺。
最终事实与保留阻塞见[本次计划](ProtocolExecutionReadinessPlan.md)和
[证据/预算/数据说明](../evidence/protocol-egress-readiness-20261006/README.md)。
提案仍未批准，LIVE 为 0；注册合成 checker PASS 不等于 owner 语义签收。

## 已完成的最小协议与复用范围

- [model_protocol.py](../../src/sim2act/model_protocol.py)：`complete_task`实际provider工具反馈循环；`extract_candidate`一次真实provider可接的有限DAG候选；`run_candidate`新资源绑定/新语言调用，无旧答案缓存。默认disabled，runner必须有require_scope/call/halt，当前批准交集read回调及独立verifier必须注入。不同模型输出决定步骤/参数/语言节点；服务端只验证范围、闭合schema/接线/预算。模型任务结果不是源码，不执行代码/URL/自由SQL。
- [model_budget.py](../../src/sim2act/model_budget.py)：现InternModel完整wire序列化，显式实验scope和发送前durable reservation，14全局slots、6阶段3/1/3分配、每次1024输出、完整8000chars/10000bytes、全局reservation与actual各64000、阶段reservation/actual源冷24000/提取8000、每阶段300秒。未知/失败/未完成STARTED全局停止，无自动retry/repair；授权每次重查且消息复制后发送。模型返回候选JSON锚定持久receipt，cold重验；ledger halted也禁止纯工具路径。
- 原InternModel身份/响应结构/usage规则直接复用；API/worker/迁移/身份授权原代码不改，无新Principal/Grant/表/DDL。sidecar补充实验全局计数，不能替代现Attempt/RPM/Run。
- [四包材料与manifest](../evidence/model-protocol-preparation-20261006/materials/README.md)：A单文档条件义务，B双材料冲突判断；B含SUPPORTED/CONFLICT/UNKNOWN及例外，不能全拒答。四包总各661/681/719/804 UTF8bytes含公开指令；31引用和6资源版本hash独立核对。gold/量表仅验收侧，owner未签，四包真实语义UNKNOWN。

## 本地证据与限制

[root回归](../evidence/model-protocol-preparation-20261006/local-regression.log)145PASS/1SKIP/1依赖弃用警告，新budget19+protocol39独立58PASS；ruff/mypy通过。独立主动复现的预算wire篡改/actualusage/schema0、candidate替换/attemptnull/identity1/停门旁路均修复并永久负例复验；[失败记录](../evidence/model-protocol-preparation-20261006/failure-history.md)不覆盖。POSIX实际锁/并发已测，Windows锁与耐久NOT_RUN，没有新原生浏览器验收。

[完整wire预检](../evidence/model-protocol-preparation-20261006/wire-preflight.json)8个InternModel+MockTransport发送体，max4542chars/bytes、reservation29201；不是实际请求或tokens费用。模拟候选和公开placeholder响应只用于协议几何，未加载gold；不能认为真实模型候选/成果同样大小、1024输出足够。每一真实请求仍须原发送前门检。14是两形态source<=3/extract<=1/cold<=3的总批准提案，当前8个样例仅走2/1/1各一次，不承诺14个任意真实序列均可在64k内完成。

## 一次性外发与预算提案（当前0，全部待批准）

供应商仅Intern官方现transport，精确`https://chat.intern-ai.org.cn/api/v1/chat/completions`；model=`intern-s2`，stream=false，无redirect/models探测/额外连接调用，间隔>=6秒。最多14真实请求、每次输出<=1024tokens（最坏输出14336tokens），每次完整输入<=8000字符且<=10000UTF8字节；累计known tokens与保守byte-envelope reservation分别<=64000，哪个先到先停。输入界限相对旧2000字符许可是明确待批变化，旧待批2/3次不叠加。

**确切数据**为manifest的四个package，按阶段只发送所选source或cold包的列明文本/hash/版本/逻辑ref/公开goal；包选择与既有项目资源ID映射、发送schema/prompt版本及真实公开工具/model反馈摘要在controller接受前一起冻结。source与extract不读cold文本；cold只携带当前新材料与接受候选必要instruction，不能夹带源答案。外发manifest只允许上述字段；gold/量表/隐藏预期/真实V5/其他repo或项目/凭据/private reasoning禁止。来源反馈不可为缩体而删权限/回执或语义内容；超体则拒绝，不补新请求。

本提案只read与内部结果账本，无artifact.save_text或业务/外部写、不扩大Grant。若现应用身份缺足够read交集，暂停报缺口，不自动授权。批准必须绑定私有持久ledger路径与scope，六阶段共用不可重置ID；失败、未知计费或STARTED遗留保留slot并全局停发，不退款、不重新发旧slot。使用量未知不记0；当前已实现sidecar操作门，运行前仍须接原Attempt/Run占额与恢复流程。

**成本**：未核实账号计价/剩余额度，没有可靠货币估值，不能声称免费。仅能给输出14336tokens及全实验64000 combined-known/reservation上界；真实tokenizer/输入比例/实际成功次数未知，mock usage不是估价依据。若账号提供输入/输出单价，可在批准前用此上界算最坏货币额；上游未知计费立即停，不把失败当零成本。

## 可执行顺序与尚缺的真实集成门

1. 本地可立即执行上方preflight和58专项：全部MockTransport，不读取真实env或凭据。核manifest字节/hash、denylist、scope、候选接受回执、负例；gold独立审草案不等于owner签收。
2. **代码前置尚缺**：可信controller把项目实际当前授权/注册read派发与VERIFIED Operation/readback接回调，并持久绑定真实源Run、goal/input/accepted responses/attempts/receipt/output/独立语义签收。协议的TEST-only verifier不能换个标签当这层，旧F1 PARTIAL原历史永不追认。真实语义证据缺失继续UNKNOWN/PARTIAL、拒绝提取。需要新增表时先单列显式迁移/CRUD方案；此轮无表。
3. **运行前置尚缺**：protocol Candidate与现ActionSpec/AppManifest编译/内部AppRun/HTTP/worker的可信接线、取消/heartbeat/进程恢复和全局budget稳定复用；当前返回executable_by_existing_apprun=false。不能仅删除Replay guard，不允许语言节点变任意代码。原真实adapter可接但产品调度尚不可直接运行。
4. 独立owner确认gold/语义量表、scope与以上统一预算/精确外发manifest；代码和本地负例再review。本次审查不是这些批准。通过这些门后才source新Run→独立验收→extract已核来源→候选/版本确认→cold新Run，按两形态分别计分；任一门失败全局停，保留证据。
5. 汇总真实usage/未知/介入/失败及清理。两形态P-B实验成功也不替代P-A、Win11/F1/完整AT02/正式发布或完整V5签收，不加部署。

本轮代码使真正provider可注入的最小协议不再停留在方案，未声称现产品端到端语义已完成；上述可信持久源/调度接线和用户审批为下一真实执行阻塞。

2026-10-06 bounded controller update: `protocol_experiment.py` now enforces a sealed six-stage cross-Run identity and shared settlement clock; `protocol_egress.py` plus serialized Intern sender validate the full actual envelope and durable wire seals. Prior statements that these two offline gates are missing describe the earlier snapshot. The gated offline executable package and exact remaining production-activation code boundary are documented in `ProtocolExecutionGatesPlan.md` and `../evidence/protocol-execution-gates-20261006/README.md`. LIVE remains0; fixed public-template extraction is not real learned-reuse/owner-semantic acceptance.
