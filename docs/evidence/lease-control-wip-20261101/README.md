# 独立租约控制原语：未接入、未启用

此为当前单writer结构实现检查点，不是产品或大型Cold验收。默认路径未导入该模块；旧5af限制候选保持原字节。

实现实际独立SQLite控制文件、pending claim、真实提交续租、暂停/取消意图、原commit周围控制写锁、唯一settlement ID历史、已提交待ack与commit结果未知分类。已保存5项独审反例原失败：ack重放、stop回调跨租期尾窗、两个foreign session role、直接remember重记时钟。修复后12原语通过；schema/metadata同短事务及版本续租联合检查23通过，不合计成默认产品验收。0模型请求。

仍须闭合：固定最终wrapper/时钟/连接工厂来源；claim与真实main committed记录绑定；新进程Authority级durable receipt恢复；Store发权/所有有效租约消费者/最终原DBAPI提交委托接线；缺控制库拒绝、跨库崩溃和旧软件/旧数据兼容。当前低层row/callback参数不构成生产证据，不能据原语通过启用。

文件静态inode检查可拒绝缺失/普通复制，但不声称证明动态rename后换回时connect实际handle的身份。持控制锁可序列化接管，不保证阻塞fsync返回仍在30秒内。没有扩大30秒/绝对deadline，没有同连接未提交续租。
