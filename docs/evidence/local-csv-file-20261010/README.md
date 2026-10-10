# 本地 CSV 入口与既有持久运行链：限定验证

源冻结 `fdc91282b2107164ba33624246be6f50e007cd13`，基线 dev `66709612d5acd2e4b0dc41f75ef5c9f769508b0c`。[352文件清单](source-freeze.json)、[产品字节证明](product-byte-proof.json)：68个产品文件只有 `web/app.js`、`web/index.html` 变化；Python API、Schema、注册表、授权与 worker 字节不变。没有新增执行器、API、表或模型调用。

用户现在可以选择单个无BOM UTF-8 CSV（1–32768字节），核对文件名称、大小、目标项目与内容，显式保存后继续现有模板/内部版本/实例流程。原 CRLF 由独立缓冲保留；手工编辑退回文本模式。取消、换文件、编辑、项目ABA、身份切换和迟到Save/列表错误均受代次守卫。资源POST无幂等键：双击仅一次，未知/瞬态4xx/无效ID保持UNKNOWN，不自动重发，手动只读核对。[合同](../../F2/LocalCSVFileEntry.md)、[使用说明](../../FirstUse.md)。

## 作者真实验证

| 数据库 | 最终必要集合 | pytest时间 | 新入口 | 已有页面与实际旧源码 |
| --- | --- | --- | --- | --- |
| SQLite | 27收集，26PASS/1SKIP/0FAIL/0ERROR | 80.175秒 | 8用例、9实际HTTP/JSDOM页、67检查 | ApplicationUse两页30检查、Report晚回执same-checks一页10检查；3实际旧源码升级 |
| PostgreSQL17.9 | 27收集，27PASS/0SKIP/0FAIL/0ERROR | 127.143秒 | 8用例、9实际HTTP/JSDOM页、67检查 | 同上；实际应用CRUD角色用例通过 |

每库共12实际HTTP页面107检查，另含不计为页面检查的独立 Python CSV/Decimal 算术、原文件bytes/hash和数据库持久结果核查。新页面逐一核验真实HTTP返回的HTML及所有加载产品JS散列；以真实文件的UTF-8 CRLF和中文名从空新项目进入，未预置该项目材料、草案、Release、实例或结果。正常 worker 的 provider 禁止调用；两个列产生独立 Run/结果v1 `20.25`、v2 `9`；冷页面重连/打开零POST。已有撤权/过期、来源改变、实例谱系与请求指纹拒绝均保留。实际旧源码为 `5a5543c902fbb78dd91c28c98386af51fb24dd67`、`1b65e94ebd81c1e31091b3078b8223328b726294` 的CSV及 `afb2f1f3813fc3a4744923f31bbcb4666b88cccd` 的Report；保留不可变历史，旧证明不能冒充当前源，要求新精确锚。

唯一SKIP为SQLite不能执行真实PG应用角色。开发Node/jsdom已存在，未安装/改锁依赖。JS语法、new-test Ruff、git diff检查通过；Python产品字节不变，未重复mypy或全量回归。[命令与结果](summary.json)、[SQLite日志](sqlite.log)、[PG日志](pg.log)、JUnit和各页面/升级原件在本目录。[精确复制回执](copy-receipt.json)不含数据库、socket、环境或凭据。

## 原图历史超时诊断：仍OPEN

在未改产品的基线667上，仅一次原精确节点 `tests/test_resources_project_lock.py::test_pg_resources_graph_share_project_first_lock[resources-history]`：[原命令](graph-history-command.json)、[JUnit](graph-history.xml)、[原锁记录](graph-history-lock.json)。原测试SHA256 `0fc8b99bd872a73739a992148327be6c208c6cb58f8e0e4153c95a4a9064f616` 不变，保留10秒Future和原SQL observer。1PASS、pytest4.180秒/进程5.481秒；资源与graph均实际HTTP200，395条graph锁查询跨度1.149秒，项目先锁、无SQL错误/旧锁环、源未变。

历史冻结42b7a992的23.054秒Future失败仍OPEN，原记录395条graph锁跨17.59秒、无状态完成证明、无40P01。此次未复现不能解释历史慢读或关闭OPEN；来源重构和每条SQL额外两次observer查询只是线索，不声称根因/稳定提速/实际生产耗时。已修40P01是另一条证据链。未加超时、删除锁、删授权或降低来源验证。[原记录](../linux-convergence-42b7a99-20261008/pg-first.xml)。

作者自有PG容器 `5929c6775b2d8d1934e27600cf55d9773f55b76fb5ab0c10bb1ae7e9d9223cd8`，owner标签resource-file-20261010、network none、无hostTCP。最终正常初始化后探测健康；诊断和正式测试前后schema/role/public均0|0|0。普通stop/rm-v完成，容器及自有卷不存在，[清理回执](pg-cleanup.json)。

## 独审、失败与验收边界

[独立最终报告](independent/FINAL_REVIEW.md)对精确fdc91282为 **LIMITED_PASS**：独立SQLite8新场景9实际HTTP/JSDOM页201检查（含资产hash），另一份含CSV引号逗号/中文/负小数的文件经真实全部操作产生1.75与4、独立Run/版本1/2，CRLF bytes/hash与冷页零POST一致。原667实际HTTP HTML/app.js负对照1页17检查按预期失败“存在文件入口”的正断言，证明入口敏感性；其余资产/后台为当前源，此对照不是旧数据库升级。352文件/68产品桥前后一致。独审自己的JSON400和持有网络却等待全局idle的失败已按全部三轮归档，修私有harness后重验失败场景，并非一次整批全绿。114白名单文件逐字节复制，含SQL写入审计、源/网络/checks/DB投影及原负对照stack；[复制清单](independent/COPY_WHITELIST.json)。独审不代签作者PG、旧数据库、原生、有效形状伪造ID完整来源证明或页面重载后的持久UNKNOWN。UNKNOWN仅页内Map，原POST无幂等键；重载前/后应手动核对材料列表，不能称持久exactly-once。[失败账本](FailureLedger.md)保留全部初始失败和修复原因；私有完整原件仍在 `/tmp/sim2act-resource-file-20261010`，没有删除失败日志。普通候选/开发推送与远端核验按 [集成记录](Integration.md) 阅读。

这只是原 F1-T03/F2-T06/T08 的有限材料入口增量，合成工程证据不是真实用户材料、模型自主生成、完整P-A/P-B或整体验收。实例仍固定材料，新列不是新材料；材料Save与草案授权仍为两个独立显式操作。LIVE=0，PROJECT PENDING/BLOCKED_PARTIAL、语义UNKNOWN、owner PENDING、整体NOT_ACCEPTED、正式发布关闭。PG历史超时OPEN；HTTP200其余坏响应形式/入口及逐item历史map限制保留；Windows900/Edge240/Node150未验收。无main修改、强推、部署、凭据/安全/网络配置变化或真实模型调用。
