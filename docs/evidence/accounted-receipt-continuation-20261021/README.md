# 首个模型回执 continuation 的精确闭包

基线 `59bd1b3362f11a95210670d371d621aa89b0546e`；上轮首 commit 返回后在原
`_cold_receipts → pin_receipt_binding → _put → frontier.added` 拒绝。首返回不证明
最终期限，旧 UNKNOWN 证据原件不覆盖。本片不改变 lease30、Run300、TTL1800、
reservation60，默认产品路径不启用 candidate。

## 实际最小实现

原 `_ColdTrialGraph._prepare` 的原 Source、recipe 检查、Generate backend version、
Generate 顺序和各 producer 一次不变；仅已有 candidate 选择传入原 `self.platform`，
不是 trial Limits facet。完整 producer 结束后、发行前，对原批准 plan 的前两个槽
按 step id 映射 SQL 返回的两条 operation：VERIFIED resource.read 和 meta.operation_id
对应的 DISPATCHED 首模型。meta.ordinal 必须 exact int 0；不依赖 SQL 行顺序。
其他合法形状发行前 LEGACY，不把原 reader/SQL/guard 错误吞为容量回退。

显式候选在同一原 SQLite 写事务内预读原 `receipt_operations`、两个 `intent`、
首 read 的 `has_effect/step_anchors/progress_event`。这会改变候选路径的 SELECT 和
错误到达时机；不能称全局 SQL 顺序相同。没有提前调用 `_receipts` 或制造 proof，
原始完整返回值在原 mutable frontier 中 fresh 校验；无新增 SQL LIMIT/JSON cap。

发行前绑定 exact platform reader、graph/事务/job、原 platform.binding 对象、
binding prefix、call.meta、pending_id 和该 reader 当前 proof 长度 m。只加入两个
完整精确根 `receipt-binding:m/receipts:m`，不放通整个前缀。`_ColdRunFacts._put`
携带 exact reader provenance；原 `_cold_receipts` 在原位置执行一次，再绑定同次
outputs/proved 对象，原 record_receipts 产生 proof。未知根、错误 reader/job/binding/
pending/m、重绑、复用及跨调用变化拒绝并关闭；未知协议对象不调外来回调，清理
也不影响 foreign owner。未到达的后续域仍不能由此宣称闭合。

`_receipts`、`intent_for`、`receipt_for` 与基线 AST 一致。原 full incoming validation、
fresh C codec、字段/隐藏数据、授权/撤权、完整 DB 读集、事务/fence/stop/期限保留。

## 逻辑预算与范围

新增小型协议/键名管理先按原生长度付 resident/work，再构造额外字符串；不够
发行前 LEGACY。完整消费 plan/source/两 operation/两 stored intent 先 bounded copy，
计量别名/隐藏存储/leaf，再预付 memo 和 DAG 遍历工作。memo 计算 JSON 的展开规模
而不展开共享 DAG，包含 quoted_name、Unicode/astral 转义、整数内容；展开过大
发行前 LEGACY。已有原 SQL 解码和完整 codec 仍属原基线，不称全进程有界。

固定两槽 consumer 的原 resolve/validate/deepcopy、read copy、wanted receipt 的
fingerprint 缓冲、outputs/proved 与新增两根浅表结构重叠，按 U 的 1024 倍逻辑
resident 和 `8*(U+1)^4` 逻辑 fuel 保守预留。不是 CPU/RSS 界，也不声称计量了
原 full codec 的全部分配。完整 binding 的其余字段仍由原 frontier 覆盖；新增
binding 根只引用原对象，不另做全 binding deepcopy。不够只在发行前 LEGACY，
发行后绝不回退、重发或减校验。scope 关闭清新增 result/control 引用及原账本，
账本归零不等于所有 Python 对象或 RSS 消失。

