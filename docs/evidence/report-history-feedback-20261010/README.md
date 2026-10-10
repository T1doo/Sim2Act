# Report 无效历史证明晚回执反馈证据（2026-10-10，北京时间）

基线开发分支 `4fc751b2f962f8e009548df8781bc9c74d4f11ea`；产品/测试冻结 `c46093d4d9bdf2c6fda17405307b053d964d8ff2`，350文件测试前后逐字一致。仅三处既有 HTTP200 无效证明分支的错误附上原上下文 `c`，保留清页、身份/项目/应用/选择代数守卫和原键恢复行为。产品范围见[修复说明](../../F2/ReportHistoryValidationFeedback.md)。

作者 SQLite13PASS/0FAIL/0SKIP，179.50秒；PostgreSQL17.9 13PASS/0FAIL/0SKIP，291.95秒。每库12实际HTTP/jsdom页面179检查及1实际afb旧源码Report数据库升级。新增8页面130检查：definition/checks接受后丢失回复，分别遭遇canonical history/presentation envelope/presentation item的有效JSON坏证明，以及延迟坏GET后切应用/身份；验证清页后守卫提示、UNKNOWN精确body/key保留、显式重新打开GET恢复无POST与外来页面状态不变。另含原成功晚回执两阶段、503读取失败、Report锁正常页面。沿用原6秒idle及90秒驱动预算。命令/JUnit/页面/实际旧版升级证明见同目录；不重跑全矩阵，也不将原112静态JS负对照称数据库升级。

独立复核对最终c460给出 LIMITED_PASS：[报告](independent/FINAL_REVIEW.md)/[精确清单](independent/FINAL_REVIEW.json)。11pytest PASS/0FAIL/0SKIP，107.945秒，包含8新源码真实HTTP/jsdom页111检查以及3原112 JS真实页面负对照。旧页先通过8/8/9个自清/原body/key前置检查，再在预期“当前自清页反馈可见”断言失败；这些是受断言验证的负例，不是产品PASS。每页13实际加载web哈希，350冻结文件及68产品Gitblob/hash前后完全匹配，其余67产品文件与原112未变。SQL事件审计恢复/坏历史GET无DML，只有显式POST写入。独审不签PG、旧DB升级、其他坏响应形式、逐item历史map行为、native或整体；作者PG/upgrade另列，不能合并为独审。

51个独审白名单文件逐大小/SHA复制，含两报告、正式/探针/初始harness失败、原112 JS、3负例及全部SQL审计，见 independent-copy-receipt.json。初始11私有harness初始化失败没有执行页面，修正仅发生在私有harness，单探针13检查不重复计入正式111检查；原失败日志保留。冻结脚本初始路径/数量修正也记录在独审harness-freeze-notes.md。

候选 `bc31c20d837d4f503a86d5fcac819c071bc0f0da` 已普通推送并将开发分支ff-only到相同冻结字节，[集成记录](Integration.md)与integration-byte-proof.json保留精确证明。仅此集成证据提交后普通推送开发分支，不重新启动已结束的13项矩阵；远端精确SHA与未推送差异按最终核验记录。

只使用本轮核验完整ID/owner标签的PG：network none、Unix socket、零公开端口，前后schema/测试角色/public表 `0|0|0`，正常停止后容器/匿名卷删除核验成功。首次pg_isready观察到镜像初始化临时服务器，随后SQL探针exit2；启动日志包含临时服务停止/最终服务启动，后续SQL真实成功才启动矩阵。私有原日志与该探针事件保留，未改安全/网络配置或升级权限。唯一测试警告为既有Starlette/httpx弃用提示。

本切片只覆盖三处晚回执自清页提示；其余HTTP200损坏响应形式/入口提示限制仍保留。PG resources-history/历史全量/探索超时OPEN、Windows900/Edge240/Node150未验收。PROJECT PENDING/BLOCKED_PARTIAL、semantic UNKNOWN、owner PENDING、overall NOT_ACCEPTED、LIVE0、正式发布关闭；未改main、强推、部署、凭据或调用真实模型。
