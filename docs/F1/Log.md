# F1 Log（追加事实）

## F1-L001 / 2026-10-05 / Codex / F1-T01、T07、T08

基线：V5；代码 6f688e4dd80b5c81d41aecde90e360d3629f9c21；Linux，Python 3.12.14。
实际：核对 origin=https://github.com/T1doo/Sim2Act.git；原工作分支 work，工作区干净，远端仅 main。建立 dev/f1-foundation，保留原 main。读取适用指令，未发现 AGENTS.md 或 .agents/skills/SKILL.md。
两份 Library 原文完整保存并校验行数/字节；保留 sources/V5，规范最小修订可追溯。
测试：文档完整性 PASS；产品 AT-01—28 NOT_RUN。
决策：先落实 F1 工程能力，不执行付费调用；LIVE、Windows 验收 BLOCKED。C0 三项规则从 F1 并行待核实，最终门仍在 R0 后。
提交：见承载本条记录的 git commit；准确引用在下一条记录追加。

## F1-L002 / 2026-10-05（实际收尾 02:55:33 UTC）/ Codex / F1-T01—08

基线：文档提交 4893cd2d2e0dcd6df405b386865a7afe9b2abc4a；Linux/Python 3.12.14/PostgreSQL 17.9 临时容器；无真实 .env/token。沿用同一目录与分支；中途按协调请求暂停，收到解除后继续，未重复初始化仓库。

实际变更：FastAPI + 独立worker + SQLAlchemy/psycopg账本、七类Schema草案、严格解析、三注册工具、本地身份/项目/资源授权、持久幂等接受、租约/fencing/心跳、Operation事务回执、暂停取消、书生固定适配与共享配额、MOCK/故障注入、三个工作区、六个PowerShell接口和Python启停器、锁文件、合成fixtures/oracle。

决定：包内可信静态前端无需Node构建；SQLite只作夹具，应用要求PostgreSQL；用独立迁移角色建表、运行角色只读写，实际DDL拒绝已测。F1结果显示PARTIAL并保留goal_acceptance=NOT_RUN，不把工具完成冒充目标/应用验收。完整清单编译、发布身份交集、文件落位及人工未知请求核对未实现。范围未缩减，P-A/P-B/增量验证保留后续门。

测试：ruff check src scripts tests PASS；mypy src PASS；node --check app.js PASS；SQLite pytest 34 PASS/1 SKIPPED（仅实际PostgreSQL进程检查）；PostgreSQL pytest 35 PASS；每次有1条Starlette/httpx测试客户端弃用警告，未隐藏。JUnit、源码hash、输入hash、Run/Operation引用与截图见 ../evidence/F1-TestReport.md。

实际端到端：API/worker独立PID，数据库持久接受202；worker停止时排队，HTTP客户端断开后重启处理，PARTIAL与回执可回读，再停/重启后结果保持；中文空格目录、占用端口拒绝。浏览器实际连接、建项目、存CSV、提交、查看、刷新重登回读、三个工作区切换、材料查看、撤权隐藏与清空显示。实际重启后的本地文本成果写入及指纹回读PASS。最后跨工具调用Stop后Status为OFFLINE，保留数据库/日志。

失败与修复（不抹记录）：首轮pytest 12 PASS/9 ERROR，httpx.Headers.update不接受Authorization关键字；改为字典后21、30项检查通过。新增进程用例曾FAIL：容器僵尸进程导致psutil.wait超时；改为识别已退出状态，增加独立回归。跨命令Stop发现cwd跨沙箱AccessDenied被误当退出，导致错误“已停止”；修复为精确命令行+创建时间验证，拒绝不明权限并保留PID记录；已恢复当次测试PID记录并停止自身测试进程，新增2项回归，最终35 PASS。APT下载PG包失败，改用仅测试的临时PG容器；Chrome下载受网络限制，使用已有Chromium，容器浏览器需no-sandbox/CDP；仅访问合成localhost，无真实数据/账号。PowerShell数组参数调用经静态检查修正为显式-Arguments，未声称原生执行。

秘密检查：未读取隐藏凭据、未创建真实.env、未调用真实书生或收费API；模板只有占位值，测试令牌显式synthetic；源码/规范秘密模式检查PASS，提交不含虚拟环境、数据、PID/日志或迁移.env。该检查不是形式化无秘密证明。

阻塞：LIVE安全注入与预算尚未确认；Windows原生/PowerShell未取得；真实任务授权及C0三项规则待核实。仅暂停相关验收，不阻塞工程底座。

提交：本条由工程增量commit承载；其准确SHA在F1-L003追记。F1整体IN_PROGRESS，未进入F2发布门。

提交前权限复核补充：聚合工具额外授权不能绕过材料resource.read撤回；历史成果/模型后续请求/最终输出重新检查已生成成果授权。新增两项回归，最终PG35PASS、SQLite34PASS/1SKIPPED。源码hash按最终文件重新生成。

## F1-L003 / 2026-10-05T03:00:27.559576+00:00 / Codex / 工程增量提交证据

工程源码提交：[f496f225ae109e4415cff3a1fa8117451a82fda3](https://github.com/T1doo/Sim2Act/commit/f496f225ae109e4415cff3a1fa8117451a82fda3)，dev/f1-foundation，已push。最终实际结果：PostgreSQL 35PASS/1条弃用警告（6.88秒）；SQLite 34PASS/1SKIPPED/1条警告（0.76秒）；ruff/mypy/JS检查PASS。源码指纹与提交中的文件一致；此追记只改文档，不改已测代码。
API/worker在独立跨执行命令Stop后已停止，health=OFFLINE；临时PostgreSQL测试容器保留供后续工程核查，不是公开部署或Windows验收。浏览器已关闭。
下一步按F1 Plan补齐契约/恢复/探针工程接口；LIVE、Windows、真实材料及C0规则仍BLOCKED或待核实。F1未签收，未合并main，未启动F2发布。
