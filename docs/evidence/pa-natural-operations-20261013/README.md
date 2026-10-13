# 自然规范应用运行恢复与成果使用证据

源码冻结 `bea218d546cd1578e5bf0450c9be9ad9b1667f4e`，基线 `147a6da63ecb8fe15b9dea99d1ff8035f31122c3`。详见 [使用合同](../../F2/PANaturalSpecOperations20261013.md) 与 [最终验收](../../F2/PANaturalSpecOperationsAcceptance20261013.md)。

作者 [128 后端](author/frozen-backend-result.json) + [14 页面](author/frozen-ui-result.json) 为 **142 唯一 PASS / 0 FAIL / 0 ERROR / 0 SKIP**；[独审 39 PASS](independent/sol61-final/FINAL_REVIEW.md) 全部与作者重叠，不加总。[源码及分母桥](author/author-independent-final-bridge.json)逐个核对双方 436 文件 before/after；当前工作树与独审 snapshot 相符。精确 73 文件软件资格 pin `7f9c65c847842687a227f05a4e991901e68387b5343a771cc5c613318ce25543`，没有扩大既有旧锚与来源集合。

[作者汇总](author/final-summary.json)、[页面原回执索引](author/final-ui-summary.json)、[实际 SQLite 求值对照](author/final-callback-observations.json)可直接读取。14 页面为 393 检查、520 次实际 HTTP 静态资产加载、16 个实际 Blob 字节捕获；每个场景 20 项资产 SHA，SQLite/正常 Worker/进程内 HTTP/JSDOM 实际运行。原 key 恢复只 GET，每次成果下载重新 GET 授权并核精确作用域/版本/原字节。JSDOM 不替代原生浏览器与 OS 下载验收。

原 [失败分类](author/preserved-history-classification.json) 与全部 raw XML/log/DB/wire/SQL 均保留。初两轮 8 个夹具失败、r3 四个真正私有读取顺序失败、API 首轮 4 个夹具断言失败分别列明；原退出码 2 的两轮中断不计完整通过。[中断原因](author/interrupted-final-reason.json)及后续冻结重跑没有覆盖旧文件。独审初读 74 py 的枚举误差原件亦保留，按既有排除 config.py 的合同重算 73，最终 map/pin 精确通过。

完整包包括所有普通文件、目录及原符号链接目标，仅排可重建 cache / __pycache__，没有删除未知数据。直接副本逐字节复制；完整 SQLite 夹具、源码快照、SQL、model/runtime wire、页面请求/结果/下载在包内。

|完整包|原成员 / 文件 / 目录 / 链接|压缩 bytes|SHA256|
|---|---|---:|---|
|[author](author-complete.tar.gz)|2232 / 1995 / 188 / 49|13778169|`bf872e03ec65129cddde10816ae090cfde1d304f3d4fc0d350e1aebb6e8ee26f`|
|[independent](independent-complete.tar.gz)|2376 / 2304 / 62 / 10|10738950|`8c60b43b9cd3242dfabf7269b8494b1022349d1299068762384bc8dc5e4462ef`|

[作者逐项清单](author-full-manifest.json)、[独审逐项清单](independent-full-manifest.json)列出大小、SHA、类型和链接目标；[包内回读](archive-verification.json)重新读取全部 4608 个成员，字节/目录/链接目标均一致、mismatch 0。[归档脚本](package_evidence.py)记录有限缓存排除规则；原源路径作为证据保留，绝对链接目标不承诺在其他环境可直接使用。

[质量记录](author/quality.json)：全 src 与改动 Python 测试 Ruff PASS，改动 JS node --check PASS，git diff --check PASS；mypy5 为两个未改文件中的既有错误，不称全项目全绿。[保护分支与 owner WIP](author/pre-delivery-protected-and-owner.json)在归档前核对未变。

归档后的暂存检查曾对原 `.diff` 的三个空白上下文行报 whitespace；[原诊断](delivery-checks/whitespace-initial.json)保留。仅增加本证据目录 `*.diff -whitespace` 后 [重新检查 PASS](delivery-checks/whitespace-final.json)，没有重写原 diff、归档或生产源码。

真实模型请求/费用 0，semantic UNKNOWN、owner PENDING、publication false。完整 P-A/P-B、自然规范 P-B 独立成功任务提取、真实资料/语义/owner、PG、Windows、原生浏览器、完整旧库升级、远端 CI、部署等未闭合；不提升其资格。原 key pending 仅本页内存，不是新增跨版本冷 key journal。旧取消窗口永久 NOT_VERIFIED、未重做；[封存报告术语澄清](author/review-boundary-clarification.json)单独保留，39 项分母不变。实际模型/reasoning/service tier/Fast 无工具核验，NOT_VERIFIED；暂停/接续记录与旧会话读取限制一并保存。
