# Agent v2 回读与 idle 判定竞态

确定性真实HTTP/JSDOM复现：已持久SUCCEEDED v2及200实例回包被暂存时，terminal poll正在等showInternalInstance，view.busy仍false；同时手动refresh只刷新实例列表（原instance已null）。旧idle提前返回，列表v2、详情正在读取且0条，原v2断言失败。释放同一真实200后恢复同iid的v1/v2两条与SUCCEEDED。

这证明原!busy等待不足，符合CI截图；不能声称已抓到原Windows精确时序。建议native oracle等当前iid/data_version2/真实v1v2两条内容后保留原断言，不改产品终态/延长时限/弱化安全。详见review.json和owned-v2/reproduction.json，helper首400失败保留。
