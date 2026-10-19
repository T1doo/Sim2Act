# P-B 原合同的生产控制器接线

基线 `c4f9a532c7ab428abccaf0ecf748398690e789bf`，普通开发分支 `dev/production-trial-stages-20261018`。本轮只完成已存在 P-B 原合同的工程接线；固定账户来源缺失和精确软件资格不匹配继续阻断真实调用，不增加 executor、Grant、凭据、来源回调、数据库表或 LIVE 许可。

## 事前冻结的阶段映射

| 原阶段 | 原合同及当前事实 | 使用既有控制器的变化 |
| --- | --- | --- |
| generate / 3 槽 | 原 trial generate key、第一材料及完整 Goal、原项目 runtime；实际三次生成 Attempt | 同一 ProductionTrialBinding、sender、journal 和账户 cursor；候选仍走原生成链 |
| source / 2 槽 | 同一原生成应用与 Recipe、第一材料及完整 Goal、显式 StageApproveInput | 必须完成原 Source Run，当前权限、lease/fence、撤销、期限及两次实际 Attempt/Operation 均验证 |
| extraction / 0 槽 | PBTrialContract 的独立 extraction_request_key、冻结 extraction_recipe、第二材料和完整 Goal | 原 extract_pb 写组；写前后完整同源检查，不发模型请求、不新增 reservation；不复用来源答案 |
| cold / 2 槽 | 提取应用的独立内部 Release/实例、第二材料及完整 Goal、原 cold key 与显式阶段批准 | 原 pb-use 显式材料/Goal 合同，继承来源冻结模式；重新计算新输入，经原生产发送与持久结果链 |

不把原 P-B V1 合同隐式迁移为 V2，不扩 qualified association 队列。旧 P-A/V2 和离线 P-B 合同、时限、quota、Grant、提交/恢复语义保持原样。

## 固定来源与归档边界

生产来源由服务端在原批准后，根据原 Generate Run 的三条实际 Attempt scalar marker 精确选择；调用方不能传 backend、account source、回调、URL 或 ALLOW。生产分支重读固定账户 resolver 和原 journal；旧 budget 只能在原 test-only SQLite 路径读取，禁止混合账本或 fallback。

Source 原任务、当前完整权限和批准在私有正文读取前重新验证。实际 NS 原请求/响应、controller 双镜像、sender Capture、slot 和 usage 按同一 Attempt 连接。生产 slot.response_sha256 是原始 decoded body hash，旧离线 slot.response_sha256 是 canonical ASCII hash；分别比较，不能互换。请求正文、完整响应、模型、原材料/Goal、提取 key/Recipe 和 source proof 都须一致。

NS 和 controller 两套新生产正文归档均标 SPEC_PRODUCTION_CONTROLLER，MOCK 保持 OFFLINE_MOCKTRANSPORT。读取要求与实际 frozen mode、Attempt mode 和 exact controller marker 一致。旧错标或缺失的未发布生产 WIP 记录拒绝，不回填或提升 provenance。读取回执仍非 dispatch authority，不证明真实账户或收费事实。

Cold claim、发送准入和最终提交均重核原来源与提取链。现有原 key 幂等、未知回执、取消/撤权/到期、lease/fence、账户 cursor/CAS 和真实发送边界沿用，不扩大故障矩阵。

## 本轮验证范围

只允许合成 SQLite 与有限 MockTransport；普通真实 HTTP transport 使用 tripwire。测试进程可明确替换生产环境选择、固定账户 producer 和软件资格以测试接线，替换不构成真实授权。原固定 resolver 缺源拒绝及实际软件资格清单不相等另行验证并保留。

新增一条实际 P-B 3+2+2 原控制器集成链，核原 Source bytes、提取、每次材料+Goal 显式提交、冷 Store/控制器运行、新结果与同 Run 人工验收入口；补必要的 provenance/正文损坏及缺源拒绝验证。保留真实 1RPM、租约和运行时限，不重跑旧 P-A/V2 七槽或相邻恢复矩阵。按源码 SHA、输入清单和实际日志分别归属，不宣称 Windows、PG、真实模型/语义或远端 CI 通过。

## 前轮实际终态（c545）：NOT_ACCEPTED / WIP_BLOCKED

源码/测试提交 `c54571391bd695ea116afc0020738c3585ba4972`。当前 113 源 mypy、10 文件 Ruff、标量基数和普通缓存权限回归通过；P-B 三节点实际 **2 PASS / 1 FAIL**，外层 199.879 秒，只完成 1 次 Generate Mock，后续预留因 stale worker lease 被拒绝，最终 Run FAILED。Source、提取、Cold、四次自然预留观察、四个归档拒绝和同 Run 人工验收断言均未执行，不能作为已完成产品能力验收。

