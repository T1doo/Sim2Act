# F1-3 工程实测报告

时间 2026-10-05T03:48:58.147384+00:00；基线 2c3761eecbbf3aca4f220c9226c850ce8c524a91，dev/f1-foundation。Linux/Python3.12.14/临时PostgreSQL17.9；当前工程提交SHA下一条日志追记。

| 实际命令/证据 | 结果 |
| --- | --- |
| .venv/bin/pytest --junitxml=docs/evidence/F1-3-sqlite.xml | 89 PASS、1 SKIPPED（实际PG独立进程）、1 warning；4.93秒 |
| SIM2ACT_TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55432/postgres .venv/bin/pytest --junitxml=docs/evidence/F1-3-postgres.xml | 90 PASS、1 warning；15.01秒，各夹具独立schema并清理 |
| ruff check src scripts tests / mypy src | PASS，12源码模块 |
| python -m sim2act.cli schemas / probe --output docs/evidence/F1-3-offline-probe.json | PASS，严格合成MockTransport，未调用真实API |
| git diff --check / 源码指纹和V5原文哈希复核 | PASS |

新增26个独立工程检查在 test_f1_closure.py；原64项完整回归保留。不是 AT-01—28 或 AT-18 应用并发全通过；Starlette/httpx客户端弃用警告未隐藏。

专项：跨主体/跨项目拒绝后对 runs/run_contracts/resources/operations/grants 五类表计数不变；实际 revoke 端点检查所有者、旧版本拒绝、成功撤权、重复旧版本拒绝，读取和提交随后拒绝，数据库无新增记录。Goal/Run接受时持久冻结，幂等策略冲突，资源/目标/快照修改及旧版缺快照都禁止模型/工具执行，较宽worker配置不能放大请求预算。最小清单预检严格引用/连通/依赖/权限/预算，无业务副作用，真实撤权后候选拒绝。

未知工具：既有文本效果模拟回执丢失，取消先保持RECONCILING；可信关联回读后CANCELLED且已知效果仍列出，不重复写入。正常恢复PAUSED，必须另行继续；继续后PARTIAL且记录/资源计数不变。已知内容不符进入EFFECT_KNOWN_INVALID；无历史请求、未知适配器、错误指纹、非所有者和已撤权不能冒充确认，未知适配器不自动重试。纯读取在冻结输入上回读，未再次派发写入或调用模型。

[PostgreSQL账本证据](F1-3-ledger-audit.json)：独立临时schema实际创建/清理；合成身份/输入；preflight报告、冻结快照、Run/Operation ID、取消意图、可信恢复事件及已有效果。模型行为全部MockModel，未知窗口明确FAULT_INJECTION；运行只有一个Operation、一个冻结快照，无重复效果。API用TestClient调用，不是浏览器或公开服务。本轮没有改前端或启动开发服务；旧浏览器证据仍在F1-2。

问题与修复：最初mypy对预检局部变量类型/复用key报7项错误；改为明确list/set类型及不同用途变量名后通过。新增测试import顺序由ruff发现并修正。全部pytest运行均通过，无测试失败被删。早期88项通过后补读回/未知适配器断言及静态权限覆盖，再执行最终90项回归，最新JUnit对应最终代码。

[源码指纹](F1-3-source-hashes.json)只含可复核源码/Schema/夹具/锁文件，排除egg-info生成物。历史F1/F1-2原哈希中5个egg-info条目移至单独build-generated-hashes报告，保留原哈希不重算；它们不是提交源码，也不能要求Git checkout出现它们。未读取任何实际凭据、未调用真实模型，虚拟环境/数据库/进程数据不提交。

[阶段边界与外部验证步骤](../F1/Scope.md)：本轮只补独立F1工程契约/预检/账本核对；完整编译执行和F2 P-A/P-B/发布、文件落位等未实施。LIVE实际模型/额度/正式能力采集与Windows原生仍BLOCKED，F1未签收。停止继续扩大底座，等待必要前置再验收。

最终补充断言：已有完整模型结果时，可信回读后恢复保留原工具反馈顺序；另行继续不新增Attempt，也不重复创建成果。按最后改动重跑完整90项回归，上表时长与最新JUnit一致。
