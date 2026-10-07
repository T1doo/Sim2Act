# 本地组合候选核验 — 2026-10-07

源码冻结为 bfdbcc875bc7c14b4d480e95c07c61e3178f6b80，正常合并 core eb90d6bdb7711f63d7e7f20ca1317b5a9b7458b2 和 native 8d3c1a3e9693233679eb33a9d4286eb7f0b16a06。198 个 src/scripts/tests/.github 文件封印（source-file-sha256.json），最终复核零差异。产品 src 与 eb90、scripts 与 8d 逐字相同；workflow/pyproject 与原0126未改。整个组合全量套件 NOT_RUN。

当前独立 venv 的洁净子进程实际 import 当前工作树 src，依赖仅只读路径；python-provenance.json/node-provenance.json 保存路径。没有写共享包或处理旧editable pth。related.log/xml 最初56PASS7SKIP；dom.log/xml 记录错误 NODE_PATH 的2PASS6SKIP；以现有 jsdom 路径修正后 dom-configured.log/xml 为8PASS0SKIP。按唯一测试名称去重，最终63PASS1SKIP0FAIL（related-summary.json），唯一未测本地项目为PG应用角色，该项由 core 精确eb90的独立全量PG报告验证。collection.log 为1026 collected；不能将两线全量相加称作组合全量。

两线独立证据：core SQLite976PASS40SKIP/542.53秒、PG1012PASS4SKIP/1146.15秒，独审25真实HTTP、9DOM及实际Uvicorn/JSDOM28断言；native SQLite938PASS39SKIP/494.87秒，对比原928PASS39SKIP/466.15秒，旧967节点全部保留并新增10守卫。单进程七动作配对重复准备平均节省5.390秒，但全量慢28.72秒，不宣称整体加速，也不承诺900秒Windows预算。各详情以相应源精确SHA的独立目录及阶段日志为准。

当前组合Node语法和git diff --check通过。cleanup.json记录本线三个原测试session均exit0，owned活跃进程0；没有创建PG或发信号。不可归属的全局历史进程不声明已清零。原失败、缺依赖SKIP及修复前Core受阻记录保留在两线证据中。

有限来源绑定UI保持整体NOT_ACCEPTED、semanticUNKNOWN、ownerPENDING；候选技术编译不是源任务成功或签收。双PNG只是人工条件报告新捕获接线（1280 PASS/BLOCK、390 PASS/UNKNOWN），实际新Edge截图/textarea几何、新来源绑定区原生流程及Windows预算均NOT_RUN。没有LIVE、新授权/身份/Grant、外部发布、push或CI。既有远端7c02和历史CI不作为该组合验收。
