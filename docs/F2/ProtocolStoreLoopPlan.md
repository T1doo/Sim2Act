# 通用模型协议最小 Store / HTTP / worker 闭环

2026-10-06，起点本地7beb20d（未push）。用户授权继续离线接线；先完成e16和独立验收review架构审查，条件APPROVE后实施。不push/CI/LIVE，不发材料，不新增角色、Principal/Grant、业务/外部写或发布。此阶段不增加固定任务family；独立注册的合成语义oracle是验收资产，不是runtime生成答案。

冻结架构：新增两表protocol_jobs/protocol_reviews，由原显式controller migrate初始化，API/worker仅CRUD；复用Run/冻结合同/claim/lease/fence/heartbeat/Attempt与真实resource.read Operation+VERIFIED回执。三phase source/extract/cold独立namespace；默认provider缺失WAITING_RESOURCE，不fallthrough旧F1、不自动调用Intern。测试仅现InternModel+HTTPMockTransport注入，Replay不变LIVE。普通F1 PARTIAL/FAILED/UNKNOWN不提升或作为来源。

source/cold接受前冻结已注册服务端contract_id/version/asset hash和精确输入资源/hash，公开输出schema可发送；gold/量表只独立评估端可读，不变项目resource不给runtime。HTTP不接caller gold/decision/PASS/candidate/provider Replay。现own_project owner只拥有发起评估权限，不能提交自己判断的PASS；服务端注册checker逐项独立核验成果，错误/缺证据/矛盾保持FAIL/UNKNOWN。契约不能事后挑选或降低。

worker已知技术完成先WAITING_APPROVAL/semanticUNKNOWN，result snapshot一次原子冻结，记录completed_fence/version、输入/输出/attempt/Operation指纹。独立review精确绑定该snapshot、acceptedcontract/hash、checker/version、实际评估端与认证owner，当前权限/版本重验、幂等追加。只该新namespace的完整证据及检查PASS可成为SUCCEEDED可信来源；评估不调用过期lease的guard、不追改旧F1状态。

extract必须从当前persisted新源Run+review PASS加载，模型给有限read-only工具/语言JSON DAG，实际accepted extract响应/Attempt和不可变plan fingerprint锚定。编译是带版本依赖与权限边界的内部计划，不伪兼容现CSV AppManifest或正式Release。cold绑定已授权不同材料，按精确plan创建新持久Run、新结果、独立待验；没有旧答案缓存或新权限。

稳定tool call ID必须绑定原Attempt/tool_call_id；cold工具ID绑定编译step。真实dispatch回执和安全model response逐项相符。每个job发送前文件scope slot和数据库Attempt均持久占额，pending未知停止该scope，不reset/retry；跨三个job的共享14-slot/64k总账尚未接通，未来LIVE前必须补齐。无PG长事务包网络。private reasoning不存入公开响应。

验收：真实本地认证HTTP入队→独立worker claim→source待验→独立checker/review→extract/compile→新材料cold→新待验/验证；同键幂等、错义务/矛盾/缺证据、篡改、版本/fence、另owner/project、撤权、PARTIAL、unknown attempt恢复、不重复派发、gold不可进入model请求。先SQLite和独立review，新增表显式migration/PG CRUD角色验证适用；原生browser/Windows本轮NOT_RUN。保留失败与未测边界，本地commit封存后交父检查。
