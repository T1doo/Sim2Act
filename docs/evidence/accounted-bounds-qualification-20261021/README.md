# Accounted bounds qualification — 2026-10-21

基线 `f51bbaae3f7f5bab64c79c4c135d0b0d3a2951c8`。本片停止寻找完整旧接受域的统一产品常数：**固定列数、成功链数及包络上界成立，但不能证明完整 Run/Attempt/sidecar 的总大小。** 物理数据库、整数解析器和机器内存当然有限；这些随部署变化的极限不是原方案给定的 owned 子域预算。

仅新增独立离线计量脚本与本审查包。`src/`、产品默认模式、采样、预算、事务、授权/fence/期限及所有 full checks 不变；未启用下述分流。没有 Worker、业务 Mock、真实模型、G0、W5、完整 native `_prepare` 或两次 commit 运行。旧窗口原件不变。

## 来源覆盖与有限界的作用域

`BOUNDS-REVIEW.md/json` 是另一 agent 的只读源审原件，`WRITER-INVENTORY.json` 列出全 src AST 直接 `insert/update(runs|attempts).values(...)` 的 **65 站**：Run 5 insert / 42 update，Attempt 1 insert / 17 update，保留动态 `**values`。这是静态直接写站点清单，不是外部 SQL 写者穷举。源码与安装依赖 SHA 在 JSON 中。

| 范围 | 已证的界/来源 | 不能推出的结论 |
| --- | --- | --- |
| Run 18 列 | `db.py:95`；`cold_accounted._FIELDS['run']` 完整列集 | 列数不是叶长度、JSON 节点/深度/字节上界 |
| Attempt 13 列 | `db.py:178`；`_FIELDS['attempt']` 完整列集 | `String` 无 length，`JSON` 无 CHECK/统一大小门 |
| 原 producer 成功外形 | `pa_trial_dispatch.py:1591-1630`：Source 1 Run、2 actual/chain、2 ns_reads；Generate 1 Run、3 actual/chain、0 ns_reads | `.all()` 在 3/2 gate 前，拒绝前的获取/解码数量仍不能用成功计数证明 |
| 五链原业务字节 | 原门完整通过后，每链 request/received canonical 各 ≤32768；固定 3+2 链 | 5×32768 仅是部分字节，不能当 packet 大小；还保留 parsed、row、模型、引用和隐藏数据 |
| JSON 包络 | `contracts.strict_json:397`：调用方 max_bytes、深度 ≤20、重复 key/非有限值拒绝；PB 相关调用 32768 | 默认 max_bytes 为 65536；不能声称项目每个 JSON 都经 32768/depth20 门 |
| Ledger/usage | `production_trial_policy._ledger:200`：slots≤7、stage 3/2/2、每 run 预留≤64000、全体≤192000；accepted total≤wire+1024；`_known:296` completion≤1024、response ASCII≤32768 | 模型的 ge 字段不能独立证明该界；未完成/拒绝/普通历史行不自动具有这些成功条件 |
| Generate 接收 | `goal_applications.py:68,594,1634`：canonical ASCII≤32768、安全 msg UTF8 JSON≤16384，archive 重读原字节 | 不涵盖完整 parameters/context 的额外值 |
| Source context | `natural_spec_runtime.py:927`：确切键集、计数/messages 关联；Generate `goal_applications.py:1928` 无同级 exact ctx key gate | Source 局部合同不能推广给 Generate、所有 Run 或底层存储 |

两张完整列表及来源逐项见源审表：Run `id/project_id/principal_id/runtime_id/goal/resource_refs/status/request_key/fingerprint/created_at/lease_until/fence/worker_id/context/result/error/cancel_intent/version`，Attempt `id/run_id/created_at/mode/request_model/response_model/status/usage/reserved_tokens/parameters/response/error/elapsed`，没有遗漏最后状态/错误或隐藏存储以制造上界。

固定模型同样需区分 schema 与成功 producer：

| 模型 | 固定字段、显式长度/范围 | 尚须关联门/没有独立上限的字段 |
| --- | --- | --- |
| Slot / Identity / Outcome | 5/14/6 字段；hash64、run36/attempt40、worker KEY≤100 ASCII、account OPAQUE≤200 ASCII、quota≤200字符、wire_bytes≤32768 | runtime_id 无 max；version/fence 仅 ge；Outcome 数字仅 ge。成功 ledger/当前 Run/原 wire/usage 才进一步收窄 |
| Capture | 11 字段；raw_bytes≤131072、body_b64≤43692字符、hash64 | canonical_ascii_bytes 仅 ge；成功 body/derive/complete/omission/verdict/Outcome 关联门才证明合法接收≤32768，不以单个 model_validate 替代 |
| BodyArchive | 15 字段；owner/project/runtime≤100字符、body_b64≤43692、hash64、固定 literals | byte_count 仅 ge；`_body_payload_from_facts:169` 完整原 body 关联才要求 0<len(payload)==byte_count≤32768 |

