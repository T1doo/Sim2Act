# 失败保全与限定修复

本目录同时保留作者初始失败、807候选的真实独审BLOCK、039产品修复和d716仅测试修复。后续通过不覆盖原失败，也不把不同冻结结果合并成一次整批全绿。

| 阶段 | 实际结果与处理 | 原件 |
| --- | --- | --- |
| 作者初始probe | 16例中15失败：快照授权字段读取与真实graph返回字段不一致。修正字段读取后原16例通过；尚未形成807冻结 | initial/probe.log、probe.xml、probe2.log、probe2.xml |
| 作者connected/safety/page-probe | 各1失败：ReleaseOrigin缺少既有KeyInput所需request_key/类型字段。补齐严格来源输入；未放松验证 | initial/connected.*、safety.*、page-probe.* |
| 作者page2 | 22例21通过/1失败：HTTP页面夹具误带计划缓存字段，修正私有页面输入 | initial/page2.* |
| 作者ui3 | POST丢回执场景通过、已接受GET失败场景失败：夹具误把显式GET判定为无method。只修正GET拦截；对应ui-read4定向1通过，upgrade-probe3通过 | initial/ui3.*、ui-read4.*、upgrade-probe.* |
| 作者807 SQLite | 73例72通过/1PG角色跳过；357冻结字节不变 | sqlite-807.log、sqlite-807.xml |
| 作者807 PostgreSQL | 73例71通过/2失败。终态写失败注入依赖SQL文本前缀，未命中PG带schema表名；另有原Report late same-checks页面6秒idle超时 | pg-807.log、pg-807.xml及pg-807页面failure.json/driver.log |
| 原Report PG定向核对 | 相同807冻结、原6秒idle/进程超时未改，仅一次原节点24.344秒通过。首轮最终Report GET尚pending，未得到根因或稳定性证明；新失败继续OPEN | pg-report-once.log、pg-report-once.xml及实际页面results.json |
| 独审807 | 14API/47检查、5UI/6页140检查通过，但联合删除双accepted marker、binding/AppRun/typed data、归零版本后，仍保留的CSV_DAG_ACCEPTED被遗漏：冷GET200空历史、直接Run409。实际BLOCK，不以通过数量覆盖 | independent-807/FINAL_REVIEW.md、joint-omission-readback.log、readback.json |
| 039产品修复 | 用接受事件、双行回执marker、实际joins三组Run集合严格相等及去重，拒绝遗漏；同时将作者注入改为compiled Update对象，新增联合遗漏回归 | source-freeze-039.json、freeze-bridge.json |
| 作者039 SQLite | 74例72通过/1失败/1PG角色跳过：新注入钩子在原BEGIN IMMEDIATE上遇到compiled=None。这是测试钩子错误；失败完整保留 | sqlite.log、sqlite.xml |
| d716仅测试修复 | 给注入钩子加compiled非空guard；69产品与039完全同字节。原失败案例定向1通过，未再整批重跑SQLite；必要74节点覆盖73通过/1PG跳过，不能描述成最终一次整批全绿 | sqlite-rollback-d716.log、sqlite-rollback-d716.xml、freeze-bridge.json、summary.json |
| 独审必要增量 | 4例12检查LIMITED_PASS：联合遗漏、重复事件409零写；正常冷实例、原型Run与兄弟实例范围正确。未重跑旧矩阵，旧807DB因既有registry源码漂移409的首轮尝试也保留，不算升级正例 | independent-delta/FINAL_REVIEW.md、incremental.log与各数据库投影 |

独审自身首轮接受pair脚本误读response字段、UI把合法1.500与1.5字符串比较的夹具失败均保留在原807白名单；只改自编harness，独立Decimal oracle不变。作者归档桥脚本首轮误把旧archive自身的archive-proof.json元数据当作Git产品文件；随后只遍历src/tests，297真实旧文件逐一Git blob核验。该脚本错误没有产品修改或测试通过宣称。

首次Git diff空白检查标记了原JUnit失败stack的尾空格；只对本证据目录原.log/.xml禁用空白诊断并保留原件，不重写诊断字节。产品与普通文档空白检查仍执行。集成前候选remote tracking ref缺失使rev-parse检查失败，在切换/merge前停止；随后用显式普通fetch refspec恢复，没有修改Git配置、强制推送或源码。只读尝试本地main名称还确认本环境没有该本地分支；远端main一直按ls-remote核验。

私有完整原件仍保留在 `/tmp/sim2act-dag-reuse-20261010`、`/tmp/sim2act-dag-reuse-independent-20261010`、`/tmp/sim2act-dag-reuse-independent-039-20261010`。公开复制排除数据库、pycache、socket、环境及凭据；精确复制回执和两个独审白名单记录原路径与散列。

历史PG resources-history Future10失败仍OPEN，本轮不重跑该节点、不改其超时/observer。新增807 Report GET idle失败同样OPEN，单次或后续通过不能关闭。其他HTTP200损坏提示形式/入口与逐item历史map限制、原生Windows900/Edge240/Node150未验收保持。LIVE=0，PROJECT PENDING/BLOCKED_PARTIAL，语义UNKNOWN、owner PENDING、整体NOT_ACCEPTED；正式发布关闭。
