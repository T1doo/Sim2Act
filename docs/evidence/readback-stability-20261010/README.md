# 同次 Report history 的新鲜 scope 纯读回复用

精确产品/测试冻结 `47388f573746daa27f8d5790ca358eef91378ad5`；开发基线754。358文件、69产品；唯一产品差异`src/sim2act/report_presentations.py`，其余68相同，scope/propose/check原AST相同。原说明见[有限修复合同](../../F2/ReadbackStability20261010.md)。

## 作者必要回归

最终集合59节点，覆盖完整Report presentation API、新增双seal coherent forged check与跨请求Grant到期反例、14原晚回执真实HTTP场景、2当前损坏proof反馈场景、Report锁/冷恢复/PG业务角色、2独立CSV DAG实例与typed原子回滚及联合遗漏反例、ApplicationUse实际冷回读、原PG资源/graph锁顺序四例、完整Report真实UI与四个实际旧源码升级。原6秒idle、Future10、statement timeout与完整Report90秒预算不变。所有模型来源固定Mock，LIVE0。

最终计数以[作者精确摘要](author-summary.json)、两库原JUnit/log与command/run为准。SQLite54PASS/5PG-onlySKIP。PG59PASS/0SKIP，两库最终均无FAIL。每库18个实际UI场景结果、248具名检查；每库四份升级证明分别源afb Report锁、5a55/1b65 CSV DAG、前dev67实际CSV DAG实例。

## 独立限定复核

[独立正式报告](independent/FINAL_REVIEW.md)及[机器记录](independent/FINAL_REVIEW.json)：473 LIMITED_PASS，17 SQLite/API用例147检查；2自编真实HTTP场景、4文档页84检查。自己建立3definitions/6checks/2个不同归档输出，核每definition独立fresh scope、同definition纯比较无SQL、全DB零写及跨请求重新授权；写check仍2 fresh scope。反例含coherent seal假text、跨definition/result替换、source/principal/project/期限/PROJECT peer/VIEW locks/Run version及fence。有效accepted晚回执与实际accepted丢回复恢复精确key/body/原解释，无补POST，脚本形解释不执行。358 before/after及69产品冻结相同。独审不签PG、升级或native，不关闭历史超时；三次自编夹具失败保持原归属。[127文件白名单](independent/COPY_WHITELIST.json)。

## 有限剖析与CI

5427各一次原节点：SQLite same-checks PASS；PG same-checks+resources-history PASS，两历史超时未重现，**OPEN**。非空PG presentation GET的实际SQL6132→4010、Report.load15→10、scope2→1、FOR UPDATE1410→920；SQLite6133→4011。[完整统计](profile-summary.json)及`profiles/*.json.gz`保存原trace，解压SHA与摘要匹配。v1/v2与并发负载不同，墙钟仅诊断，CPU基线未记录，不做benchmark/根因/整体稳定性结论。原SQL observer会额外发两条SQL/应用query，未改。

[5427原CI](https://github.com/T1doo/Sim2Act/actions/runs/38023764691)：72 Ruff问题在三新测试文件，非72产品失败。754样式修复非import AST与全scope import/alias同义，产品与5427全同；完整严格Ruff/mypy通过。[新754精确CI](https://github.com/T1doo/Sim2Act/actions/runs/38024430136)也通过Ruff/mypy/Setup/smoke，但工程套件cancelled并记录26 failures、38 skipped、863 tests（未完成），Edge SKIP，Cleanup成功；失败详情NOT_RECORDED，不记整体PASS。[新CI实际结论](ci-754-verification.json)、[API步骤](ci-754-summary.json)、[原文摘录](ci-754-verification-excerpt.log)。原完整CI log私下保全，SHA在verification记录。

补充只读核验：GitHub job公开annotation已确认取消是超过15m0s上限；754只有此1个run/attempt1，没有另一个有效成功run。26个F标记全部先于取消，首个04:34:42、最后8个04:46:50，因此不能归为取消产生的失败；node/产品或夹具具体归因仍NOT_RECORDED。artifact API实际为空。正常开发push自动触发后续 [run38025760656](https://github.com/T1doo/Sim2Act/actions/runs/38025760656)，精确6eb42aae9ca6533ef608db9f0a834a9b2a9ccf3f、产品/测试仍473全部358文件；核验时in_progress，不记通过，未手工rerun。见[取消原因与后续run](ci-followup/ci-754-cancellation-confirmed.json)、[原26个F时间线](ci-followup/ci-754-pre-cancel-failure-marks.json)。下一轮首要取回并处理这26项native失败；本轮Linux限定通过不能替代。

[失败清单](FailureLedger.md)包括作者probe夹具FAIL、首次collection命令错误、独审3脚本错误、原72style及新native未完成、只读API限制。没有阈值变更或盲目重跑。

## 边界及证据原件

两历史读超时OPEN；新native工程26失败/取消OPEN；HTTP200其余损坏响应/入口提示与逐item map限制保留。Windows900/Edge240/Node150未验收，PROJECT PENDING/BLOCKED_PARTIAL、semantic UNKNOWN、owner PENDING、overall NOT_ACCEPTED、LIVE0、formal release disabled。

`author-export-manifest.json`是作者明确白名单及SHA256；raw日志/JUnit/真实DOM结果/加载hash/实际旧源码证明/未变source freeze，压缩profile可还原原始字节。独审按其COPY_WHITELIST单独核验归档。原件保留原字节，`.gitattributes`禁换行变换；不归档数据库、socket、pycache、私有环境或凭据。临时PG仅本轮自有network-none/Unix socket夹具，正常清理后对象不存在；最终实际证明见pg-cleanup。
