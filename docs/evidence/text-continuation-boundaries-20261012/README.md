# 有限续接历史范围与完整性修复证据

起点 `b244a24b607688af169cc08ac13c90f84b4a275a`，同原保存环境，分支 `dev/text-compatible-continuation-20261012`。root唯一仓库writer，独审只读。具体范围见[合同](../../F2/TextContinuationBoundaryReview20261012.md)，旧证据目录原字节保留。

|实际原版轮次|结果|解释|
|---|---|---|
|red，38节点|2PASS/36FAIL/0SKIP/ERROR|12错scope私有cell、4缺typed完整验算、16异常残留验算断言；另外4 VERIFIED op是原夹具唯一约束错误，不能当产品复现|
|red-operation-corrected|4FAIL/34deselected|修正夹具，不复制冲突operation；四项真实产品失败，含迟到VERIFIED op commit201|
|red-missing-typed-chain|实际脚本exit0，两锚均201→201→409|exit0表示成功复现原漏洞；不是产品通过。两旧库成功历史全部原证明保持，仅删typed/data_version0|
|old empty terminal controls|4PASS/38deselected|实际旧API/Worker FAILED-only及正常queued cancel后的CANCELLED-only无typed控制|

`red-before-source.json`冻结原38测试的源码；`red-test-original.py`保留原测试字节，操作夹具修正后原日志/XML/失败不覆写。错scope证明在`red-proofs/`含实际SQL、校准、外域private cell求值及全库零写；观察器不修改cell值。原预检201会写批准，JSON的database_unchanged=false如实保存，不说它原先零写。缺typed的完整原链在`red-missing-typed-chain.{py,log,json}`。全部均合成持久库故障，不是真实攻击或HTTP响应泄露。

`final-freeze.json`为410文件map `973918a69af80c30b19436f09519e25f09dbf581892cdf24a3db7b2d9e49ef04`，目标 `7bc662bb1483693e96edf916d2177ad51f246e0cbde7a50d943675d8c9ec852d`；pyproject49f不变。两新旧库生成命令/exit见`*-empty-terminals-build.*`，实际数据库SHA和精确旧软件map在 `tests/fixtures/text-legacy` 对应info/archive/create文件；生产时钟、TTL、权限不变。所有模型请求0。

作者原249+新42的291个唯一节点相关回归实际 **285PASS/0FAIL/0ERROR/6SKIP**，原session18009及实际子进程exit0，pytest670.42秒；完整命令、原log/XML和前后410文件零差异分别在`regression-command.json`、`regression-final.log/xml`与`regression-exit.json`。六项均因缺显式隔离PG而跳过：实际before/after commit崩溃恢复、pause/cancel计算无长锁、最小应用角色enqueue和内部生命周期应用角色，不提升为PASS。

独审本轮[完整报告](independent/FINAL_REVIEW.md)实际 **112唯一节点/112PASS/0FAIL/0ERROR/0SKIP**：100后端、4实际HTTP/JSDOM/NoModel Worker、8独立SQLite负例，三个进程均exit0；源码410与pyproject前后精确对应同一冻结。独立deny型单元屏障校准后，跨scope错链及错误AppRun owner均保护单元求值0；孤立typed和迟到VERIFIED-op拒绝且全库零写。原四页面240资产hash/60断言/4冷正常Worker另有原JSON，不把断言或资产数量当测试数。112与作者291不合并，不复用旧80/12签当前软件。

`review-copy-manifest.json`保存96独审产物及manifest共97份复制的原SHA，`package-verification.json`逐原字节验证复制、410冻结及pyproject；SQL大文件由`sql-compression-manifest.json`无损gzip存储，解压后SHA与原字节相同。原b244证据全部Git blob逐文件比对零变化。独审`history-manifest.json`核903份既存历史原字节，明确排除当时仍在追加的本轮regression-final.log；不把活动日志视为不可变历史。

改动三文件Ruff PASS；`ruff check src tests`10和`mypy src/sim2act`5仍为原基线，原输出/exit保留。新测试首轮2个导入Ruff错误已修，generic Python冻结时ModuleNotFoundError未产生冻结，改用原仓库venv解释器；这些错误原记录保留，未安装软件或改权限。

PG、Windows/native、真实模型、真实用户升级、人工语义、完整P-A/P-B/正式发布和远端CI仍NOT_RUN。原取消精确候选安装竞态永久NOT_VERIFIED，Forbidden CI保持停止；未调用这些路径、未部署、未改main/core或强推。
