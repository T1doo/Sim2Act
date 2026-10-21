# 固定复合parent pin：仅合并同次重复编码

基线 `7832d211c6b952c6e79444c7f9bf666cc609fce4`。上一真实Mock窗口见证
OWNED发行，但首commit超原lease；run-context和Source resolver仍有3835次
codec／11.438898226秒线程CPU。这是选择本片的成本证据，不承诺能省11秒或过门。

## 最小实现和边界

仅 `_graph_run_context` 与 `_graph_resolve_trial_source` 的 `_parent_pin` 使用
新私有固定入口。exact已发行native mode每次先执行**原 `_graph_trial_pin`**，
保留exact graph／Store／connection及原拒绝顺序；随后执行原mode dynamic／links
纯检查和原stage关联：Generate family及完整Run、raw／metadata身份，Source Run
或Cold job／family／extraction身份。所有叶子动态检查继续执行；原typed cohort
仍在parent后校验。复合异常关闭scope，默认None和非native旧模式仍走原两步。

公开assert_current／assert_stage AST不变；assert_family／assert_run只提取纯谓词，
内联回去与原AST完全相同，仍自校验。没有PASS缓存、token、全局重入标志或通用
skip_guard。新分派只接受exact NativeCandidate及`owned_ready is True`，私有Cold
extraction只接受exact tuple4，避免在固定纯段调用外来迭代器。frozen和extraction
body原本由typed/model边界校验，本复合身份谓词不单独声称证明9字段内容全等。

原每SQL／授权查询／外部返回guard、source_proof身份、typed cohort、完整读集、
txn/fence/stop和最终期限均未移除。两消费函数除parent替换外AST相同；原
_graph_stage_current、_trial_typed_guard、runtime、native、DB、dispatcher、settings、
账户门、launcher、保护与五阶段观测器均保持基线，见preserved-boundaries.json。

## 实际离线验证

| 批次 | 实际结果／范围 |
| --- | --- |
| first | 19P2F／31.60s；初版关闭连接拒绝顺序有误，已恢复首个原pin；Slot反例误改不参与Source验证的Generate槽，修为Source槽同aid非aid变化 |
| broad-final | **97P1F／163.86s**，98项；native／SQLite／wiring及新增23项；唯一F是强制c.close后旧source-read／Store.tx退出访问c.info的ResourceClosedError，不冒称98通过 |
| closure | **24P／36.13s**，最终四SHA；内层精确检查pin的DomainError／VERSION_CONFLICT及关闭，外层单独记录既有夹具退出异常；生产清理未改 |
| static | 最终Ruff四文件、mypy三源文件通过；初版Ruff样式失败及修后日志均保留 |

同scope Source／Cold分别实测单次旧parent **7次codec→1次**，family／Run纯谓词
次数相同；公开入口仍有codec。错family／Run、raw／metadata／binding／Cold job／
extraction各身份关系拒绝，复合scope关闭；两调用间变更、SQL撤权／写入、rollback、
stop及closed连接拒绝；typed cohort变更、授权查询返回后撤权仍被原guard拒绝。
真实Source回执／完整Slot非aid字段拒绝、foreign边界、默认原顺序和exact两接线点
均有定向见证。局部测试禁止Worker／模型／transport，不调用完整_prepare或commit。

广批与closure重叠，不相加成总验收数。广批之后源变更仅两处ready真值判断收紧为
is True，新增相应首pin前回调顺序反例；closure绑定最终四SHA。原source-read／
Store.tx强制closed清理限制仍保留原栈，不为测试变更生产事务／清理行为。

设计、初审P2和最终闭包原件分别封存；两名reviewer只读源、哈希和作者日志，
没有执行代码／测试／DB。限定ACK不代表G0性能通过，运行授权来自当前用户委托。

## 已授权的一次后续验证

冻结候选后正常推送，以干净HEAD重新describe、新目录／SQLite／新单次grant，
使用规范绝对解释器／脚本路径。至多6 Mock交换／8入口，prefix480／G0120／
总600＋TERM5/KILL5清理10秒；原lease30／Run300／TTL1800／reservation60不变，
64MiB采样监测，不称native硬配额或RSS界。只到首G0，禁Cold2/W5，0真实模型／
费用／外网业务／新增安全权限，无自动重试。完整计数、OWNED/LEGACY/UNKNOWN、
两commit、最终期限、逻辑预算和实际清理以随后窗口原件为准。
