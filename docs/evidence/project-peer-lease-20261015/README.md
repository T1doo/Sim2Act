# peer_version有限观测证据（未证实修复）

基线2747eec91fdcfdefb6f575a8d96dbb0dab26114e。两个单例批各1PASS/RC0，完整旧批仍388PASS1FAIL/RC1/NOT_ACCEPTED；源码、测试、资格pin未变，不声称已修复。不累计两次单例为完整回归。

[报告](../../F2/ProjectPeerLeaseObservation20261015.md)。本包包含integration观测/执行/分析脚本、observation两次真实隔离测试及499源码/manifest/XML/日志、METHOD_NOTE粗筛修正、delivery报告和review独审。第一批INITIAL_COARSE是保留的粗筛上界，不当精确重复次数；第二批有精确caller及callback1RETURN。observer脚本副本在终态后封存并与执行前hash核对，不冒称启动时复制。

ARCHIVE.json/MANIFEST.json记录真实包大小/hash和全部regular成员集合，排除声明cache/symlink及根PACKAGE_RESULT自引用。独立外部审核逐成员比较原件/清单/tar的大小/hash和安全唯一路径。归档完整不升级产品验收。原完整FAIL和旧审查JSON重建说明仍在前批原归档，未复制覆盖。真实API0；完整389/安全反例/PG/Windows/原生浏览器/真实P-A/P-B/CI/部署未运行。
