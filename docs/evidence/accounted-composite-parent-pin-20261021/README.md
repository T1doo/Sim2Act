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

## 本次实际窗口：首次commit返回，新continuation拒绝

实际执行候选 `ef040cfc780d37d4442327231d21ab500b97a661`，source/dependency摘要
`dac37ef4adfd9832653ab9ed61d8a131117edcc3bcf17246a2f9e871661f397c`。
与上轮完整manifest比较，恰好变化3个源文件及1个新增测试，依赖／launcher／保护／
native核心均不变；profile仍为原f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f。
实际绝对parent argv已只读保存，旧原件哈希和旧进程组均在启动前核验。

| 项目 | 实际结果 |
| --- | --- |
| parent／child终态 | **UNKNOWN**，退出码2，business_acceptance=INTERRUPTED |
| 交换／入口／Source同步delegate | **6 / 8 / 2**，6条实际合成wire归档 |
| route | **OWNED**，native:issuance，diagnostic_incomplete=false |
| launcher work wall | **341.4612587740012秒** |
| G0 wall | **30.078201882999565秒**，带仪器，非性能验收 |
| 首次commit | **returned=true**，记录成功原authority的11项deadline |
| 第二次commit | 未进入；只有ordinal1记录 |
| scope／最终期限 | original_scope_returned=false，complete=false，NOT_PROVEN |
| 直接错误 | VERSION_CONFLICT：**Unexpected native continuation root** |

此处commit为原Cold校验函数。原首次commit的期限断言曾通过，但观测器没有
保存首次返回时间戳，不能据此声称返回时仍在lease内。本次新错误没有原admission
diagnostic/end，不用G0 wall减30秒声称实际量得lease超时，也不推第二次或最终
期限能够通过。保持原selected UNKNOWN分类，不宣称G0／完整PB通过。

原栈明确经过 `advance_model:3680 → pa_spec_apps._cold_receipts:1669 →
_ColdRunFacts.pin_receipt_binding:469 → _put:413 → _ColdGraphRead.add:1872 →
_Frontier.added:384`，在两commit之间原正常回执读位置拒绝。
runtime源码推导新增key为 `run-facts:<job-id>:receipt-binding:<len receipt proofs>`，
value是原binding对象别名；诊断未保存实际name，不能把某个后缀当实测值。
当前native future集合是12个固定commit／settlement根加最多2个精确Release键，
没有这个正常惰性读根，且没有针对其新增key／浅表entry给出发行前额度见证。

本轮没有追加白名单、通配前缀、删除continuation门或发行后LEGACY回退。
最小剩余条件是证明同reader／同事务scope内的精确key和原binding关系、发行前
额外元数据预算，保持新根完整校验、fresh codec和防重绑；不能仅加1个常量或
放行整个run-facts前缀就声称后续receipt流程闭包。未到达后续仍未知，本片不做
更多根迁移，不再发起窗口。

### 实际分段成本和范围

| 已观测阶段 | codec调用 | codec线程CPU秒 | wall秒 |
| --- | ---: | ---: | ---: |
| _prepare | 3590 | 9.281794468 | 14.803792279 |
| _graph_run_context | 892 | 2.519207181 | 3.287720152 |
| _graph_pb_accounting | 95 | 0.274048235 | 0.378141105 |
| _graph_resolve_trial_source | 1143 | 3.295056682 | 4.410669205 |
| _graph_pb_archive_chain | 9 | 0.025695145 | 0.032120581 |

五阶段共5729次codec、3989501290累计返回字节、15.395801711线程CPU秒；两目标
阶段共2035次／5.814263863线程CPU秒。上一窗口两目标为1510+2325=3835次，
本次为892+1143=2035次，与局部7→1机制一致。两次不同终止点的单轮运行不是
受控总体性能对照；不把累计返回字节当峰值内存或SHA实测量，不承诺省11秒或
把首commit返回包装成最终验收。

### 实际资源、清理和封存

逻辑resident/live85803380、peak105470324、work50098473668149788430366，
退出后active=false、resident=live=0。它们是逻辑账本，非RSS或全进程CPU界。
磁盘6778次采样，峰logical2257144／allocated2273280字节；实际完成间隔
min0.000172228／max0.157804755／mean0.050384992秒，约19.84718Hz。
未触及64MiB，仍是监测预算。child报告THREADS_CLIENTS_CONNECTIONS_CLOSED，
parent为OWNED_GROUP_EMPTY，finalization_errors=[]；另只读核launcher及child
PID45056均结束、原PGID无成员。源摘要child前／后及parent清理后相同。

Cold2／W5未到达依据原StopBoundary控制流，原字段明确不是独立W5计数器。
0真实模型的依据是固定合成Mock归档和网络拒绝路径，diagnostic未另给独立真实
模型counter。没有复用grant／库、重试或扩大期限／安全权限。

原目录保留于
`/tmp/sim2act-authorized-composite-g0-59ed1f1cfba542958a5e1f5c67a7e7ec/`。
window/raw-map.json给原件大小／SHA及gzip无损封存路径；fixture.db仅原地保全
和封存哈希，不复制Git、不续用。window/reviews为两份只读结果独审，不是新的
运行授权；先前代码／局部证据ACK与本次未通过结果分开保存。
测试失败原日志的行尾空白逐字节保留，Git diff-check对此有告警；源、测试和
脚本diff-check通过，不修剪原证据来制造整树检查通过。
