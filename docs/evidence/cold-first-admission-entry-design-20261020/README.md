# 真实 first-admission / G0 局部入口：仅设计，构造阻塞

只读基线 `ada263ce4102a55c6ee9b54d3c85224561f6c51f`，诊断产品提交 `6301e19964bd4c309d98ec9f004a6e79d3b03958`。本轮没有导入产品、打开数据库、运行测试/producer/Worker/sender/模型、创建执行入口或启动新窗口；仅保存设计和独审。原完整失败及永久取消的旧 JS 双 actor 安装窗口均保持。

**结论：在“从新合成上下文开始即 sender/模型调用为零”的本轮条件下，找不到合法构造真实目标上下文的现有产品路径。入口 BLOCKED，不可启动。** 不能把 G0 本身没有发送，偷换成整个准备和验证流程零发送。没有用手填数据库、重签旧链、换时间/lease 或批准 DTO 解决这个矛盾。

## 唯一候选入口与停止位置

目标位置是 `natural_spec_runtime.advance_model` 已正常持久接收本次 Cold 原响应、归档、原 renew、fresh lock_live 之后，进入 `_cold_model_before(worker, c, current, graph_call, limits)` 的同一新事务/读取 epoch。它内部由真实 `_ColdTrialGraph.commit` 首次调用依次经过真实 `_prepare`、`_graph_run_context`、`_graph_pb_accounting`、`_graph_resolve_trial_source`、`_graph_pb_archive_chain`。五函数及下游真实校验不得替换、抽掉、缓存或以 unit stand-ins 组装。

若第一次原拒绝发生，保留同一异常与私有诊断后即停止局部入口；不继续 fail_owned/恢复/后续写入。若首次 commit 成功，不能把此返回当 G0 结束：仍须按原顺序完成 enabled、实际 cold receipts、已接收 Attempt 完整检查、parse/usage/schema/receipt、第二次 commit，及 `_cold_model_before` 正常退出的最后全图与期限检查。只有该上下文成功返回才是 G0 结束；紧接着、第一条 `update(attempts).values(status="VERIFIED")` 前停止，W5 不可进入。

这只是代码位置和要求，**没有已实现的可执行 harness**。现有 `advance_model` 没有一个接收“外部已验证 fresh G0 参数”的公共恢复入口；直接调用它先要走本次 sender。复制局部变量、反射栈帧、跳到函数中间、伪造 call/Attempt 或直接调用 coordinator，都不能作为同一个真实 G0 上下文。未来如果存在合法的新上下文取得方式，还须单独审查具体入口与停止控制；本设计不是启动 ACK。

## 为什么从空库不能合法构造

| 源码边界 | 真实要求与阻塞 |
| --- | --- |
| `natural_spec_runtime._ColdTrialGraph._prepare` | 读取同一批准合同的 generate Run、三份 production marker，当前 source/Generate 全账链、extraction/use/release、当前阶段批准；不是一个 RunCheck DTO |
| `pa_trial_dispatch._pb_prefix_source_from_facts` | Generate/Source 恰好五个 accepted 槽且未 halted、唯一 Source Run |
| `pa_trial_dispatch._graph_stage_accounted` | Generate 恰三份、Source 恰两份实际 Attempt；同合同/account/version marker；完整 slot/capture/wire/正文/用量，Source operation 为 VERIFIED |
| `natural_source_archives._graph_resolve_trial_source` | 原成功 Source 的实际 proof 与 extraction，完整原正文及当前授权；独立重建当前 StageAuthority，再与事前记录的 StageApproveInput 比较 |
| `pa_trial_dispatch._graph_pb_archive_chain` | 两份 Source 的 NS/controller 完整正文、capture、slot、原 request/response 严格交叉一致，receipt.verification 为 SPEC_PRODUCTION_CONTROLLER_ARCHIVE；Capture.provenance 为 SPEC_PRODUCTION_CONTROLLER |
| `natural_live_admission.approve/approve_stage/_approved` | 正常 API 重建当前来源/阶段，批准绑定确切合同；stage 必须在 QUEUED/无 Attempt/零 requests 时记录。旧批准不能改合同期限后沿用 |
| `production_trial_sender._dispatch/_captured` | public offline sender 不是生产 controller 的离线导入入口；production 只能走原私有 business continuation，Capture provenance 必须匹配 LIVE/生产 marker |
| 原 `advance_model` G0 调用点 | 自己的 Cold response 已接收和持久归档；正常全新流程到该边界实际有 Generate3 / Source2 / Cold1 六次 sender/Mock 调用 |

需要区分两个判断：五个函数自身主要重建 Generate/Source 账链，不能因此声称它们每一个都独立强制 Cold1；**Cold1 是原真实 G0 调用位置的前置**。即使退到仅内部 first-admission，前五个 production 收发证明仍不能在新空库、零 sender 条件下通过原正常流程产生。已有局部 synthetic_commit 仅验证诊断，不是上述 Stage/来源/批准证明。

原普通 dormant fixture 的旧 Generate/Source 不是本合同的 production 账链，也没有合法当前 Cold 阶段；它不能再当性能入口。旧 full 库是历史证据，且没有失败瞬间完整有限期限/局部变量；不得修改其时间、lease、fence、批准、provenance 或重新签 seal 后继续。新合同使用旧字节会改变 contract fingerprint/entity 和所有 scope/marker/slot/阶段/extraction 关联，重签不是保留原证据。没有发现无需 sender 的受支持生产 archive import/rebase 路径。

