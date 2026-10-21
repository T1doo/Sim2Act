# 本轮核对的规范与官方事务资料

原产品规范为仓库冻结 V5：`docs/sources/V5/平台产品设计.md`，SHA256 `e30251bda3f92a95728b79e002d75378669536aad1308304d73a3993dfbced78`；原阶段计划 SHA256 `00c0e820136eab631b99548bd77f8822dcfd2bf4628cb9469ba5a878926857cc`。本轮完整 hash/大小均与原 manifest 一致，不改原文。具体 §5.5/8/9.2/10.2 到设计边界的映射见 DESIGN。

- [SQLite Transaction](https://www.sqlite.org/lang_transaction.html)：核对单写者、BEGIN IMMEDIATE 即时写事务和事务持续到提交/回滚。用于说明保留同事务也保留写锁，不能把该设计说成已解决 heartbeat 竞争。
- [Isolation In SQLite](https://www.sqlite.org/isolation.html)：核对不同连接提交可见性及写入串行化。连接本地 epoch 不是跨事务/跨连接完整变更证明。
- [PostgreSQL 16 Transaction Isolation](https://www.postgresql.org/docs/16/transaction-iso.html)：核对默认 Read Committed 的语句级快照以及 nonrepeatable/phantom/serialization 问题。不能把 SQLite 原排他写区间或“同一事务”几个字直接当作 PG 的完整谓词一致性证明。

这些是设计机制的官方依据，不是本轮数据库运行结果；没有打开数据库或运行 PG/SQLite 并发测试。
