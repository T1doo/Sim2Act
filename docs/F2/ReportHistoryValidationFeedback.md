# Report 无效历史证明的晚回执反馈（限定切片）

基线开发分支 `4fc751b2f962f8e009548df8781bc9c74d4f11ea` 已集成已审 PROJECT 候选112c；新产品/测试冻结 `c46093d4d9bdf2c6fda17405307b053d964d8ff2`。只修改 `report-manifest.js` 三处既有 HTTP200 无效证明分支：清除 protected 展示后，将原上下文 `c` 附到原 `VERSION_CONFLICT` 错误。晚回执协调器因此能识别自己刚清除的当前页面，显示“当前展示回读失败，请重新打开或刷新”。

保留既有身份、项目、应用、fingerprint、epoch 与选择代数守卫，不扩大错误提示到已经切走的页面；API 非200错误处理不改。回读不能继续提交写入，UNKNOWN 原键和请求体保留；显式重新打开后仍须新的授权 GET 证明才能显示归档内容。原计算结果、canonical 图、PROJECT计划/jobs、runtime/grants、发布和模型权限不变。

作者新增真实 HTTP/jsdom 场景为 definition/checks 两种接受后丢失响应，各测试 canonical Run 历史、presentation envelope、presentation item 三种有效JSON坏证明；另测试损坏 GET 被延迟后切应用/身份的隔离。固定6秒等待与90秒驱动超时不改。必要回归包括原成功晚回执两阶段、原503历史读取失败、Report锁真实页面与实际afb旧源码数据库升级；SQLite/PG结果和独审应按最终冻结证据读取。

这是三处晚回执自清页的反馈修复，不是全部 HTTP200 损坏形式或其他入口的验收。原112 JS真实页面负例需要在预期提示断言失败，不能把负对照当产品失败。其余 HTTP200 提示限制、PG resources-history/历史全量/探索超时 OPEN；Windows900/Edge240/Node150 未验收。`LIVE=0`、PROJECT `PENDING/BLOCKED_PARTIAL`、semantic `UNKNOWN`、owner `PENDING`、overall `NOT_ACCEPTED`，正式发布关闭。

最终作者 SQLite/PG 各13PASS、0FAIL、0SKIP，每库12实际HTTP页面179检查及1实际旧源码Report数据库升级；独立LIMITED_PASS为8新源码页面111检查及3原112 JS精确预期失败，独审不签PG/旧DB/native。350冻结文件前后逐字一致；独审初始私有harness初始化失败及PG初始化SQL探针exit2全部保留，未计产品通过。完整[本轮证据](../evidence/report-history-feedback-20261010/README.md)含精确命令、负例、失败ledger和冻结清单。候选bc31已普通推送，开发分支按相同350冻结字节快进集成；源码不变，不重复已通过矩阵，[集成证据](../evidence/report-history-feedback-20261010/Integration.md)仅记录集成与最终普通推送核验。
