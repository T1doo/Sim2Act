# Accounted 事实族：离线所有权证明，尚未接入运行路径

基线 `f814843a1ce776c8cdc6387352650b743f8ca0d2`。本片收窄到 `cold-trial:accounted-generate/source`，实际完成完整字段投影、独立表示原型及必要反例测试。[独审](REVIEW/REVIEW.md)定位四模块内的消费者闭包；[最小边界](MINIMUM-BOUNDARY.md)列明必须一起迁移的具体读点。没有新增全平台重构或 CSV 授权功能。

**结论是离线表示组件可继续评审，运行接入尚未成立。** 当前 `src/`、现有 `tests/`、采样器、预算、租约、事务和权限不变。未删除或跳过任何 pin、哈希、签名、动态授权、fence、停止或期限检查；没有第四个 Mock 窗口、真实模型、G0/W5、DB 打开、旧实例恢复或外部进程操作。不能把本片称为 G0 修复或性能验收。

[原型](PROTOTYPE/accounted.py)完整复制 Run 的 18 列、Attempt 的 13 列、每条 chain 的六项和 Source NS read 的五项；真实固定模型包括 Slot/ReservationIdentity/Outcome、Capture、BodyArchive，字段清单由源码 AST 提取，见 [SCHEMA-MAP.json](SCHEMA-MAP.json)。原 Pydantic 嵌套存储检查在固定 serializer 前执行。业务视图将受控 `quoted_name` 列名投影成 str，另保留完整受控 keys/data/safe-index 侧投影，包括不可见数据位置；没有把 `dict(row)` 说成全部隐藏存储。

[平坦节点原型](PROTOTYPE/owned_graph.py)仅在一次 freeze 中复用已完成的不可变子值，active backedge 拒绝循环；保存子图高度，复用时仍检查最长路径深度。返回值只含 native immutable 值、元组与字节，不含外部模型、行、metadata、dict/list、builder 或闭包。节点编号保留重复边，编码不沿 DAG 的所有路径展开。40 层共享二叉 DAG 从 8 节点/7 边/183 字节到 48 节点/87 边/852 字节，见 [原始计数](PROTOTYPE/DAG-MEASUREMENTS.json)。这是表示规模计数，不是 CPU 基准；成本须计入独有节点、边和字符串/字节负载，不能只称 O(V)。旧代码其他根仍可能重扫相同内容。

实际输入是**第三窗口已归档的五组 Generate/Source 请求和响应字节，加人工构造的完整 native RowMapping 及真实模型类型**。不是恢复原库、原 G0 完整事实、有效 producer 证明、LIVE 准入或代表性性能夹具。默认 Capture/BodyArchive provenance 与 MOCK 行只用于离线投影，不能冒充真实来源。

最终 [11 tests passed，0.40s](PROTOTYPE/PYTEST-FINAL.txt)，[tripwires](PROTOTYPE/TRIPWIRES.json)无触发。覆盖所有 3/2 aid 的嵌套输入隔离与下次重新读取、完整 schema 投影、旧 capture/archive 指纹与原字节/规范化证据、循环/共享深度/规模拒绝、隐藏行数据、未知回调零调用、精确数值及序列类型。测试保留了 UNKNOWN 和不一致事实，由原叶子继续拒绝；快照本身绝不是授权证明。详见 [测试及缺口映射](COUNTEREXAMPLES.md)。

失败原件全部保留：首轮 7 passed/3 failed，定位轮 1 passed/2 failed；一个是严格比较器不接受旧 `dict(row)` 的 quoted_name key，需要分开业务视图与存储投影；另一个是测试赋值被 Pydantic frozen 保护拦下，改成验证底层存储意外变更。独审随后发现旧解析器/C Pickler 可表示孤立 surrogate，而原型默认 UTF-8 计量会拒绝。先用旧原型实际复现 [UnicodeEncodeError](PROTOTYPE/PYTEST-UNICODE-BEFORE-FIX.txt)，再改为 surrogatepass 计量及原来的 ASCII 转义编码；完整 11 项回归通过。修复前源码和 10 项通过原件同样保留，不改写历史。

仍需闭合的运行条件很具体：scope/role/phase 发行接口；stage tuples、complete 副本、typed cohort 和归档叶子全部改读同一 owned family；所有外部可变引用均退出该消费者闭包；完整规模限制从原输入上界推导；新私有 manifest 与 pre/post 模式隔离。`Packet` 可人工构造，`View` 不是旧 typed helper 的替代合同；测试中的 `materialize_oracle` 只供旧值/指纹对比，绝不能接入消费者。当前这些条件未实现，因此原检查继续完整生效。

来源哈希见 [SOURCE-HASHES.json](SOURCE-HASHES.json)，独审与实际测试分开记录；[官方资料](REFERENCES.md)辅助说明 frozen 模型与 RowMapping 的边界，未拿通用文档替代本仓库证明。复现方法见 [REPRODUCE.md](REPRODUCE.md)。交付提交 SHA 与远端状态以最终回复为准。
