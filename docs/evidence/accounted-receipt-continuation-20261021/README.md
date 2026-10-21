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