## 阻断、证据及资源上限设计

以下是**将来存在合法前置时仍必须满足的条件草案**，本轮不实现、不执行、不分配运行目录；当前实际执行预算为 0。

- 从入口最开始（包含构造阶段）阻断 `pa_trial_dispatch.request_captured/_journal_exchange`、`production_trial_sender._dispatch_business/_dispatch`、InternModel 同步/异步请求、MockModel.request，以及 httpx 真实和 Mock transport。任何触达都记录一次违规并结束，绝不返回合成响应或转成备用路径；不能仅用 no_real_http 宣称 sender=0。阻断补丁只负责拒绝，五个真实生产函数及原鉴权/SQL/回调不能替换。由正常流程取得新上下文会先撞此阻断，这正是本设计的不可达原因。
- W5 要有独立不变量：G0 正常返回后立即退出 caller，且本次 G0 读取连接上任何 INSERT/UPDATE/DELETE/DDL 在执行前拒绝；不可把事后查“没有 typed 行”当作 W5 没进入。具体 harness 尚未存在，故还没有动态保证或启动资格。
- 原 TTL1800 / Run300 / lease30 / RPM gap60 秒、7槽 / 输出7168 / 总预留192000 / wire32768 / paid cap0 一律保持。不改真实时钟，不停原检查，不用更长外层预算续产品期限。
- 若未来仅执行已经合法取得的单个 G0，建议外层 wall **120 秒**，另只预留 TERM 后5秒、KILL后5秒收尾，总上限 **130 秒**；第一次原拒绝或 G0 完成即提前结束，不自动重试。不能把需要五至六次、相邻至少60秒的全新 sender 前缀塞入此预算或另列“免费准备”隐去。
- 独占目录总上限 **64 MiB**，启动前至少保留64 MiB可用空间；执行器须以有界 stdout/stderr/元数据写入器计量总量，超限停止、不删除旧证据腾空间。只保留一个当前 fixture DB、原输入与原响应归档、有限阶段诊断、退出记录及哈希，不增加四个损坏库/恢复矩阵、深层字段轨迹或第二次 probe。具体磁盘约束尚未实现，当前没有实际可执行预算。
- 记录冻结 source/tests/依赖、五函数身份/源码字节、上下文正常创建与实际批准沿革、原全量证明/DB及原 wire/body、命名 finite/end/stop/RunCheck/已有Run快照、五阶段浅计数、同 epoch/transaction、执行前后资源与清理回执。只读检查旧证据不能补签新上下文。已有精确深 observer 原件不改写；本局部设计不另装逐字段 deep observer，若父侧另要求保留旧 observer，须如实列出其非零开销，不能声称零扰动。

失败清理只能管本次独占进程组：正常退出或首次拒绝后关闭本次 client/Store/事务/heartbeat；未知退出先核身份/结果，不重发。外层超时对精确 owned PGID 依次 TERM、最多5秒后 KILL、再最多5秒确认；拒绝信号或进程仍存则标 UNKNOWN，不按名字杀服务、不换方式绕过。保全原异常、DB及原件哈希后才处理本次可重建临时副本，不改失败终态、不恢复旧 Worker/Run、旧服务、过期批准或 JS 窗口。没有 PG、系统权限或凭据动作。

## 原计划仍可独立推进的一个实际产品缺项

只列已在原计划中有依据且当前代码确实缺失的一项：**已有 `resource.read → 两个 data.aggregate_csv` 双求和应用，改用同项目另一份既有注册、当前已授权的单 CSV**。

依据原 V5 分阶段计划 F2-T03（提取变量/稳定逻辑、消除固定路径依赖）、AT-10/11（冷会话、未见输入新 AppRun/新结果），以及既有双求和和单列新材料复用产品。`csv_material_reuse.recipe` 当前显式拒绝 TWO_SUM_VERSION，`definition` 仍只接单 column、只改 nodes[1]；`csv_dag_instances.validate_input/apply_input` 已支持原材料上的两个稳定节点 columns 映射。因此缺的是双列新材料合同与接线，不是新算子、双 CSV 比较、材料注册、自动迁移或权限扩大。

此外 target_for_schema 仍比较单列目标草案 schema，`csv_dag_instances.source_snapshot` 的 material_reuse 分支显式 `not dual` 并只保存标量 default_column。实现不能仅删除 recipe 的一条拒绝；双结果来源 schema、双列 intent、实际运行与后续 Release/实例保存须一并冻结和核验。

最小产品范围须先冻结两个稳定节点的列意图、目标既有单 CSV 的真实 hash/graph/当前授权与双结果 schema，保留原来源当前授权、一跳转移、冻结预算及所有写前重核。沿用已有工具/执行器/身份/Grant，不新增或恢复权限；不依赖 G0、sender、模型或完整 PB。必要验证是独立 Fraction oracle 对两个结果、新 AppRun/冷回读、旧 Release/实例/结果不变、幂等/同键异参、无权目标/输入拒绝，以及一条旧单列新材料回归。

这是一项可独立推进的工程缺口，**本轮没有实施或测试**，也不把它提升为完整“不依赖旧源”或全平台 AT10 通过。已交付的记录采纳和本轮诊断不重复列为缺项，不为凑数另造需求。

源码位置与哈希见 [design.json](design.json)，独审见 `independent-review/`；本设计只签可达性与边界判断，不签执行、性能或 PB。
