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

## F1-L004 / 2026-10-05T03:28:49.450701+00:00 / Codex / F1-2 独立工程增量

基线：已推送 5c930bc3e668294f1f55f3fc60a5d13a485c4c20，沿用 dev/f1-foundation、既有依赖和 PostgreSQL 测试容器。检查未提交 diff 与先前产出一致，保留继续；协调恢复时曾误回复早期只读检查，收到当前目标纠正后恢复本增量，没有覆盖改动。

实际：闭合嵌套 ActionSpec/AppManifest、JSON Schema 类型/边界、注册依赖/效果/权限申请和有限前置条件、纯候选校验 API；离线 probe 不读取配置、固定 MockTransport；严格响应与失败用量保留、修复计数原子保存；未知请求指纹绑定、人工导入暂停/另行继续或明确结束、版本/主体/撤权/取消意图/未知效果保护；现有成果画布核对入口与布局修复。完整编译/发布未实施，原始 V5 来源未改。

实际测试：SQLite 63 PASS/1 SKIPPED/1 warning（2.90s），PostgreSQL 64 PASS/1 warning（9.88s）；ruff、mypy 11 模块、JS语法、Schema生成、离线probe、git diff --check PASS。新增29项覆盖契约、核对、独立心跳/并发、失败用量和离线隔离；Starlette/httpx警告保留。新增测试局部 import 顺序曾被ruff拒绝，修复后通过；之前契约类型标注在mypy提示后补set[str]。

实际浏览器：合成失联请求 close_unknown -> CANCELLED；record_response -> PAUSED 且数据库0个工具效果；用户明确继续后独立worker --once -> PARTIAL、回执可读。原用量仍unknown/null。长指纹select早期列溢出，短标签/title+弹性列修复；最终宽1280、scrollWidth1265，错误列表为空，截图已目视检查。截图相对路径首次失败，绝对路径成功。Run/Attempt/Operation与USER_SUPPLIED审计见 ../evidence/F1-2-browser-audit.json。

收尾：自身 API/worker 停止，另次Status为OFFLINE，浏览器关闭；临时数据库保留，不是公开部署。未读取真实密钥、未真实调用书生；合成证据明确MOCK/FAULT_INJECTION，模型列表非账号实测。源码/测试/Schema指纹与JUnit见 ../evidence/F1-2-TestReport.md。

剩余：LIVE安全注入/批准预算、Windows原生仍BLOCKED；GoalSpec/Run完整冻结、Manifest编译/节点类型连通、文件跨事务恢复、通用未知工具效果核对待后续。F1整体IN_PROGRESS，未进入F2，AT-09—28保持NOT_RUN。代码提交SHA在下一条追加。

## F1-L005 / 2026-10-05T03:29:36.214017+00:00 / Codex / 第二增量提交证据

