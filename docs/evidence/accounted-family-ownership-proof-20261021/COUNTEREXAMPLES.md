# 实际回归、反例和未证明项

| 性质 | 本轮实际证据 | 限制 |
| --- | --- | --- |
| 全部当前列和固定模型字段 | Generate/Source 各完整 shape；actual 3/2，chain 6 项，NS read 5 项；类型精确比较受控业务视图，模型/身份与 archive 指纹对比 | 行值/身份人工构造，只用已归档原字节，不是原 G0 事实 |
| 无可变 source 引用进入 packet | 直接递归 inspect 所有实际存储对象的 exact type；每 aid 嵌套 mutation 后原 packet 不变，下次 capture 不同 | 只证明 completed packet；当前 runtime/消费者仍有原引用 |
| 隐藏行数据完整 | native RowMapping hidden positions/alias mutation、hidden cycle/未知类型拒绝；duplicate normalized keys 和 bool index 拒绝 | metadata 原 helper 当前检查保留；未宣布隐藏布局为 V5 永久业务版本 |
| 未知 callback 不执行 | 外来 nested value/key 的 iter/eq/str/reduce 全零；typed 额外存储拒绝在 serializer 前 | 不把任意进程内 monkeypatch 的精确异常次序变成产品要求 |
| DAG | 40 层共享、node/edge/编码实数计数，cycle 拒绝，复用节点另一条更深路径仍越界拒绝 | 无计时/无 full G0 热点量化；oracle 不准接入运行 |
| 精确值域 | int/bool/float、负零、list/tuple 分别编码；非有限数拒绝；escaped lone surrogate 经原 strict_json/C Pickler 接受，新编码保留，旧 canonical 相同 | 私有新 digest 可区分局部共享结构；原业务版本不按这种身份区分 |
| UNKNOWN/不一致不漂白 | 原 stage usage 对不一致行拒绝，原 capture SHA 对不一致值拒绝；owned packet 保留 unknown | snapshot 可以复制无效事实，**不是 verifier** |
| authority 反例 | 缺/增列、3/2 数量及 role shape 拒绝；测试明确展示 swapped chains 仍可复制，packet 无执行许可属性 | aid/run/role/scope 完整关联、issuer 不存在，原 producer 必须保留 |
| 持久兼容 | Capture identity pair/BodyArchive fingerprint，wire/raw/canonical、public receipt 基础七字段实际对比 | 未证明完整 public receipt、StageAuthority、post/origin 桥或运行差异 |
| 动态新鲜性 | 本轮源文件零改动，原授权/collection queries/fence/停止/期限/事务检查都在 | 本轮无 DB/Run/Mock；未新增撤权、提交回滚或期限集成结果 |

最终 11 项测试通过。此前首轮 3 个失败、定位轮 2 个失败及 surrogate 修复前 1 个失败均保留，不抹去未通过结果。`TRIPWIRES*.json` 对应各轮，测试前的纯模块 imports 不冒称受 tripwire 审计。tripwire 涵盖 Store/Worker/InternModel 构造与业务入口、DB connect、Mock/HTTP transport、socket connect/getaddrinfo、subprocess；无触发。

原 `test_cold_trial_guard_delta` 保护第 3 aid 及完整 cohort 的实质性质：未来 owned 路径必须消费所有 3 个 aid，不能只护当前第一个；复制完成后 discarded source 变化不污染 owned value，但任何消费者回读它都违反迁移合同。本片对每 aid 的隔离给出证据，**没有**据此删除该旧测试或声称当前消费者已改成 owned。旧源文件 hash 随本片归档。
