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

## 本次完整窗口：第二commit已进入，但未完成

执行候选 `bdcdce6248fb97b99f0c957aff85682a1cabfbee`，source/dependency摘要
`d74b3b4c73c3f18839b0b5e18b3ead5709d2e713d21d8d7fc11cfddca132a8a8`；
profile `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`。
manifest相对前窗仅本片两源/一测试变化；launcher/guard/observer/依赖/预算均未改。
绝对解释器与脚本身份实录，新目录/SQLite/grant消费一次；没有自动重试。

| 实测项 | 结果 |
| --- | --- |
| parent/child分类、退出码 | **UNKNOWN / 2** |
| Mock交换 / 入口 / Source delegate | **6 / 8 / 2** |
| 真正进入G0 / 资格 | 是 / **OWNED**，native:issuance |
| work wall / G0 wall | **342.2903028850051 / 30.890151267994952秒** |
| 第一次原Cold commit | returned=true，11项原deadline；无返回时间戳 |
| 第二次原Cold commit | **已进入**，在_recheck拒绝，returned=false |
| 原scope返回 / 最终期限 | false / **NOT_PROVEN** |
| 直接错误 | VERSION_CONFLICT: Run identity, cancellation, version or finite lease changed |
| child / parent清理 | THREADS_CLIENTS_CONNECTIONS_CLOSED / OWNED_GROUP_EMPTY |
| 独立进程核实 | 父60685、子60709不存在，60709 PGID为空 |
| finalization_errors | [] |

冻结实际栈 `advance_model:3752 → observed:46 → commit:3001 → _recheck:2896
→ _require_run_context_row:869`。第二prefix已返回，与前窗停于prefix的Store.guard
不同。该原Run谓词涵盖身份、项目/Runtime/资源/status、取消、version/fence、
created_at及最严lease/Run/contract期限；没有拒绝现场的actual/at单独快照，不能
仅据通用消息认定唯一为lease，也不能以G0 wall−30计算精确超期。

根据冻结直线控制流可**推断**原 `_cold_receipts` 的pin_binding→_receipts→
record_receipts等整段以及attempt回读、parse/usage/schema、receipt_for、
settlement-parsed已返回；第二commit前置prefix亦已返回。没有独立receipt阶段、
root/m采样，故这不是新增运行观测或硬编码m。没有证明第二commit后续、原scope
返回或最终期限，整个G0/PB仍未通过。Cold RUNNING/RECEIVED是既有StopBoundary保现场机制的说明，
本次未单独开库观测该行状态，不据此报生产漏收尾。

五阶段 **5348 codec / 成功返回3720455764字节 / inclusive线程CPU14.564701304秒**。
_prepare为3587，前窗3628，实际少41；其他阶段分别664/95/993/9。阶段wall分别
15.003480207、2.578736076、0.381821738、3.962464959、0.034409378秒。
局部15→2是lower_base完整fixture调用计数，不是整个输入每次都同样减少13，
更不是G0通过。五阶段不含所有G0调用/CPU；成功返回字节非实际SHA调用观测，
仪器有非零开销。前后窗口不同拒绝位置，不能宣称总wall受控改善或省下全部codec CPU。

逻辑resident/live458430612、peak478097556、work188404034025305936651508，
scope后active=false/live=resident=0；非进程RSS/CPU界。磁盘6795次采样，peak
logical2257646、allocated2273280字节；均值0.05038094610847803秒，最大
0.13611715400475077秒，配置0.1并非固定计划周期或原生硬配额。
source before/after/parent cleanup摘要相同，收据evidence哈希全部实核；旧17项原件
不变。当前全部原件见window归档/manifest，DB仅保全本地及摘要。0真实模型、费用、
外网业务或新增权限；W5为原静态stop口径，不冒充观测计数；未自动重跑。

最小剩余条件是原第二commit `_recheck`、后续全部期限和原scope最终检查完成。
要唯一定位这次Run谓词失败，缺的是拒绝点at及各原比较输入/期限的只读见证；早先
run_context快照不能代替此点。当前结果不支持扩大租约/删guard或原样再跑赌时间。

两份最终窗口只读独审均接受结果、清理及README口径，见reviews。reviewer未执行测试、产品、DB或新窗口；本轮源码自冻结后未改。
