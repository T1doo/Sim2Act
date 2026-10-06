# 共享持久预算与安全状态恢复

2026-10-06，起点 fd259942b85cc2d67bef184d7afb10fb682974fd。用户明确授权继续并行闭合：旧DOM完整SQLite失败同顺序/父版本对照，以及三阶段共享持久总额、未知停止和安全恢复。仅本地开发、回归、提交；不push/CI/LIVE，不发业务材料，不增加产品Principal/Grant/部署。注册四包oracle的通过不代表书生真实模型语义验收。

## 实施前冻结

固定服务端protocol namespace/mode共享pool，所有该协议source/extract/cold Run、owner、project与进程共用；客户端不选择pool，不建池、提额、退款、清账。旧F1 Intern路径不属于本实验账本，不谎称已覆盖整个系统所有模型调用。显式controller initialize默认offline/live均0；合成test_only环境明确初始化offline拟议14、64000总token envelope，live恒0且原接口继续拒绝LIVE。新增表仅原显式migration创建；缺账本不自动seed。已有协议Attempt但缺旧账核算时拒绝另开预算，不改旧证据。

project→Run→旧quota→pool一致锁序，fresh auth/lease/fence再次确认。一次短DB事务同时插Attempt STARTED、唯一slot并占额；提交前不能调用provider，事务不跨网络。未闭合STARTED挡住其他发送，即使另进程/项目/新Run/键/sidecar也不能绕过。原调用只能当前有效fence下把slot和Attempt同时记完整RECEIVED；未知usage/模型不匹配/失败或双账不一致保留占额并停池，无退款。发送与DB commit不能原子，接受保守falseunknown，不承诺网络exactly-once成功。

安全恢复只读取/固化持久状态，不续跑协议、不重发、不注入答案、不造completion seal或PASS。完整可信原子结果保持原等待验收/终态；未发送须同时没有Attempt、Operation、pool reservation及completed记录，最多标PAUSED等待明确新claim。任一STARTED/单边账/已收到但未完整completion结果停止，等待人工定位/验收配置。Store.claim的协议过期分支必须隔离通用F1自动QUEUED恢复；旧F1执行不改。完成后pause/cancel导致版本不匹配不能回写旧version绕过proof。

旧DOM保留原704PASS26SKIP1FAIL；父7beb20d和当前fd25994隔离同NODE_PATH/默认顺序对照。正常poll保留；受控回执时序负例只验证可能路径，不倒推原失败原因。若必要修复，只精确等待当前IID/RID/终态/读回完成；不得sleep/扩timeout/禁poll或force可见假通过。

## 验收门槛

独立架构及最终实现审查；真实PG跨进程末槽竞争、重启、新阶段/新sidecar拒发、DB占额后/sidecar后/返回未commit后崩溃；current auth/fence/version/篡改/幂等/跨项目负例。原真实HTTP与受控DOM时序都验证，同顺序父对照保留。root完整SQLite和相关PG回归，记录失败及范围，owned进程/DB清理后仅本地commit。不因孤立DOM重跑PASS或固定响应oracle PASS宣称完整修复或真实模型验收。

覆盖更正：上一阶段131个所谓PG专项中，test_protocol_jobs自有fixture硬SQLite（39项），API不建表测试也显式SQLite（1项）；其中真实PG仅91项，40项SQLite。原历史报告保留，本阶段明确更正并将jobs fixture改为可隔离PG，不能沿用131当作全PG验收。


实施终审追加必要门槛：真实PG发现单tx多个expiredprotocol恢复在取得pool后又锁下一project，与active Worker.reserve形成40P01死锁（原探针1PASS表示成功复现缺陷）。修改为每个expired Run独立project→Run→pool短tx，commit后再下一个；常规claim tx不带pool锁。用同schedule永久PG负例和独立修后复验确认，再重新冻结完整回归，保留修前完整结果和实际死锁事实。


最终冻结的 SQLite 全量已实测741PASS34SKIP0FAIL637.12秒；PG最终完整回归仍待退出。单独专项：独立恢复+永久三Run并发15PASS23.58秒（真实PG）；跨进程末槽与五崩溃点6PASS26.70秒（真实PG）。完整结果和清理另见本轮 evidence/result.json，不能把专项代替完整。


最终锁修复冻结版 PG配置全量 **774 PASS / 1 SKIP / 0 FAIL**，1475.06秒，775 collected；2个既有依赖/字段警告。PG配置全量含纯单元与显式SQLite测试，不把774全部称真实PG；真实跨进程/三Run并发/角色专项另列。结合SQLite741PASS34SKIP637.12秒及最终独立两报告，此有界离线工程切片通过。删容器前owned PG残test schema/role均0；仅本轮容器已移除且inspect确认不存在，私有credential env/state目录已清除。真实模型请求0，LIVE预算0；无push/CI。最终本地提交hash在父线程交付回执，证据见protocol-shared-budget-recovery-20261006/result.json。
