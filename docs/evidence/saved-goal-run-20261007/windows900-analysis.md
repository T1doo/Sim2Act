# Windows900：只读阶段账本与下一优化切片

结论保持 **NO_GO**。完整Linux1309成功和PG49成功不能补Windows900容量证据。本次没有CI、test/full、PG、源码修改或LIVE；输入原件SHA、当前只读HEAD与完整原始步骤时间在analysis.json。

## 原始历史账本

|实际run/source|前置到工程|工程（pytest）|Edge|尾部|job|
|---|---:|---:|---:|---:|---:|
|37621453354 / b2328e45，attempt1|55s|741s（730.12s，1028P18S/1046）|110s后cancel，**完整值UNKNOWN**|6s|912s /900 limit|
|37597713044 / 7c02c66e，attempt1|保存原steps逐项|677s（661.87s，954P13S/967）|完整150s|保存原steps逐项|896s，仅4s观察余量|
|37613698141 / e6c03cf，attempt1|保存root-review，未猜分配|567s（556.10s，1017P18S/1035）|105s后fixture退出FAIL，**不是完整成功成本**|成功cleanup，未猜分配|734s FAIL，不能当900预算通过|

b232逐秒官方job.json：12:30:20开始；checkout8、Python选择0、Setup31、smoke15，12:31:15开始工程，12:43:36结束工程；Edge至12:45:26被取消；report1、cleanup1、checkout post3和剩余转接到12:45:32。912中工程741占81.25%；pytest外工程封装只10.88s。主要已证明问题是工程和完整Edge**串行总关键路径**没有余量，而不是已证明某个特定SQL查询或Node150超时。Edge截断110不能签成功；它还剩多少U未知。以原历史速率仅作会计恒等式，完整成本为912+U；净Windows节省S需超过12+U+预留margin，S/U均未实测，不能据Linux20s推出通过。

b232原slow30完整30项合计241.46s，只约pytest730.12s的33.1%，不是全部性能账本。四global-gate实际calls53.31s；可见registered-browser setup12.05、4.86、4.84s。慢项还包括two-form PG15.42、normal/-O来源边界15.01、冷流程及实际子进程。这些断言/子进程边界不可删。工程677→567→741在不同源/runner观测的变化说明不能按新增case数线性推Windows时间或把全部变慢归新增功能；当前1309比b232多263，当前完整Windows成本仍未测。

## 可实施的最小切片：仅新鲜测试schema减少冗余初始化探测

实际代码证据：Store.initialize（db.py478）只供显式migration，调用meta.create_all(engine)，SQLAlchemy默认checkfirst=True。tests/conftest.py16–24先由owner创建新随机PG schema，再每个env调用initialize。当前meta有40表；SQLAlchemy SchemaGenerator metadata walk会逐表调用has_table。对刚创建并确认空的自有schema，这40存在性探测重复了“空schema”事实；**次数可由代码定位，native毫秒成本及其占741比例未知**。Worker.once/reserve没有initialize，项目/Run/额度/池锁及当前授权重核不是DDL探测，不能把它们当冗余删除。

建议下一授权切片限定test-only controller：在新UUIDschema、owner显式建schema且一次catalog证明确实空之后，用明确fresh-schema建表路径checkfirst=False；仍创建相同40表/索引/外键/默认quota，所有业务角色只CRUD、Store(role)不initialize。已有schema/碰撞/未知schema必须拒绝或走原显式idempotent initialize，禁止全局把默认改false，禁止API自动DDL、缓存迁移身份或给runtime角色DDL。保留initialize两次幂等测试及fresh/nonempty/角色否定用例。即使省了探测也仍要40个真实DDL，不能保证大幅总耗时下降。

先只做可审查计数器/计时设计：把fresh-schema has_table SELECT、DDL、seed业务SQL、实际来源准备/Worker、subprocess分别记count与elapsed；使用owned同容量已有native资源的明确授权定向资格验证，不自动再开CI。保原输入/normal/-O/crash/revoke/越域/版本/幂等/authority/cleanup断言及完整集合。需要同源同容量成对native冷schema样本、完整Windows阶段包络和margin才可闭900；若native资源不可用则继续NO_GO。不要先盲跑整轮或凭40乘用例数预算——实际env初始化次数尚未统计。

## 已有优化不能重复算未来收益

- ff58011/ff3三个test files的immutable module模板复用已在当前源：每case仍独立拷贝完整SQLite文件/marker、实际normal/-O子进程，seed仅一次，mutation隔离hash保留。Linux10case成对22.57/20.26对35.13/41.66，仅12.56–21.40s观测；Windows节省0已证明。它是fixture改进，不是生产优化，也不是新的900预算。
- 1258 request-local来源复用已实现，cached SELECT646→347、Report416→345是SQLite profile；保持当前授权/源seal实时强门，不准跨请求cache。这是生产请求热点优化，但没有当前Windows成本证明。
- 4d目录hint跳过已知Report的背景CSV发现deep inspect也已实现。LinuxPG paired旧34deepGET sum44.572s、新17 sum16.825s，sum重叠，不代表44s墙时节省；native fixture没有同Report promotion路径，不能推Edge必然受益。explicit open/来源/授权和unknown fallback保留，别为预算弱化guard或把UNKNOWN变PASS。

## 串行容量仍不足时才考虑更高风险的同runner重叠

已有NativeBudgetPlan及独审将工程/Edge重叠列为**design-only BLOCK/未实现/未qualified**。它可能缩短关键路径但不能自动当省预算，也不增加runner/CPU/RAM/cache。必须有真正原job起始deadline（不能在supervisor launch重置900）、Edge240覆盖npm/signature/seed/API/Node/emission/finally、Node150独立时钟、cleanup reserve；独立PG schemas/SQLite roots/ports/严格child env，不能把PG ownerURL或凭据带到Edge。保所有原工程集合和native26+19+22/PNG/审计/安全沙箱，joint成功只在双branch完整exit+sealed成果+清理都达成，不因提前截图或PNG存在就PASS。

先资格测试supervisor失效、启动阻塞、occupied port、旧监听者/产物、任一branch失败、secret env crossover、timeout和owned descendants cleanup，再在同资源成对观察完整串行/重叠CPU、memory、tail latency。当前没有原job-start marker/持续端口保留/跨全树终止资格，不能仅重排workflow启用。若资源争用抵消收益或缺margin，保持NO_GO。Windows900/Edge240/Node150、coverage/assert/security保持；Win11、AT02、formal P-B仍另有门。

所有分析产物在/tmp独立目录，不编辑旧日志或原1309证据。