字符长度不能直接当 UTF8/JSON ASCII 字节数；例如非 BMP 字符 ensure_ascii 编码为 12 字节。布尔、固定 literals、finite float 和固定字段数量的局部界可用；没有为 version、fence 或未经关联的计数凭空补 le。

## 真正没有全域产品界的来源

Run 初始写入：`Store.submit_tx db.py:966→1072`、`app_jobs.enqueue:369`、`csv_dag.enqueue_tx:383`、`local_record_apps.confirm:899`、`protocol_jobs.enqueue:733`。Attempt 初始写入唯一为 `Worker.reserve worker.py:258`，Source/Generate 接收分别在 `natural_spec_runtime.py:3545`、`goal_applications.py:1646` 更新完整事实，后续修复/终态写见完整 inventory。

源审保留 7 个**未执行的源码反例**，并标明接受域：Store 的 key 长度不受 HTTP RunInput≤100 自动约束；checkpoint 只合并 tools 后保存整个 context；普通 finish 可保存通用 result/error；普通 synthetic mock 的合法短 content 可附长 raw.model，经 enforced=False 实际写入 response_model/parameters；normalize_usage 没有通用位数上限。它们不是“这些值能通过完整 PB”的声明。足以否定把所有 Store/DB/旧原生输入统一收窄成 PB wire 大小；没有为执行反例打开窗口。

真实固定 `select(runs)` / `select(attempts)` 无 join 多列，未经外部变更时原始 data 确为 18/13 位置。但 exact RowMapping 类型不是查询来源证明：原生构造器允许额外 `_data`，合法位置的额外字符串 safe-index 别名不受可见列数约束。`_cold_graph_row_storage:1680` 保留全部 data 和安全字符串索引；foreign key 即使不进入 payload 也有迭代成本。不能用 visible keys 投影裁掉 sidecar。

