# 首次直接换已有授权 CSV：有限交付证据

基线 `6a8444fbae08cc14ebe0c25de673b9788429815d`，普通本地分支 `dev/production-trial-stages-20261018`。本片完成原spec1/Goal1直接换材料B；上一片仅同CSV换列，不能合并称换材料。

[使用步骤](../../F2/BlankSyntheticWorkspaceQuickstart.md) · [范围](../../F2/FirstMaterialRevision20261018.md) · [作者实绩与失败](raw/outcome.json) · [源码冻结](raw/final-source-hashes.json) · [完整作者原件](author-originals.tar.gz)。

实际安装包链：旧A amount10/20→30/v1；直接选择既有授权B amount100/250并固定共同amount列，原Goal1未变；独立CHECK350、分别确认新Release及原实例采纳，再明确新Run350/v2和同Run人工PENDING；冷页回读两Run各自Release/hash。没有Goal PUT、先行列修订或自动采纳。

[API3节点](raw/cache-api/command.json) PASS/pytest17.77秒，覆盖权限/hash拒绝零写、ACTION锁、proof缓存的写入/事务/撤权边界；[导入排序桥](raw/cache-api/import-order-bridge.json)明确仅后续交换两import，独立核对原hash及非import AST。

[最终安装实跑](raw/qualified-installed/installed-result.json)：新页21检查/84HTTP/242.336609秒，冷页9检查/56GET/107.751435秒；各页有1个可选protocol/contracts400原件。三个原Worker jobs SUCCEEDED/fence1、3CLAIMED、0模型Attempt/Reservation，冷页54个非heartbeat表逐字相等。原完整Goal、Grant、材料、draft和历史均保留。JSDOM加载实际HTTP安装页及原事件处理器，不是原生浏览器验证；依赖显式复用已有锁定目录，不是干净机器下载。

[新页原始HTTP与检查](raw/qualified-installed/new-page-proof.json) · [冷页](raw/qualified-installed/cold-page-proof.json) · [安装前后139包文件](raw/qualified-installed/wheel-files.json) · [源码143项前后相等](raw/qualified-installed/execution-after.json) · [仅执行后追加文档的桥](raw/post-execution-doc-bridge.json) · [静态检查](raw/cache-static-final.json)。

前置仅为**已有App授权B**：测量/derive/初始Release之前，fixture明确预置App对B的两项resource.read/data.aggregate_csv Grant；其他创建走原API。产品整个测量窗Grant表不变。普通导入没有给既有App追加材料授权的页面，本片未实现该入口或新增权限。

原始失败不改签：混合API180/240秒超时（旧长兼容节点NOT_COMPLETED）；独立锁断言误期待409而原保护400正确；安装fixture HTTPX keyword TypeError（首次fixture HTTP前，但工程初始化已写）；较早终态18秒失败及整页300秒超时（停机后新Run PAUSED，无业务Btyped）；Ruff import排序、只读剖析辅助字段及汇总观察器语法错误。完整日志/代码在作者archive，常用raw副本保留；[观察器更正说明](raw/observer-errors.txt)不冒充产品stderr。最终观察器整页900秒来自三个原300秒Run，产品预算/租约未变，实际新页242.34秒。重复原Release证明热点已按既有TX/epoch缓存复用，权限与源文件仍逐次重查；不认定旧超时唯一根因。

当前真实远端HEAD未知；沿用访问拒绝，本轮Git远端/auth重试0、push0。未改main、强推、部署、凭据或费用。Win/native、PG、真实语义及人工签收、远端CI均NOT_RUN；真实账户材料SOURCE_MISSING，旧满盘最终独审缺证NOT_RECOVERED。完整F2/R0状态不提升。

最终有限独审 **LIMITED_PASS_FIRST_MATERIAL_DIRECT_ON_ALREADY_AUTHORIZED_CSV**：[报告](final-independent-review.md) · [核验与源码hash](final-verification.json) · [完整独审原件](independent-originals.tar.gz) · [独审封存](independent-sealed-manifest.json)。独审不背书未执行的平台/全阶段、归档或commit；后两者由主写入者逐文件、archive及Git blob独立校验。

归档阶段第一次全量staged空白检查仅报[原始剖析输出](raw/fair-installed/readonly-release-2-profile.txt)第67行末尾空行，提交尚未执行；[原始Git检查输出](raw/packaging-diff-check-attempt1.txt)保留。该sealed原件不改字节。再次提交严格要求九份源码及除这一条原始输出外的全部文本空白门通过、仅这一条报错完全匹配、所有源/证据blob逐SHA相等；不是跳过产品质量门。
