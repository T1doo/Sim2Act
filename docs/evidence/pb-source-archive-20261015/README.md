# 原trial来源归档离线证据（完整回归FAIL）

冻结源码 `056fb5a4796ba91cd5c2bcd12628bd06d2eae9ca`；完整389项结果 **388PASS / 1FAIL / 0ERROR / 0SKIP / 0 deselected，RC1**，整体NOT_ACCEPTED。精确失败及剩余阻塞见[交付说明](../../F2/PBSourceArchive20261015.md)。独立P-B链即使PASS也不构成整批通过。

5个归档实际字节/hash与成员清单见ARCHIVES.json和各MANIFEST；逐成员核验源集合、大小/hash、安全相对regular唯一路径。仅排除声明的cache、symlink/current别名及integration根PACKAGE_RESULT自引用。归档完整性通过不代表产品回归通过。

- tests：setup NOT_RUN、capture 7P1F/8P/11P、旧7c定向20P、pointer首15P/扩展29P1F/修正30P，以及各批执行源码/封印和初始静态失败，全部保留且不累计389。
- regression：旧7c完整358P1F/RC1与当前056完整389/RC1的命令、PROCESS_EXIT、collection、XML、streams、RESULT、FAILED_SUPPORTING_CHECKS、源码前后/副本和真实回执；两版质量结果保留。
- review：设计/代码/P2修复/85模块资格/历次终态/当前失败/失败感知脚本/最终文档独立审查。
- integration：两版终态audit与pin、7c transport恢复、056两次连接通知、peer_version公开日志时间线、执行/归档/正常push核验脚本。postpush回执另存工作区外部文件，避免自引用。
- design：原计划范围、旧7c失败、056最终说明；DRAFT为准备稿，不代替FINAL及RESULT。

独审输出曾误覆盖旧7c审查JSON，覆盖前原hash未知；误写056副本、明确标记的7c重建审查件及纠正哈希说明均保留，非字节恢复。原测试RESULT/XML/父audit未改，详见review/REVIEW_OUTPUT_NAME_CORRECTION_056.md。

499源码before/after/copied/root/Git及30+原359顺序保持。当前汇总为FAILED_SUPPORTING_CHECKS.json；旧7c失败不覆盖。真实书生/Intern/API调用0；仅MockTransport实际Worker。PG/Windows/原生浏览器/人工语义/真实完整P-A/P-B/费用/远端CI/部署NOT_RUN，formal publication false。
