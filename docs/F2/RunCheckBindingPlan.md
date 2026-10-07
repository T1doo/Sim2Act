# 可核验 Run → 有界检查 → 候选与受限 DAG（实施前）

2026-10-07，基线5671d0fdc4797d2cac0be475a9acdf46bf61f637；独立 dev/run-check-binding-local 与 /workspace/Sim2Act-run-check-binding。另一原生验收线仍测试567，不含本实现。只本地代码/测试/阶段证据/commit，不push、CI、LIVE，不改变真实身份、Grant、发布或准备器。

实际 V5 产品§4 P-B、§5 ActionSpec/CheckSpec 与阶段 F2 要求检查绑定明确任务输入输出和轨迹，且新输入形成新结果。当前 conditional_checks 是授权只读、调用者人工 Report 的有限核对；protocol A-S 的实际 output 是 obligations/case.CONFLICT，不能转换造一个 Report 再签。本切片新增显式 opt-in 的 bounded conditional-report 协议目录，不更改原四 exactJSON 目录、原 protocol.source、_source 或 ModelProtocol 的成功来源门。

## 最小实现路径

1. 新注册有界契约只支持现人工声明的 A-S 规则hash，公开目标仅为限定 Report 的逐规则条件/引用/决策/期限/例外结构；说明文字不在覆盖范围。输入是严格 Scenario（含显式 UNKNOWN）与当前授权资源，契约/目标/hash/输入指纹在入队时冻结。不接受 HTTP Report、candidate、gold、decision 或权限。新来源 API 在项目 conditional-runs namespace；同键绑定全部参数。
2. 复用协议 Run、显式冻结合同、claim/fence/heartbeat、Actual Attempt、resource.read/VERIFIED Operation 与不可变完成快照。源执行只接受 InternModel+MockTransport 注入；默认无 provider 仍等待资源。模型假回应必须手写 Report；不读取 gold 造报告。技术完成 Run 仍 WAITING_APPROVAL / semanticUNKNOWN，绝不伪 SUCCEEDED。
3. 检查端只从当前完整持久完成证据取得 Scenario/Report/来源；复核全部 Operation/Attempt/completion 独立锚、当前授权和材料实际hash，然后复用 conditional_checks 独立规则核对。events双锚封存 Run ID、fence/version、输入/成果/检查契约/目标/来源/完成指纹及请求键；同键重试幂等，错Run/旧报告/协调单行篡改不可冒用。
4. 仅完整有限检查 PASS、事实无 UNKNOWN、目标在精确声明覆盖域内的源可抽取 candidate-only。检查PASS不等于实际事实已核实、一般语义或 Run 整体成功。提取仍通过真实零网络 Mock wire 取得 JSON，再严格比较公共注册的 read→language DAG/Schema；该模板不含源答案或任意代码/URL/权限。候选与实际提取 Attempt receipt、源检查指纹/成果版本绑定，原通用成功提取入口仍拒 UNKNOWN 源。
5. 新 Scenario 冷运行绑定同 A-S 规则（新授权资料 ID 可为相同规则内容）；新规则hash、CSV、A-C不同政策不在本契约范围。复用有限 DAG 执行和授权网关，生成新的 Run/Attempt/Operation/完成证据，再独立检查；源 BLOCK 可得到新事实 ALLOW，但任何 UNKNOWN/未覆盖目标不能提升或作为提取源。候选不进入既有 CSV AppManifest/正式 Release。

## 数据与接口边界

优先复用 protocol_jobs、runs、events；不新增表/DDL。如需存储新实体先更新本Plan再实现显式迁移，API只CRUD。新条件目录的冻结/重核路径与旧四目录分支明确；原接口不能靠新catalog绕过成功来源语义门。所有回读/提取/冷执行重核 owner/project/runtime、资源bytes/hash、完整来源、契约版本与候选锚。

## 验收与审查

真实认证HTTP→独立 Worker/MockTransport→真实 read receipt→完成UNKNOWN→独立检查→候选→新事实冷 DAG→独立检查。正常680未审批BLOCK→500不要求审批ALLOW；未见501/缺收据/补齐不重期限/过期政策未知/审批未知/行程未知；错误引用/条件/决策/缺规则/重复/bool-as-int、跨用户/项目、撤权、资源/成果/trace/Attempt/check/候选篡改、旧版本/键冲突/错Run/旧报告及并发幂等永久负例。断言无 Principal/Grant 增量；无任意代码/真实模型/外部写入；默认provider不发送。

先专项 SQLite 和静态；自建唯一标签/端口 PostgreSQL 容器，专项、最小业务CRUD角色（不DDL）及适用完整工程回归，关闭并计数清理。源码可审后请父安排不同agent独立复核，保留真实失败日志，再冻结精确source/docs SHA本地commit。原生/像素NOT_RUN、真实语义/ownerPENDING、整体P-A/P-B/F1/AT02与发布未提升。下一片才讨论扩大公开规则/目标覆盖或新的完整真实模型批准。

技术来源精确口径：整体 Run 不可称成功源。只验证独立可信技术 completion：RECEIVED 模型响应、VERIFIED 读取、known 用量账本、完整 immutable payload/完成事件及当前授权。整体保留 NOT_ACCEPTED / semanticUNKNOWN / WAITING_APPROVAL；结果未知、STARTED、未决 Operation、FAILED/PARTIAL、缺完整成果直接拒绝。candidate-only 不提供运行/发布权；后续显式冷验证只能检验已授权假设事实范围，不能冒充已验证应用。