安装 SQLAlchemy 2.0.48 源码 `_py_row.py:39` / `resultproxy.pyx:14` / `row.py:171` 证明上述存储传递；`sqltypes.py:2811` 默认 JSON result processor 用 dialect deserializer 或 json.loads。官网 [2.0 JSON deserializer 文档](https://docs.sqlalchemy.org/en/20/core/engines.html#sqlalchemy.create_engine.params.json_deserializer)与此一致；本项目实际依赖以归档 SHA 为准，不采用官网最新补丁版替代已装实现。它不会自动调用本项目 strict_json。DBAPI 全行与 JSON 解码发生在后置 meter 前。

现有 `_cold_graph_row_storage` 会先完整建 lookup，`_capture.row` 又建 names tuple/set、visible dict 与 sidecar；`_freeze` 先做全字符串 encode、base64 flat 等部分分配再限额。因此“先调用它们、后计量”仍不是这些前置分配的限额证明。

## 本片实际代码：仅 prepared native value 的流式计量

`scripts/diagnostics/cold_accounted_size.py::measure_prepared` 有显式正预算，无任何产品默认值，无 src 导入点。仅支持与 private `_freeze` 一致的 exact native dict/list/tuple/str/quoted_name/bytes/int/bool/finite float/None。未知类型、RowMapping、Pydantic、环、不支持的键和运行时不可编码的大整数返回 incomplete；不触发 foreign reducer、iterator 或 metaclass equality。它不检查业务授权、内容有效性、关联或新鲜性，也不生成 Packet/digest/handle。

成功时，对**同一个已准备好的值图**精确报告唯一节点、存储边、最长路径深度（root=0）、leaf bytes、字符串 UTF8 surrogatepass/ASCII 转义字节、base64 ASCII 和 private 编码总字节（含 envelope、tag、引用索引、括号/分隔符）。未复制 body，编码膨胀可从后三项与原 leaf 计数直接比较。不是预测 C Pickler 或 G0 成本。

- 每调用局部 active/done 与强 source 引用，复用已完成 DAG 子图并检查 depth+height；显式栈不受 Python 递归深度限制，不按路径指数展开。
- dict/sequence 先用 O(1) len 作边数下界拒绝，再逐边迭代，不造全 keys/ref 表。字符串先廉价长度下界再逐字符计量；bytes 用 4×ceil(n/3) 计 base64，不整块 encode/b64encode/JSON dumps。
- 整数先 bit_length 预算，再有界十进制位数算术而不建十进制串；同时遵守当前 runtime digit limit。临时算术由显式 integer_bits 约束，不新增产品数值限制。
- 超限报告 `complete=False`、reason 和已观察前缀/下界，不能用其中计数冒充完整总量。不缓存跨调用成功；同步调用要求输入不变，结果不是冻结/发行证据。

测试使用真实 `_freeze` 做 native prepared 值的精确差分（含所有单字节控制/DEL、BMP/astral/lone surrogate、base64、真假/整数/浮点、随机共享 DAG）。边界值及小一值、80层共享二叉 DAG、1500层显式栈、恶意 metaclass、hidden RowMapping 拒绝均覆盖；巨大浅容器/叶提前拒绝的 tracemalloc 只界定诊断临时分配，不把预先分配输入/DB 内存计入。首轮 38 项结果保存在 before-review；最终结果见 junit/log 与下方记录。

1500 层用例只证明 meter 能完整计量该 private 格式，不证明当前递归 `_freeze` 在该深度能执行；`complete=True` 不是 encoder 成功或发行资格。差分用例严格使用实际 `_freeze` 可执行的有限深度数据。

**该原语没有覆盖 `_capture` 的 raw→prepared 投影。** 尤其固定 model_dump 的对象分配/别名、schema envelope/sidecar 新对象、RowMapping lookup 和任意 foreign metadata 的工作量都未被本脚本计入。不能先无界 `_capture` 再调用它而宣称发行资格闭合。下一步若接线，必须共享受控表示构建规则/虚拟投影，在复制前限制原 keys/data/index 的全部扫描项（含忽略项）与中间临时量，保留全部字段/隐藏值，随后复制时再强制同一预算；本轮未实施或启用这一步。

## 兼容子域最小设计（只读设计 ACK，不启用）

全域无统一界，未来优化应为有限可证子域而非新全局拒绝。整族必须一次选路，不能先发行 Source 再发现 Generate 超限而退回。拟定状态：

```text
original producer Source once -> original producer Generate once
     | failures keep original rejection/cleanup
     v
UNISSUED staging + final original full guards + joint bounded eligibility
     | capacity/representation inapplicable only      | all qualified
     v                                               v
LEGACY (same completed raw facts)                 OWNED (issue both)
     |                                               |
     +---- original current action/commit checks ----+
                           any failure -> CLOSED
```

1. 在同一原事务、read scope、phase/schema、source-generation 下，让两个原 producer 各完成一次，并暂存未发行的完整事实/receipt。保持原 Source/recipe/version/Generate 验证顺序；中间若需只读 legacy 断言也不提前创建 owned mode/handle。现 `_completed` 即时发行实现需要明确调整，不能仅把第二次超限 catch 后调用旧路径。原 producer/权限/漂移/模型/关联错误不是容量不适配，保持原拒绝，绝不吞掉重跑。
2. 最后原 full guard 后，由纯计量对完整 Source+Generate cohort 决定一次 immutable route。在任何新 issuer、owned 消费或业务动作之前，**仅容量/表示能力不适配**选 LEGACY，沿原完整路径消费同一已完成 raw 结果，不重读 producer/重发/跳校验。原完整读取/check 继续按原路径新鲜执行。选 OWNED 才复制并私有发行两 family；逻辑 complete/input/stage 同 scope 同族。
3. 资格结果不是永久授权，也不是一次 hash 后不读。复制后原 full guard，动态 worker/settings/model/max_output_tokens/transport/current binding、取消/停止/lease/fence/授权及原事务提交规则保留。发行开始后的复制/计量溢出、变更、关联或动态失败关闭整个 scope，不降级、不补发、不重试。预检与复制间变更须拒绝；不能用身份或旧 digest 命中资格。
4. 只将有资格的内部优化预算与原业务限制分开。所有旧域超限值仍有原 full 路径；不裁字段/sidecar、不更改原租约或业务 cap，不要求用户接受新产品限额。Route/version 仅私有，不混入原 pickle raw/pre/post/origin/software/公共指纹合同；软件修订本身仍正常改变内容指纹。

本设计还须闭合：raw→prepared 全字段/别名/隐藏存储的流式适配与 mutation 防御；原查询 `.all()` 和 JSON 解码前是否能做同事务有界获取（后置 meter 只保证自身复制，不能冒称前置获取有界）；其他消费者 `_freeze` 的 ledger/resolved snapshot/Slot/usage/full Run 比较；两 packet 与 memo/临时表同时驻留的整 scope 峰值，不能用 per-packet cap 冒充总内存 cap；选路和所有错误的 SQLite 实际接线回归。本片保留原事务与全部原扫描，未为这些剩余条件签发运行资格。

## 实际验证与审查范围

最终命令/输出为 `pytest.log`、`junit.xml`、`checks.log`。源码独审与计量独审分开记录：前者仅文件/AST/哈希、未运行测试；后者仅静态读新增脚本与设计。最终主写入者测试使用合成纯数据，不依赖上轮消费者夹具，不打开 SQLite/Mock/Worker。没有扩大为重复 G0/完整 _prepare 验证，也没有性能通过声明。

最终 **39 passed in 0.30s**；Ruff 两文件、mypy 计量脚本、git diff --check 通过。`src/` 相对基线无差异。首轮 38 项日志是 metaclass 独审修正前的观察，不代替最终源码的结果。

```text
env -u SIM2ACT_TEST_DATABASE_URL -u SIM2ACT_RECORD_PG_CONFIG .venv/bin/pytest -q scripts/diagnostics/test_cold_accounted_size.py --junitxml=/tmp/sim2act-accounted-bounds-20261021/junit.xml
.venv/bin/ruff check scripts/diagnostics/cold_accounted_size.py scripts/diagnostics/test_cold_accounted_size.py
.venv/bin/mypy scripts/diagnostics/cold_accounted_size.py
git diff --check
```