工程提交：[637cca93aeb7022cb1062c73bb43ff40cab9c29d](https://github.com/T1doo/Sim2Act/commit/637cca93aeb7022cb1062c73bb43ff40cab9c29d)，dev/f1-foundation。PostgreSQL 64 PASS/1 warning，SQLite 63 PASS/1 SKIPPED/1 warning；静态检查、合成离线探针及浏览器人工核对双路径通过，API/worker 收尾 OFFLINE。完整数据和源码指纹见 F1-2-TestReport。本次追记只更新文档；该工程提交及追记将一起正常 push，随后核对远端 SHA。LIVE/Windows 保持 BLOCKED，F1未签收，未进入F2。

## F1-L006 / 2026-10-05T03:48:58.147384+00:00 / Codex / F1-3 独立缺口收尾

基线2c3761e，沿用dev/f1-foundation。先对照V5产品§5/8、计划F1-T01/04/05/07及F2-T01—09，划分见Scope.md：本轮不执行/发布应用。实现最小清单引用/连接/依赖锁/静态权限/保守预算预检；新Run接受事务冻结Goal/输入哈希/运行身份/模式/模型/预算，旧版或变更快照拒绝执行；Operation意图与本地效果关联同事务，可信回读恢复、已知不符、未知等待、取消/恢复保护与已有效果列表。没有实现真实外部工具、文件执行或F2编译运行器。

新增26项独立断言，含只读审查建议的跨项目拒绝后五类表计数不变、实际revoke所有权/版本/撤权效果，位置tests/test_f1_closure.py前两用例。SQLite89PASS/1SKIP/1warning（4.93s），PG90PASS/1warning（15.01s），ruff/mypy12模块/Schema/离线probe/diff检查PASS。真实PG独立schema的快照/预检/未知回执核对/取消意图/不重复效果引用保存在F1-3-ledger-audit.json，随后schema清理；未启动开发服务或改变页面，未新做AT-18应用并发。

mypy预检变量报7项错误，明确类型及变量名后修复；新测试import排序修复。先88项回归通过，补2个重要断言及静态资源权限覆盖后最终90项，保留警告。历史哈希清单中的5个egg-info生成物独立移出，保留原哈希，最新源码清单排除构建生成物；V5原始字节未改。

迁移为显式migrate新增三表（run_contracts/operation_intents/local_effects），不由API/worker建表、不删除旧数据；旧Run不伪造快照。Linux工程闭环已完成本轮列出的F1独立缺口，停止扩展；LIVE安全配置/批准预算、Windows原生、真实材料/赛方条件仍待核实，实际账号能力报告尚未验收。F1未通过，F2保持PLANNED。具体步骤见Scope.md，工程提交SHA下一条追记。

提交前补充：恢复既有工具反馈改为原位置更新/按原助手步骤插入，保留对话顺序；已有完整最终响应时继续不增加Attempt，独立断言通过。最终仍90项PG/89项SQLite加1skip，最新时长已更新，源码指纹按最终文件生成。

## F1-L007 / 2026-10-05T03:51:00.276565+00:00 / Codex / F1-3提交证据

工程源码提交：[a38b98d4d39712afcbf256fe7b697ce8ed16db8f](https://github.com/T1doo/Sim2Act/commit/a38b98d4d39712afcbf256fe7b697ce8ed16db8f)，dev/f1-foundation。最终PG90PASS/1warning（15.01s）、SQLite89PASS/1SKIP/1warning（4.93s），ruff/mypy12模块/Schema/离线probe/hash/diff检查通过。新增三表需显式迁移，旧快照不补造，完整应用编译运行和发布属F2未实施。此追记只改文档，随工程提交正常push后核对远端SHA；F1仍IN_PROGRESS，LIVE/Windows等实际验收保持BLOCKED，停止扩展底座。

## F1-L008 / 2026-10-05T03:58:07.060630+00:00 / Codex / 有界token名称兼容修正

基线f118b33，dev/f1-foundation。Settings增加INTERN_API_TOKEN别名，非空SIM2ACT_INTERN_TOKEN优先，专用为空/未设置才读取通用别名，两者缺失/空则无token；只改名称支持，不改变LIVE开关。Common.ps1显式配置载入只额外允许准确别名，.env.example两个字段都空，README记录用户私有输入与优先级。

测试：tests/test_config_token_alias.py 7PASS（0.02s），ruff/mypy12模块/diff检查PASS；1条已有Starlette/httpx弃用警告保留。配置测试完整替换environ映射，6种合成值/优先级/缺失组合，不读取真实环境凭据并断言无输出、MOCK默认不变；PowerShell允许名及模板作静态检查，不宣称原生执行。JUnit见../evidence/F1-token-alias-tests.xml。没有读取/写入真实.env、没有设置真实token、没有模型或数据库调用、没有启用LIVE。提交引用见承载本条记录的Git提交，本轮只做该小修正后结束。

## F1-L009 / 2026-10-05T04:32:56.377335+00:00 / Codex / 返回模型标识兼容修复

基线04335528。独立真实接入验证向父任务报告canonical模型发现intern-s2，但成功返回model=Intern-S2；旧Worker严格小写比较可复现FAILED且零工具。接受已有证据，不发新的真实请求。新增明确白名单intern-s2/Intern-S2 -> intern-s2，版本intern-s2-returned-name.v1；不泛化大小写、不删身份校验，不接受异型号/缺失等。Worker和人工恢复共用规则，适配器原返回保留，离线probe增加同形合成和显式规则检查。请求model仍intern-s2；Attempt原始请求/返回名与规范化规则版本在parameters持久记录，未知成本/暂停不变。

新增14项零网络专项，含项目API/适配器/Worker的resource.read→VERIFIED反馈→42闭环、7种错误模型零Operation、别名不能越权、人工恢复暂停/拒绝及原名/策略保存。专项14PASS（1.04s），SQLite110PASS/1SKIP/1warning（6.15s），PG111PASS/1warning（17.47s）；ruff/mypy12模块/离线probe/diff/sourcehash PASS。见../evidence/F1-model-identity-TestReport.md及ModelIdentity.md。实际mode=live的测试配置只由代码内合成Settings和固定MockTransport提供，是FAULT_INJECTION而非真实账号验收。未访问.env/凭据、未运行真实API、未消耗父任务留给验证者的3次预算。独立实际复测仍待本次push后进行。

新用户偏好补记：两项目希望跨Windows/苹果/Android等；本仓库记录响应式网页客户端目标，Windows本地后端仍是主验收，Mac本地后端另行兼容验证，Android/iOS仅浏览器连接已运行后端，不承诺手机运行数据库/原生App。窄屏/触控及实际设备/浏览器待独立核查；历史Chromium桌面/视口证据不当作iOS/Android实机PASS。本轮不展开新平台工程、不部署公网、不改监听或防火墙。设计补充见平台产品设计及Scope.md。提交准确SHA下一条追加。

## F1-L010 / 2026-10-05T04:34:26.229781+00:00 / Codex / 模型返回身份修复提交证据

工程提交：[3707ef63e249095d9ffabbb8a3671bd3099a0fc0](https://github.com/T1doo/Sim2Act/commit/3707ef63e249095d9ffabbb8a3671bd3099a0fc0)，dev/f1-foundation。专项14PASS，最终PG111PASS/1warning（17.47s），SQLite110PASS/1SKIP/1warning（6.15s），ruff/mypy/离线probe/hash/diff PASS。只允许canonical请求intern-s2的两种明确返回名称，原返回和策略版本持久审计。未进行真实请求，保留验证者3次预算；推送后交独立验证者复测。此追记只改文档，不改已测代码。

## F1-L011 / 2026-10-05T04:49:18+00:00 / Codex / 独立有界LIVE证据归档

归档前取回远端dev/f1-foundation最新HEAD，确认为dd195681de8966f79cf9ba45188ea15a04704f75，无未知并发修改；只在独立副本添加docs/evidence/LIVE-20261005及更新对应Plan/Log，不改源码、不forcepush。完整[脱敏证据与范围](../evidence/LIVE-20261005/README.md)、[源码hash](../evidence/LIVE-20261005/source-hashes.json)、[证据hash](../evidence/LIVE-20261005/evidence-hashes.json)保留各阶段和失败成本。

原04335528的模型返回名问题经零请求MockTransport/SQLite工程诊断确认FAILED、零工具；合成usage不计费。dd195681的第一项实际PG任务首轮HTTP200/Intern-S2接受/resource.read VERIFIED，但第二体2028>2000在发送前拒绝，Run保持FAILED，不覆盖。经用户明确授权缩短目标，新Run在正常loopbackAPI/独立worker/PG17.9/原InternModel两轮真实HTTP200，输入1170/1958，间隔6.100秒，max_tokens512/stream=false/修复0；反馈后答案42，Operation VERIFIED，Run为PARTIAL/LIVE，语义验收NOT_RUN。身份raw/canonical/policy、已知usage、冻结合同、上下文、回执和API/新连接持久回读均核验，14项零请求身份专项通过。

真实HTTP总预算10已用尽：早期网络诊断3（未知/无返回，不记零费用）、独立API接入4（已知1155tokens）、项目第一任务1（576tokens）、短目标新任务2（1412tokens），已知总3143tokens，剩余0。本次归档不产生真实模型请求、不查询models；不保留请求头、配置环境值、token、私有reasoning、个人资料或原始tar/进程日志。真实输入仅合成文本42。API/worker/临时PG已关闭，原失败导出保留。Windows原生、真实材料、完整账号/故障矩阵和语义/F1整体门仍未通过，AT-02仅合成LIVE反馈子项已验证，F2继续PLANNED；停止测试与开发扩展。

## F1-WCI001 / 2026-10-05 / Codex / 有界Windows云工程验证准备

基线最新开发分支a5b79d12（已ff-only同步，独立LIVE验收文档保留），公共T1doo/Sim2Act、main仍不合并。已核查官方windows-2025镜像PG17二进制与默认停用服务，以及官方pg_ctl Windows restricted-process实现。只新增窄push/contents:read/15min/concurrency取消的标准runner workflow与临时原生PG工程harness，无cache/artifact上传/secret/OAuth/模型请求。

本地ruff/mypy/diff检查通过，Windows实际运行待首次push后监督；不能预写PASS或Win11通过。小smoke调用现有Setup/Doctor/Start/Status/Stop，随后Test Engineering；临时随机账户/localhost集群、运行角色DDL拒绝，always清理。Windows fixture仅补必要系统路径。初期shell gh API读取被envoy CONNECT代理403拒绝，不是GitHub权限判定；已有GitHub连接工具可读取公共仓库和commit workflow runs，未申请新权限。范围/复现/Win11剩余见WindowsCI.md。
