# 默认 Graph 当前版本读取：真实时钟与可安装限制候选

应用验收源码 `35eaa941f544ca016ddeeefb839178d316fc1c6b`；本轮所有权修复基线 `27619e9c7d250694a3f614f7960427321e804ca4`。开发分支 `dev/cloud-g0-live-20261028`，main／Release未改。新源码真实保存改善，但**原普通30秒目标仍失败，长写锁尚未解决，不是全产品完成**。

封存身份见 [identity.json](identity.json)，文件大小与SHA256见 [artifact-manifest.json](artifact-manifest.json)，本轮配置秘密值及压缩成员扫描范围见 [privacy-check.json](privacy-check.json)。清单不包含自身；应用源码身份与后续证据提交身份分开记录。

## 实际产品修复

1. 复审发现：借用 Frontier 后同时改 Frontier.graph 与 mode.graph，旧 Python 清理仍会关掉其他 owner；Candidate.release 的可变 frontier 指针也存在同类路径。C Journal 现在保留原 child 和 mode/scope/candidate 清理身份，撤销 live scope/version 后仍能正确完成原 owner 清理；GC traverse/clear覆盖新增引用。查询分配失败时先撤销、保留原异常，不回退跟随借用指针。原版本实编后新双 backlink 反例实际失败，原件保留；新反例通过。
2. 原30秒实测发现当前版本链重复核资格：一次受限G0已发生约7.7万次直接 source verifier、5.4万次 pin_registered、3.6万次 pin_current。三个native计时项互不重叠，但不把它们相加冒称可直接节省时间。
3. `pin_resolve(subject)` 将**同一次当前版本读取**中的新协议重复核合成一次 fresh 完整 Source gate。所有可能分配在 gate 前；之后以预建 Unicode keys 读取精确dict、13个scope锚点、原issuer/current/key、原Frontier及shadow状态，无分配、无回调地返回同一Version。gate后补核Frontier.graph。所有native实际属性／hash角色、模块精确类型仍核；已发行对象不可降级。死弱child也不能退回父图旧版本。

默认 Graph.content_version 与 versions.current 已实际接入，旧API仍供发布／清理使用。未缓存Graph PASS、授权、撤权或时钟；未合并不同Graph.check、SQL、callback、发布点或W5/G1。业务callback、完整内容比较、原五写和独立完整G1都保留。内部Python helper和sys.monitoring事件次数有变化，不声称逐事件追踪等价。

## 原普通30秒：单独失败记录

| 源码 | 实际区段 | 拒绝位置 | 首次DML | G1 |
| --- | --- | --- | --- | --- |
| 27619e9c | Epoch 29.957598s，snapshot 29.957145s | `checkpoint→_ColdGraphRead._check_dynamic`；物理栈在 `commit:first→_graph_run_context→scope_gate` | 未尝试 | 未到达 |
| 35eaa941 | Epoch 29.962927s；实际snapshot见 candidate30 | `checkpoint→_ColdRunFacts.progress_event→_receipts→_cold_receipts`；在首commit之后、第二commit之前 | 未尝试 | 未到达 |

两次均为原 `TrialCaps` 的30秒lease，无 settlement_seconds／protocol 字段，原 Source／Run／节点截止未扩大。实际单调时钟已耗尽、墙钟采样尚有余量；这是异常时采样，不能据此唯一断言短路分支。接收响应、已知用量和拒绝历史保留，无typed结果／目标成果／延长预约。完整栈、caps、source库存、snapshot与原失败判定均保存于 baseline30／candidate30。

诊断pytest通过表示**预算负例安全拒绝**，不表示Goal成功。后续报告辅助函数修订只澄清失败attempt及全Run无扩展预约的断言；历史原件不改签。原30与下表120选择的内部路线不同，不相互代入耗时或理论下界。

## 显式signed120：同环境、同fixture、同观察器顺序对照

7次固定Mock（Generate3＋Source2＋Cold2）、独立文件SQLite/WAL、实际墙钟；0真实模型。未同时跑两轮测量，观察器SHA一致。source／binary／命令及前后clean状态记录在各 run-run.json；UUID和真实时间自然不同，不是字节相同数据集。观察开销包含在结果中，不是无观察SLA。

