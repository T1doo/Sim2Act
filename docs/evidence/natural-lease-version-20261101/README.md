# 自然任务续租绑定原Run版本；大型长事务问题仍开放

源码 `6a0b39e3b569e889aab40d8ae33b160b0610d4b6`，父版本 `0a605f51b8a62dabb3114b6fe8621fe97e831347`。本轮有默认路径安全修复，没有把它称为大型性能或原30秒验收通过。保留5af小型Linux包，未改其字节、扩大30／120／300预算、增加模型请求或启用新租约存储。

## 原方案与当前实现的确切边界

原 [F1 Architecture](../../F1/Architecture.md) 明确租约30秒／独立心跳10秒、总任务300秒；AT-06要求失联和旧fence拒绝提交。**原方案没有要求所有工作30秒内完成，也没有全面禁止续租。** 当前SQLite结算实现的限制在于以下同时成立的工程合同：

| 源码入口 | 当前约束与后果 |
| --- | --- |
| `Store.heartbeat`／`publish_sync_renewal` | 原租约仍有效时CAS，实际事务提交返回后才能发布精确新租约；savepoint或未提交UPDATE不算续租成功。 |
| `natural_spec_runtime._model_settlement_writer` | 全段持有renewal_lock／settlement_lock。普通 `original_interval` 只在入口同步续租一次，然后固定墙钟／单调钟token；第二次cold.commit前没有新的合法提交心跳。 |
| `_sqlite_model_snapshot.transaction/_Read.before` | G0同一个BEGIN DEFERRED WAL快照只读，随后升级写入；任何另一连接提交（包括心跳）都会使旧快照升级失败。原 `test_heartbeat_after_g0_read_cannot_reuse_old_snapshot` 已用真实第二事务证明，不是性能推测。 |
| 完整G0／G1 Graph | 固定transaction／driver／total_changes／source epoch、完整Run行及typed原始数据；不能在其间改lease再重设changes来冒充同一完整证明。 |
| G1与最终commit boundary | 持有SQLite单writer，另一连接心跳不能提交。提交回调／尾窗仍受原双时钟与完整写集边界保护。 |

因此不能仅去掉renewal_lock、加频繁线程、在writer里发未提交lease UPDATE、重置Graph epoch，或把固定token悄悄延长。前者会得到BUSY_SNAPSHOT／写锁等待，后者破坏当前协议。本轮不重复跑没有结构变化的同一大型30秒失败。

## 实际修复：控制改变版本后旧自然心跳不得续租

旧 `Store.heartbeat` 绑定worker／fence／lease，却没有调用方原Run.version。自然后台在deadline=None时仍可走普通heartbeat；真实pause使Run.version增加、worker和fence不变，旧发送者原来仍可能续租。

新可选 `_expected_version` 只接受精确int>=1：在guard后核对原版本，UPDATE同时CAS该版本、已读status及cancel_intent。自然同步／后台／普通结算入口、P-A/P-B source/cold发送边界和非SQLite自然续租均传原Run.version；不从新读行偷换expected。其他family不被强制传新参数。sync_renewal成功marker和锁竞争恢复判据也绑定同版本；显式120结算的原owner/version CAS与marker保持一致。原提交后发布、过期拒绝、最早deadline、回调保护和原子性不变。

修前真实SQLite反例：旧版本同步续租两路均未拒绝，2 FAIL／1 PASS。修后：旧版本不发布、不留liveness写入；版本在guard与UPDATE间改变则CAS失败，整个事务回滚。真实HTTP pause v1→v2、fence不变，原10秒后台节拍于10.0167秒拒绝旧版本、租约不变；最终source另一次原节拍复核在 `real-pause-final-source.json`。测试没有替换时钟／调度器、没有模型调用；这是一项控制／心跳验收，**不是完整自然应用或大型Cold验收**。

## 三个旧失败如何闭合

保留 `pb-owned-default-core-v15-20261101.log/xml` 原文，对应此前344项回归：

| 原失败 | 修正及保留的反例 |
| --- | --- |
| `test_native_dynamic_and_frontier_invalidation[model]` | 原测试直接改新只读View而AttributeError；现在先断言赋值拒绝，再构造修改model的完整合同并替换binding，仍要求DomainError。 |
| 同测试 `[max_tokens]` | 先断言只读caps不能改，再修改重建合同的max_output_tokens并替换binding，仍验证完整失效。 |
| `test_native_optional_absence_preserves_original_complete_path` | 新解释器缺tests导入路径导致ModuleNotFoundError；子进程显式加入现有tests目录，仍阻断可选扩展、走原完整投影并检出原mutation。 |

另行区分真实业务admission错误（3c修复并重跑通过）、原30秒预算拒绝（仍未解决）及旧诊断type(caps)断言（5af修诊断，原退出1不改写），见 [PB默认接线证据](../pb-contract-owned-default-20261101/README.md)。

## 回归与失败控制

第一轮修后58 PASS／2 FAIL：新测试把初始化renewal_lock误当“发布租约”，已在fixture预先建锁；另一项是旧expiry测试只匹配错误的CAS消息。后者在精确父版本导出中也失败：原pre-CAS时间门先返回 `BUDGET_EXHAUSTED / Original heartbeat interval ended`。测试现分别严格核对expiry和wrong-worker的错误码／消息，并保留行未变断言，不放宽到任意异常。

父版本控制初次缺原生扩展而在import报错；随后逐个核父／当前全部C和header字节相同，复用原四扩展才运行该对照，两个失败原件均保留，不把setup error冒充已证既有失败。

85项0失败0跳过覆盖本轮主体修复及已有过期／最早截止／提交回调／快照续租反例，发生在最后非SQLite sender参数漏接闭合前；独审随后指出并修复该漏口。最后产品源码改动后的sender／自然续租／reserve fence／序列化31项0失败0跳过；另加错误版本marker反例1 PASS／9 deselected，产品字节未变。不累加成同一套完整产品验收。冻结后软件资格核验PASS。PostgreSQL仅补完整调用接线，**未执行PG**；0live、无新版Windows、大型重计时或安装包扩签。

## 下一结构修复：实现前必须闭合的生命周期协议

独审确认可行方向是**权威租约控制存储与长业务SQLite事务分离**，让每次独立续租真实提交且仍最多30秒，保留完整G0→W5→G1。此方向尚未实现／启用，不能称大链可用。完整实现至少包含：

1. 版本化owner／fence／Run.version／lease／绝对deadline权威控制行。claim、heartbeat、guard、过期回收、取消／暂停、状态投影须共同迁移；旧runs.lease_until不能同时仍被部分入口当权威。文本扫描有70处直接字段访问、分布于24文件，含状态缓存读写及实验候选，不是70个权限门，须逐一归类，不能只改心跳入口。
2. G0／G1纯业务快照保持完整；可变租约控制由独立当前核验承担，完整保留内容、权限撤权、文件、callback和并发snapshot升级拒绝，不转移旧Graph或PASS。
3. 最终提交前短持控制写锁，核原owner／fence／version、上一次真实续租尚有效、取消／stop及最早绝对期限，并持锁跨原DBAPI commit，封住“检查后被抢占再提交”的窗口。暂停超过租期或控制库失败均不得本地延长或复活。
4. 跨文件崩溃、控制意图及旧软件兼容有明确恢复协议：只读核对原durable receipts与fence，不自动重放模型或效果；不能半迁移既有用户库。

这需要实际产品协议／消费者迁移和并发独审，不是新的免费模型许可，也不是增大30秒常量。本轮先交付已经验证的版本安全修复及原约束事实；大型原30问题仍是明确工程缺口，不用小包或测试数量覆盖它。
