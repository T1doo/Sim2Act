# G0 离线定位与安全设计草案：尚不改生产路径

基线 `337569ed731bb806a25f29328a8119e7b40cf2b4`。本轮没有第三窗口，没有产品路径、事务结构、租约、额度或鉴权修改。以下区分已观测结果、源码机制与未验证方案。

## 可确定的范围

原诊断五个局部区间合计 5620 次 check、5685 次 input_key；wall 分别为 `_prepare`14.743301s、`_graph_run_context`4.081457s、`_graph_pb_accounting`0.414143s、`_graph_resolve_trial_source`6.001872s、`_graph_pb_archive_chain`0.030677s。这五段合计25.271449s，不覆盖全部31.125280s G0。没有CPU profile，不能将这些时间全归给某个底层函数、SHA或序列化，也不能据次数推算收益。

确定调用链：`natural_spec_runtime._ColdGraphRead.check`(1812起) → `input_key`(1805) → `input_bytes`(1779) → `_trial_typed_storage`全 contract 存储遍历 + `_cold_graph_bytes`(1732)完整协议5序列化 → SHA256。`add`(1845)还会校验新增原值并对完整现图重新 pin。`natural_live_admission._trial_typed_guard`(1332)、`_graph_trial_produced`(1371)在原父边界前后反复调用；`_prepare`(2617)构造完整来源/生成/accounted事实，`natural_source_archives._graph_resolve_trial_source`(435)的 parent pin 还逐次核Source阶段原事实与模型 cohort。它们是可离线确定的重复工作结构，不能由此证明哪部分占CPU主导。

`STANDIN-MEASUREMENT.json`只使用已保存的原 contract JSON及六条交换日志组成71,917字节协议5 primitive envelope，保留共享引用；100次每次重新完整序列化和SHA，分别约0.033899s和0.003367s。它不含真实typed graph、字段存储验证、SQL、cohort或完整guard，不能外推到原5685次调用，更不能当作G0速度预测。纯数据回归证明深层字段变化、增加字段及等值但不同别名结构不会被该stand-in编码折叠；这不是生产序列化器资格证明。

整轮342.200s与G0 31.125s必须分开：`pa_trial_dispatch._journal_wait`(1239)按last_reserved_at+60等待，`production_trial_policy.reserve`再次要求原reserved_at间隔>=60；六次reservation之间已有原节流。不能把前缀大段等待解释成网络/训练或G0扫描。原receipt没有逐次磁盘采样时间戳，6795/342.2≈19.8568Hz只是整轮粗比率，不能还原G0内采样间隔或开销。

## 写锁机制与不安全的直接拆分

`natural_spec_runtime.advance_model`在同步renew后进入`store.tx`(3555起)，包住G0；`db.Store.tx`(726/743)在SQLite上用BEGIN IMMEDIATE，直到commit/rollback释放写事务；`Store.heartbeat`(1370)也使用tx。另一连接无法在此写事务内完成续租。这是源码与SQLite机制结论；没有逐次心跳时间日志，不能宣称已测得本次后台阻塞时长。[SQLite事务文档](https://www.sqlite.org/lang_transaction.html)、[隔离文档](https://www.sqlite.org/isolation.html)均说明单写者及BEGIN IMMEDIATE的写锁语义。

小型stdlib存储单测仅验证：读操作所在IMMEDIATE事务仍使另连接BEGIN IMMEDIATE返回SQLITE_BUSY；rollback后该连接可写；短读释放后用版本/fence/原lease/deadline谓词的CAS会拒绝失配或到期。这不是生产CAS实现，没有证明完整授权、集合/新增行或内存输入的覆盖。

现`_ColdGraphRead`绑定connection、transaction、driver、total_changes、thread、source token/epoch等，不能跨事务复用；连接本地epoch也不能证明其它连接未改变数据。只移出原函数、保留旧guard、仅比Run version或仅信摘要，均不足以保持验证与提交原子性。WAL也不允许两个写者，不能作为这个锁问题的解决方案。

## 可审候选设计及实施前硬条件

本轮只提出以下分阶段候选，不实施、不声称已经安全可行：

1. 将纯类型/结构校验、完整字节序列化/哈希、已存wire解析及不可变证明关系重建识别为锁外候选。先用短一致性读取取得完整拥有的不可变快照，立即结束读取事务；计算期间不持旧SQLite事务/guard，不暂停原有心跳。不得改变journal模式或延长lease。数据库返回row/view与可变Pydantic实例不能直接作为不可变快照。
2. 快照必须保留全部字段、别名、存在性及集合谓词；须证明每个审批/撤销、scope/Grant、Source/生成/归档原文、journal/quota/占用与Run相关写入都有原子、不可绕过的变更见证。新增/删除匹配行也要被覆盖。内存contract/binding/cohort要有可证拥有且不可变的完整表示；对象身份或历史验证缓存不合格。当前源码未提供这样可复用的跨事务完整见证，**这是未满足条件，不是建议直接加一个epoch就算解决**。
3. 在新短写事务重新构造当前所有权/version/fence/停止/审批权限/原所有finite期限与当前已提交lease，按原错误优先级核验；CAS必须同时绑定完整见证和业务写入。只有仍一致才能在同一事务做原提交/结算写组及最后deadline/stop检查，任何不一致/到期均整体回滚。Run version CAS只是必要条件；没有完整覆盖就保留原路径并拒绝使用快照结果。
4. 锁外阶段只允许原有尚未到期的owner按既有心跳条件续租，禁止过期复活；短提交仍必须严格end<min(全部原finite)，原run300/lease30/TTL/RPM/额度保持。不把旧RunCheck deadline沿用为缓存，也不能把未批准的新边界解释为原期限语义已等价。须先独审其线性化点和拒绝顺序。

实施前必要回归包括：并发撤销/Grant变更/Source正文及seal变化/新增删除匹配行/账链quota漂移/Run version与fence竞争/停止及有限期限边界/过期续租拒绝/内存深层字段及别名变化/写组部分失败全回滚/原错误顺序/每个原pin的覆盖。未完成这些证明前不拆生产事务，不减少pin，不缓存验证结果，不以stand-in结果决定生产优化。已否决的提前标量校验、单删SHA、类型分派和前缀分配方向不重做。

## 当前交付边界

当前能交付的是磁盘报告口径修正、纯数据成本分解和机制回归。没有足够证据批准某项生产提速补丁；采样报告修正不解决G0期限。第二窗口Cold RUNNING/RECEIVED来自StopBoundary将原DomainError转为BaseException保留现场，不表示生产漏收尾；原证据和业务状态一律不改。