| 源码／笔次 | G0至promote（s） | snapshot写入区段（s） | snapshot总计（s） | 结果 |
| --- | ---: | ---: | ---: | --- |
| 276／1 | 47.217929 | 66.585299 | 113.804086 | COMMITTED |
| 276／2 | 48.268267 | 67.924824 | 116.193618 | COMMITTED |
| 35／1 | 35.419513 | 51.985205 | 87.405691 | COMMITTED |
| 35／2 | 37.579921 | 56.425874 | 94.006303 | COMMITTED |

两笔总计分别降低约23.2%／19.1%，是本轮匹配样本的实测差异，不是所有输入或环境的稳定保证。原控制checkpoint计数20327／20614保持，未删动态门。G0／writer／total的snapshot边界与Epoch有亚毫秒差别，不混用。写入区段不是精确SQLite锁期：首次DML返回到commit开始为下界，首次DML尝试到commit返回为上界；详见 `graph-real-clock-paired-summary-20261101.json`。新下／上界约51.983926–51.985109、56.422378–56.425767秒，长锁仍存在。

两版实际五写、完整post G1、原SQL COMMIT及最终Run SUCCEEDED通过；各自新解释器只读重开，HTTP保存结果、app结果、typed版本1、两条Cold VERIFIED与7条attempt一致，主DB内容不变。absent→empty WAL为无内容的生命周期变化，明确physical_identity=false，不能说物理文件完全不变。276第一次helper尝试在SQL之前因不完整runtime witness及路径误差停止，转录另存；不是数据库损坏，首次实际DB回读通过。35首次helper及实际回读直接通过。

SQL计时行仍与Python exclusives重叠，派生表不会将两者全表相加。所有inclusive也有嵌套，不能相加当互斥总耗时。

## 回归、持锁取消与限制候选

189项相关源码回归全部通过、零跳过；78项边界回归与其重叠，不相加。覆盖原结构/隐藏行/别名、类型/角色替换、模块类零getter、GC/弱引用死亡、重入发布、跨Graph清理及分配失败。两位既有只读reviewer分别复核生命周期／C代码与证据口径，未发现保留的新增mustfix；静态结论不代替实际命令。

真实G1持锁探针返回SQLITE_BUSY；状态读取0.044971秒、取消POST0.104240秒，完整事务回滚，原收到响应、typed／资源／归档历史不变，原流程暂留RECONCILING。随后在原数据库私有副本用默认worker收敛CANCELLED，重复cancel为200/CANCELLED，再开Store.once返回False、无新增模型尝试。原数据库未改。辅助检查首次错误地要求所有Attempt/Operation状态也完全不变；实际只允许当前Attempt RECEIVED→REJECTED_KNOWN、Operation DISPATCHED→REJECTED_KNOWN，正文／用量及其他列和所有非目标行保持。原断言失败、逐列差分及修正后结果都在cancel目录，不将辅助断言错误藏成一次通过。合同仍显式120，不能改签普通30；没有权限／额度／超时变更。

新限制候选使用**同一枚实际安装并运行过的wheel**。隔离venv、源码目录外启动，四原生扩展从安装目录加载；普通入口实际CSV sum30／版本1保存、同键不重放、两次退出0/clean、首次新进程回读通过。共用已有锁定依赖，经显式.pth链接，非干净机器下载依赖验收。默认模型关闭，通用自由目标仍明确拒绝。新包仅Linux x86_64／CPython3.12，不是Windows EXE；PG、大型live、任意目标语义、人工验收与原30秒性能仍未通过。

包身份和使用范围见 [限制候选](../../../deliverables/limited-graph-current-20261101/README.md)。旧2ad候选完整保留。当前新包／工件对注入秘密值精确扫描，压缩wheel解压后也核；只保存PASS及SHA，不输出值。无数据库、模型正文、私人账户、运行环境或新凭据发布。不使用用户电脑，不新增Windows CI、费用、安全权限或部署。