Python 官方文档说明 deepcopy 使用 memo、JSON 的 ASCII 转义和环检查选项；
本实现另外用必要的共享 DAG/quoted Unicode 反例约束自己的逻辑计量，未从小样
推导 G0 收益：[copy](https://docs.python.org/3.12/library/copy.html)、
[json](https://docs.python.org/3.12/library/json.html)。

## 验证记录（不相加）

初版本地 receipt 12P/18.46s；format 夹具枚举错误修为 txt，未改产品 Schema。
中间组合 68P1F/106.46s，唯一 F 是原软件指纹拒绝。作者在该批执行期间继续
修改源文件，此批不是最终冻结验收，原日志/XML保留。中间新增反例 21P1F/42.90s，
DAG 测试错误使用 10^30 夹具 allowance 而期望容量回退；改用有限 512MiB logical
resident/1GiB peak 后定向 1P/1.72s。测试 allowance 不作为产品运行资格。

最终冻结批和实际一次窗口结果见后续归档。局部 SQLite 测试禁止 Worker、模型、
transport，不执行完整 prepare/commit/G0；counter proof 明确是通过原 reader 记录的
合成前置条件，不冒充完整 counter 或账户验收。强制 close 连接的原退出夹具异常
继续按独立内层 VERSION_CONFLICT / 外层 ResourceClosedError 断言，不改生产清理。

独审设计、中间问题及最终六 SHA 源码回执原件均保留；reviewer 只读，无执行，
源码 ACK 不等于性能或最终期限通过。

最终冻结批 **109P/195.61s**（XML 109 tests、0 failures/errors/skips）；Ruff 六文件、mypy 四源文件通过。frozen-before/after 六SHA一致。源码独审两份限定ACK均与同六SHA匹配。

## 本次单次完整输入资格窗口（UNKNOWN）

实际执行源码 `5a012556196271c5b33137a1d0b9b4864c64784c`，source/dependency摘要
`1c12ad8aaeaaaf41c635863275f6c154a5b2d5b4f826da65b91e522a2624de91`；
原 profile 摘要 `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`
未变。只读describe、实际父argv、干净HEAD、远端同SHA及祖先、旧17文件哈希、
无活动旧launcher均核过；本次新目录/SQLite/单次grant，消费一次，无重试。
四源码+两测试是manifest相对前次唯一六项变化；依赖、launcher/guard/observer未变。

| 实测项 | 结果 |
| --- | --- |
| parent/child终态及退出码 | **UNKNOWN / 2** |
| 实际Mock交换/入口/Source delegate | **6 / 8 / 2** |
| 真正进入G0 | 是，原control g0_enter有attempt/run身份 |
| route | **OWNED**，native:issuance；diagnostic_incomplete=false |
| 总work wall / G0 wall | **341.7464095940013 / 30.576640528997814秒** |
| 首次原Cold校验commit | entered，returned=false，DomainError |
| 第二次commit / 原scope返回 | 未进入 / false |
| 最终期限 | **NOT_PROVEN** |
| 直接拒绝 | VERSION_CONFLICT: Production admission expired during verification |
| 原拒绝end / lease deadline | 1792580405.388139 / 1792580404.8569577 |
| 原期限差 | **0.5311813354492188秒**；基于上两原值，不是wall减30 |
| child / parent清理 | THREADS_CLIENTS_CONNECTIONS_CLOSED / OWNED_GROUP_EMPTY |
| 独立进程核实 | 父51568、子51592均不存在；51592 PGID为空 |
| finalization_errors | [] |
| 真实模型 / Cold2/W5 / 自动重试 | 0 / 未进入 / 0 |

W5保持原 `STATIC_STOP_BEFORE_NEXT_STATEMENT_NOT_AN_OBSERVED_COUNTER` 口径，不
杜撰运行counter。0真实模型由固定Mock prefix/transport保护与原prefix-proof说明；
不把产品contract的max_requests7误作本窗口6交换许可的扩容。lease30/Run300/
TTL1800/RPM1/原reservation保持；64MiB仅采样监测，不称硬配额。

本次逻辑预算 resident/live458430612，peak478097556，work188404034025305936651508，
在原512MiB logical resident/1GiB logical peak/fuel内；scope后active=false、live=
resident=0，非RSS/CPU验收。磁盘6785次采样，peak logical2262825、allocated2277376
字节；实际平均间隔0.05037501823761766秒，配置0.1不是定时采样计划。

五阶段 codec **5767次 / 成功返回4030692610字节 / inclusive thread CPU16.17643788秒**。
_prepare 15.361985817s，run_context3.425767411s，accounting0.381547731s，
resolver4.779158223s，archive0.033442487s。仪器有非零开销，未涵盖完整G0 CPU，
也不是观测SHA调用或无仪器性能验收。前次停止位置不同，不把单次差值归因成
本片确定耗时/提速，亦不把总341秒的原RPM等待与G0约30秒混淆。

**本次first commit先失败，实际尚未到新 `_cold_receipts` pass。** 因而本片完整
receipt闭包只有109项冻结批内的局部真实SQLite/原consumer证明；不能称完整输入
运行两proof根或第二commit已经通过。完整PB仍未通过，不推广为生产账户资格。
原Cold RUNNING/RECEIVED可由诊断BaseException保现场，不改生产收尾迎合测试。

最小剩余条件：保持原新鲜性/授权/事务/期限，在同可达路径继续证明可消除的
同次重复计算，并让原首commit、实际receipt整段、第二commit及scope最终期限都
返回；本次0.531秒差值不是稳定优化收益目标。没有自动再开窗口，没有延lease、
减pin、缓存PASS或增加scope权限。本次所有原件（含DB）留在独立/tmp目录，DB仅
归档哈希，不续旧库。后续还需独审最小源码候选，不能盲重复本窗口。

两份最终窗口只读独审原件已归档。0.531秒只是已见首commit拒绝点的期限差；后面仍有原receipt、第二commit及scope最终检查，不是完整G0所需总提速。reviewer均未执行产品/数据库/测试或新窗口。
