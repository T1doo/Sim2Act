# 两步 CSV DAG 内部复用：限定证据

最终源码/测试冻结 **`d716feda486fd6f0322c11b2e1b5112f718a94fa`**，产品源 **`039b74cf03ea5926b0b02b1b81dc684fa639a46d`**；基线开发分支 `67c6ccc8ad7d6f132205c2ac4f33b10defca5da7`。357文件Git blob与工作树逐字节核验，69产品中7文件变化；DB/DDL/Schema、worker、注册动作定义及依赖文件不变。可信Python源码变化会改变既有registry内容指纹，旧证明保守失效，不自动迁移。[冻结清单](source-freeze.json)、[产品证明](product-byte-proof.json)、[两次字节桥](freeze-bridge.json)。

成功的无条件 `resource.read → data.aggregate_csv` 来源现在可经人工准备/确认保存内部版本，再分别创建实例、选择同一冻结CSV另一数值列、确认新持久Run。来源/授权/预算、双行seal、审批与持久请求键均核实；新Run有独立计划、两个真实VERIFIED回执和typed实例结果，业务结果写入如实计1，模型请求0。冷历史比较接受事件、双回执marker和关联账本三组集合，并重构真实Run/Operation；完整性矛盾拒绝零写。[实现合同与操作说明](../../F2/CsvDagInternalReuse.md)、[首次使用](../../FirstUse.md)。

## 作者必要验证

| 数据库/阶段 | 实际结果 | pytest时间 | 归属 |
| --- | --- | --- | --- |
| SQLite039整批 | 74例72PASS/1FAIL/1SKIP | 124.052秒 | 原事务BEGIN的compiled=None触发测试注入钩子错误；所有产品字节与最终d716相同 |
| SQLite d716定向 | 原失败节点1PASS | 2.847秒 | 仅测试加非空guard；未无目的重跑其余已通过节点。必要74个不同节点覆盖73PASS/1PG角色SKIP，非一次整批全绿 |
| PostgreSQL17.9 d716整批 | 74PASS/0FAIL/0SKIP/0ERROR | 262.081秒 | 完整必要集合；357源码/测试字节前后一致，进程263.201秒 |

[原命令](run.py)、[归属汇总](summary.json)、[SQLite039日志](sqlite.log)、[SQLite定向日志](sqlite-rollback-d716.log)、[PG日志](pg.log)和JUnit均保留。必要集合覆盖新实例权限/来源/预算/CAS/同键冲突、单次typed append、最后提交失败全事务回滚、期限/旧fence、家族降级/双行seal、联合历史遗漏、冷恢复、既有纯DAG、四节点组合、原单节点应用使用与Report晚回执，没有跑全库2000余例。产品五Python文件Ruff及JS语法通过；未改CI或依赖。

每库9真实loopback HTTP/jsdom页面、104具名检查：新复用两场景4页面36检查（丢POST接受回执与已接受后GET失败，各含冷新列）、既有组合2页面28、原ApplicationUse2页面30、Report same-checks1页面10。新页面逐项验证实际HTTP加载HTML/JS的SHA256，操作真实API及正常worker；不是只伪造成功响应。两个新列产生不同Run及typed v1/v2，冷页面恢复零POST。资产散列、独立Python算术与DB持久结果核查另外记录，不混入具名检查数量。Linux/jsdom不签原生Windows/Edge/Node或像素体验。

每库4个实际旧源码升级：实际基线67的成功来源Run在旧端准备新内部版本404；当前端旧证明409、元数据控制200且无单元格、原历史字节不变，新精确来源才可新Run求和15；另有 `5a5543c902fbb78dd91c28c98386af51fb24dd67`、`1b65e94ebd81c1e31091b3078b8223328b726294` 两CSV及 `afb2f1f3813fc3a4744923f31bbcb4666b88cccd` Report的真实旧端执行/当前升级。当前机器旧67归档297文件逐一Git blob验证，[归档证明](archive-proof.json)；CSV旧模块SHA256 `e02a5a1e38910f64914e095e77da95cd7f0106dea49844f3a1723e37d0acc1d2`。各库old-source/upgrade JSON保留；没有把独审读取807旧DB的registry漂移拒绝算成升级通过。

作者自有PG容器 `0b88f84d7c896f768abea84cef45dd9c8eeb2220d13ad633fa66f51eb0808897`，owner dag-reuse-20261010，network none、无发布TCP端口，仅本轮Unix socket。最终server正常初始化后SQL探测，前后schema/role/public均0|0|0；普通stop/rm-v完成，自有容器/卷都不存在。未修改已有PG或凭据/安全网络配置。[就绪](pg-ready.json)、[前后统计](pg-after.json)、[清理](pg-cleanup.json)。

## 独审与失败归属

[原807独审](independent-807/FINAL_REVIEW.md)仍为 **BLOCK**：自编SQLite14API/47检查、5HTTP UI场景6页面140检查通过，但真实联合marker/joins删除使冷历史错误变空。039修复后，[最终必要增量独审](independent-delta/FINAL_REVIEW.md)对d716签 **LIMITED_PASS**：自编4例12检查，联合遗漏和重复接受事件409零写；当前正常冷实例、原型Run和兄弟实例scope正确。807→039仅1产品模块及1测试改变，355/357文件、68/69产品不变；039→d716仅1测试，69产品全相同。旧矩阵不重标为最终全矩阵，新增独审不代签PG、升级、新UI或整体。

807作者PG的注入失败和Report最终GET在原6秒idle内未drain失败均保留；同冻结原Report节点仅一次定向24.344秒通过，最终PG集合也通过，仍未解释首轮慢读，**新增Report GET超时OPEN**。历史resources-history Future10/395graph锁慢读另行OPEN，本轮未跑该节点、未改超时或observer。[全部失败账本](FailureLedger.md)还包含作者初始probe与独审自编harness失败，不能用后续通过覆盖。

[精确复制回执](copy-receipt.json)含241原件；两个独审白名单72与32文件及清单本身逐字节保留。嵌套.gitattributes保持Git blob原始字节，排除SQLite、pycache、socket、环境及凭据。普通候选推送、开发快进、远端SHA和本地状态按[集成记录](Integration.md)读取。

这是固定同材料、无条件两步CSV流程复用切片，不是任意DAG、换材料/版本、模型自主生成、完整P-A/P-B、PROJECT全局或整体验收。DAG新写入使用既有持久幂等账本；原材料Save UNKNOWN仍仅页内Map、无幂等键，不承诺跨刷新exactly-once。未确认新UI intent跨刷新会丢失，先手动只读核对历史。LIVE=0，provider预算0，PROJECT PENDING/BLOCKED_PARTIAL，semantic UNKNOWN、owner PENDING、overall NOT_ACCEPTED，正式发布关闭；HTTP200其他损坏响应提示与逐item历史map限制保留；Windows900/Edge240/Node150未验收。无main修改、强推、部署、凭据/安全网络修改或真实模型调用。
