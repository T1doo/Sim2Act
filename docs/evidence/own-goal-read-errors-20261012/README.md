# 新Goal面板读取错误保护：P2有限修复

基线 `a747a7aafe7a537858f75bbfa129addd8696d0a6`，分支 `dev/own-goal-read-errors-20261012`，root唯一产品作者。初始工作区干净、Git远端精确同SHA、无活动测试，未找到适用AGENTS/技能文件。新面板成功读已有代次门，但失败只检查视图或编辑资格，旧首次GET晚失败可覆盖后续CURRENT摘要；编辑ABA、catch之间新读和save读回同类错误也缺门。

作者精确旧JS新增11个确定性页面场景：**4 PASS / 7 FAIL**，原代码、逐场景proof/stderr/exit及JUnit保留在`before/`和`before.xml`。是受控同Window JSDOM Promise排程、真实规范SHA256；不是HTTP、Worker、原生undo或旧取消的候选安装测试。七个失败独审按同一a747字节独立复现。

最小修复仅`owner-review.js`：inner.catch丢弃过时读取错误；initial/read/recover/save读回caller捕获原编辑/workspace fence及同步读取代次，outer.catch再次核资格。save读回失效不进入owner后续刷新；GET失败不能证明保存无效，不清原pending/state，未知仍只原key GET。当前有效错误继续显示；首次读仍可重叠，不靠busy串行化或停poll遮盖问题。

作者最终 **49 collected / 34 selected / 15 deselected，34 PASS、0 FAIL、0 SKIP**：新11受控页面、已有19 owner页面/调度、新Goal四个真实TestClient HTTP/JSDOM/正常NoModel Worker页面；见`after.log/xml`。独审分组：旧11为4P7F；当前11全部PASS；正常四页PASS；附加当前GET409原key保留1例PASS，分别记，不把重叠组选集当唯一总数。独审[报告](independent/FINAL_REVIEW.md)SHA256 `8fdb91c5d7702fe3c711bddc4c3966f1db4efd275bcbe77e598b91481a264805`。

379个Git可交付src/tests，5 ignored egg-info排除；前后逐文件一致，map `8ec8228f078bf5137f0f8f3ffe57579458ccc10467ef54c3d3cfe249f5a247f2`。首次freeze沿用了旧helper的base/branch元数据，留存`freeze-initial-metadata-mismatch.json`后纠正；源码map未变。独审8次前后检查同map。SQL无损gzip，原SHA与gzip SHA见`sql-archives.json`；独审原120产物manifest按解压字节保持一致。旧a747全部证据不改。

原a747分母仍是作者核心34、独审同选34+独立9=43、另次原家族152 selected/147P5S，本轮没有把这些历史数字加总或称全量重跑。新增测试ruff与JS语法检查PASS；生产Python未改，全仓ruff/mypy本轮未重跑，既有10/5错误基线不提升。

本修仅晚错误摘要/原key保护，后端保存、运行、人工签收契约不变。选择SIMULATED、语义UNKNOWN、正式发布false、模型请求0。真实人工语义、PG/Windows/native、旧库升级、完整P-A/P-B、真实模型与部署NOT_RUN。CI Forbidden保持停止，原取消精确竞态永久NOT_VERIFIED。本小修后立即接续原F2-T08显式兼容预检/批准及实际旧SQLite到当前冷执行闭环，不能把此页测试当升级已验。
