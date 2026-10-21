# _ColdTrialGraph._base 内部纯校验合并

基线 `f18d6845db4a5ebdb5b71b745462b575cc47cfc0`。仅 exact 已发行 native
模式，将 `_typed_parameters` 内嵌的 family/Run/stage 纯关联校验归为一个固定段。
原 `_base` 前后两次完整 CGR.check 不动，段首及末端检查 dynamic/links；全部
末尾 typed_values 保留。独立公开断言、默认/未发行路径、SQL/外部/授权返回检查、
完整DB读集、事务/fence/stop及最终期限不变。不增加PASS缓存、通用skip参数、
重入标记、解冻/载荷容器或更多root迁移。新增私有collector只有 `_base` 一个调用者，
AST断言锁定此边界；它不是独立自校验公共入口。

## 必要实证与范围

真实隔离SQLite、原producer、已发行双family/双stage fixture，整个 `_base`：
**codec 15→2**，family11、Run3、typed_hold5、typed_values1；跨类别交错的
完整谓词与typed执行序列相同。两个完整扫描保留，独立入口仍自校验。
末段 frontier/撤权/settings/stop/model/max_tokens/links 变更，以及两次调用间
变更/撤权/typed drift/links均拒绝并关scope。默认/未发行不调用新纯入口。

fixture的trial=None/platform=None、live/context为空；覆盖完整owned lower `_base`
双族双stage，不冒充完整_prepare上游收集或两次commit的集成。其余分支静态AST
与基线一致。`_pin_stage` 提取纯段后内联AST等价，公共assertions不变；模式关闭
默认collector还原后与旧模块AST一致，原 `_base` 完全未改。

初批10P1F/16.79秒暴露末typed_values后stop变化只被scope退出拒绝，base未标INVALID。
新增末端便宜dynamic/links见证，**不是声称CGR本身检查stop内容**。原失败完整保存。
随后12P/16.99秒；最终再补max_tokens/links反例，冻结 **129P/227.74秒**，0失败/
0跳过；三文件SHA前后一致。Ruff三文件、mypy两源通过。无运行中修改源码或测试。
原强制close连接夹具异常既有边界未靠改产品清理迎合，本批不重复无关广测。

源码SHA256：cold_accounted `87b0c464866ac038140d615182d1dc552c83dd53cbf629a9bad2b4973bad017e`；
natural_spec_runtime `d0140af82c18f1b5181e6ffa929189d7dbd9ac49431a980710792c31d62628c7`；
测试 `5a26147d2bcd8079c1f820ecae579ff8a065e2744e6aa6b32074dcbcae4aba6e`。
原件gzip解压逐字节恢复，test-originals.json列原/压缩摘要；开发失败不隐藏。

## 原预算完整窗口

独审完成后正常开发分支推送，clean HEAD只读describe并核精确摘要。新目录/SQLite/
单次grant，只运行一次：6 Mock交换/8入口，prefix480/G0120/总600+清理10，
lease30/Run300/TTL1800/RPM1/reservation60不变。64MiB采样监测非硬配额，逻辑
work allowance非CPU/RSS界。0真实模型/费用/外网业务/新增权限；禁Cold2/W5，
不自动重试。必须证明原回执、第二commit及scope最终期限，首commit或单次wall
不足30不能替代全流程。当前局部15→2不是G0性能通过；实际窗口结果随后归档。

两位只读独审已封最终源码与129项证据ACK，见reviews；reviewer未执行产品、测试、DB或窗口。
