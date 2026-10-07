# Windows Server 条件报告原生证据（精确 7c02）

父线程后续授权精确 `7c02c66efc09ad8b23a5e92e2ee61a25e21dfc59` 普通 fast-forward 到既有 `dev/f1-foundation` 并运行一次既有 Windows CI。实际唯一 push CI [37597713044](https://github.com/T1doo/Sim2Act/actions/runs/37597713044)、attempt 1、job 112714276667、source exact 7c02，2026-10-07 09:16:20 UTC SUCCESS。未 dispatch/rerun，core `fb239a5` 不在其 ancestry 且未推送。本目录是随后本地文档记录，不改变被测源码。

工程 967 collected：954 PASS、13 SKIP、0 FAIL/ERROR，661.87 秒，3 warnings。Ruff、mypy36、原最小 application-role smoke、Report、Cleanup 成功。套件含环境支持的 PG 和显式 SQLite/Mock/JS，不能把954全部称PG；原-q日志未逐项输出 skip reason，本目录不推定13项原因。

原 legacy rollup59、history39、agent33、registered generation29、protocol26、组合应用使用16及新增 conditional22 全 PASS，各集合有嵌套，不相加成独立测试数。新增 phase 10.235 秒，真实2500ms poll保留输入、事实编辑清旧证据、错误报告FAIL、未知事实UNKNOWN、版本变更及恢复、持有200响应的A→B→A、冷文档无POST/旧PASS、实际撤一条已有读Grant、全表指纹及零新增Run/Grant/Principal等均通过。结构PASS仍可业务BLOCK；semantic UNKNOWN、owner PENDING、发布关闭。

新增阶段前后各5个实际 renderer 均 AppContainer/restricted token、integrity RID0、security args verified，无禁sandbox参数；主browser进程的高完整性并不冒称renderer保护。完整来源resource已精确恢复，终态只有既有Grant撤权改变grants表fingerprint，其他所有表和Grant IDs/principals不变。新阶段0真实模型，旧protocol4MOCK/0network，零outside origin/browser review请求。未激活准备器或LIVE；CI不提供真实业务签收。

原 job15分钟、browser step4分钟、Node helper150秒及既有保护/权限/runner/locks/output slots未改。实际 job09:01:23→09:16:19共896秒，余量4秒；Edge step09:13:42→09:16:12共150秒，包含setup与输出，不能把它称独立Node耗时。Node成功在原 `subprocess.run(timeout=150)` 内，原日志没有单独计时。此次终态成功，未来该整体预算余量很小。

9个原stdout白名单文件、712 chunks，原声明尺寸、SHA256与2MB上限全部校验，恢复3 JSON/6 PNG，无新增上传目的地。主审实际查看全部六张PNG：应用使用冷页、registered CSV source→candidate→new cold结果、原protocol source/extract/cold桌面及390px窄屏内容可见，原protocol两种宽度overflow0。新增conditional报告阶段没有截图；原应用截图只有该区域初始资料选择器，不签已打开报告态像素。历史图片槽由组合应用使用截图替代，scope见 `pixel-review.json`。producer的NOT_REVIEWED等原字段保持原样，另记后续实际像素查看。

原CLI日志下载在签名Azure跳转403，随后正式连接GitHub job logs读取成功，未改变代理/身份/安全策略。`job.log.gz` 为connector文本（CRLF规范化LF、保留BOM），`emission-receipt.json` 保存该输入SHA和逐文件原始bytes/SHA，实际输出字节不重编码。API终态、独立审查、decoder与验证汇总均随目录保存。Cleanup step成功；原Windows日志未独立给出残schema/role数量，不虚构零计数。

本证据提升精确候选的Windows Server protected Edge工程通过；Win11、条件报告态像素、完整P-B、F1/AT02、用户与目标语义签收仍未完成。源码冻结213fe90、本地回归40PASS1SKIP及独立审查见前一目录 `../conditional-native-candidate-20261007/`；Run/check/DAG core仍在独立工作树，其PG证据不混入此CI。