同连接账户检查修复已做针对性验证；只读证明作用域和标量投影修复保留所有原完整首证、当前 Grant、批准、账户、lease/fence 和写边界。没有扩大通用 heartbeat/恢复矩阵或更改时限。日志记录实际续租、BUSY5 和过期 guard，但原比较时刻及外层调用栈不足，具体锁占用原因仍未知。未做无变化盲重跑。

[分 SHA 的全部结果、原始包、独审及未执行边界](../evidence/pb-production-controller-20261019/README.md)。旧失败和失败的测试/剖析种子均保留；14 次失败 P-B Mock 与另 3 次 ordinary Mock 分开计数，不拼接槽位。真实模型/账户探测为 0。固定生产来源和实际软件资格继续阻断真实调用；没有自授 LIVE、部署、main 或权限变更。

## 2026-10-19 接续终态：Source/提取前缀有限完成，Cold仍阻塞

本轮产品源码 `9fbcb6a4e682a09f916b4561795f000c609aea10`，测试合同修正 `84fde1b6a5724c57ce0fa68b868ff82e445ed1d8`（src逐字相同），接续远端 `5bd438812a9914fac827014336a5ba38b63d08dc`。复用原续租控制器和同调用完整来源证明，SQL结构共享仍逐次绑定当前身份、读取/锁住当前行；未改原Grant、源/软件资格、额度、30秒lease、Run300或合同期限。

5项窄门、113源mypy、11文件Ruff实际在9fb通过；84f只补Cold前真实draft GET/指纹核对，单测试Ruff和0发送SUCCEEDED结构检查通过，全部冻结输入稳定。另有一次0发送检查因作者运行中编辑测试而一文件漂移，原件保留且未计冻结PASS。不存在新单一SHA全测试PASS声明。

9fb原标准整链实际5Mock，Source SUCCEEDED、两VERIFIED；原提取/同key重放、完整Source原文归档、四个归档拒绝、Release/Instance和目录NATURAL_PB通过。测试随后因提取回执字段误用而KeyError，Cold未提交；84f修正测试合同，产品未变。

为避免重复五槽，在本次结束DB只读backup上重核原合同/expiry/权限/软件/五accepted账本/Source/缓存提取后，仅执行原Cold段；外230.645秒、2113输入稳定、0新Mock/Cold0Attempt。显式材料Goal review/提交/同key cached重放和阶段批准通过，但首个本地读取的最终commit_guard被原finite-lease综合谓词拒绝，Cold Run `run_4ed4f78b22df49edbf752dac24b40b3d` 仍RUNNING、无steps/结果；未到Cold结果、同Run owner合同、七槽/22归档最终断言。原前缀DB哈希未变，未调整期限或补账本。Standalone无事务耗时/SQL/CPU及精确比较时刻，不补用旧观察器证明。

完整 P-B 仍为 **NOT_ACCEPTED**；剩余是Cold本地读取证明的工程lease边界问题，不是访问审批阻塞。原固定真实账户来源及实际软件资格继续关闭，真实模型/账户探测均0；Windows、PG、原生浏览器、真实语义/人工签收和远端CI未执行或未核验。所有失败、15版源码、外部脚本和独审见[本轮原始证据](../evidence/pb-lease-cause-20261019/README.md)，旧c545及旧满盘独审缺口不覆盖。

## 2026-10-19 最后有界接续：FAIL_NOT_ACCEPTED

最后执行源候选 `2b3846d0802ef2875d9665acc1280b949d1a4131`，原完整 P-B 标准pytest实际1 FAIL/0 skip，19:12:22至19:25:29 UTC，6次有限Mock（Gen3+Source2+Cold1），真实模型与账号IO为0。Source成功，并完成提取、NATURAL_PB目录、显式Cold材料/Goal提交及同key去重；Cold初次本地读取实际提交，首次模型响应结算的完整证明事务跨过原30秒lease，结算写组回滚，Attempt持久化REJECTED_KNOWN，Run仍RUNNING/result null。完整Cold及最终结果/人工验收断言未通过。

最终v26独审为FAIL_NOT_ACCEPTED；按最新收敛边界，本轮停止源码修改及完整链重跑。下一最小待定位点为同一Cold响应结算内完整绑定/admission核查、写后证明与读回/settle_verified链；不得跨写复用旧证明或延长租期。定向结构/边界门和Ruff/mypy通过的实际范围、各历史FAIL、不可回写原始包及最终独审见[最后接续证据](../evidence/pb-cold-local-read-cause-20261019/README.md)。此前Cold本地读取阻塞记录保留，本次进展不覆盖旧失败或旧满盘独审缺口。
