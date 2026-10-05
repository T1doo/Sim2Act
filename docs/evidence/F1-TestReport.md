# F1 第一个工程增量：实际验证

2026-10-05，云端Linux，Python 3.12.14、PostgreSQL 17.9临时测试容器、MOCK/FAULT_INJECTION。精确源码文件hash见 [F1-source-hashes.json](F1-source-hashes.json)，源码提交：[f496f225ae109e4415cff3a1fa8117451a82fda3](https://github.com/T1doo/Sim2Act/commit/f496f225ae109e4415cff3a1fa8117451a82fda3)；实际证据追记在F1 Log。

| 检查 | 实际结果 | 证据 |
| --- | --- | --- |
| Ruff：src/scripts/tests | PASS | 本任务执行记录 |
| mypy：src | PASS | 10模块，无类型错误 |
| JS语法 | PASS | node --check src/sim2act/web/app.js |
| SQLite工程夹具pytest | 34 PASS / 1 SKIPPED | [JUnit](F1-sqlite.xml)，PG真实进程检查仅在PG执行 |
| PostgreSQL pytest | 35 PASS | [JUnit](F1-postgres.xml)，包含实际API/worker断开/停止/重启 |
| Wheel UI资源 | PASS | wheel内index.html/app.js/app.css均存在 |
| 运行角色DDL拒绝 | PASS | smoke实际创建表被数据库拒绝 |
| 浏览器主链/刷新回读/撤权隐藏 | PASS（MOCK） | [项目截图](F1-project.png)、[资源截图](F1-resources.png)、[运行引用/输入hash](F1-process-smoke.json) |
| 跨执行命令生命周期 | PASS（修复后） | 独立Start/Status/Stop，最终health OFFLINE |
| 源码文档秘密模式检查 | PASS | 仅合成令牌及模板占位；未读取隐藏凭据 |
| AT-01/27 Windows原生 | NOT_RUN，BLOCKED | 缺真实Windows条件，PowerShell未执行 |
| AT-02 LIVE | NOT_RUN，BLOCKED | 缺安全注入与批准预算；无真实API调用 |
| AT-09—28 | NOT_RUN | 已冻结规格，后续阶段实现 |

AT-03/04/05/06/07/08这里只报告工程子集，完整F1门没有签收。AT-07的429/120秒截断形态是注入，并没有压测真实上游或等待真实120秒。模型用量缺失保留unknown/null，不记为零。任务工具链终态PARTIAL，目标验收NOT_RUN。

执行命令：`.venv/bin/python -m pytest -q --junitxml=docs/evidence/F1-sqlite.xml`；PG使用显式`SIM2ACT_TEST_DATABASE_URL`指向隔离临时库执行同一命令并输出F1-postgres.xml。测试仅清理自己的test_* schema，未触及用户业务数据。

失败完整性：首轮夹具12PASS/9ERROR、进程停止超时FAIL、跨沙箱cwd导致误报停止均保留在F1 Log；未重新标记为成功历史。原始终端输出在本任务执行记录，仓库保存原因与修复摘要。Starlette/httpx测试客户端仍有1条弃用警告；后续依赖兼容性检查需处理，不影响此次实际断言。

浏览器：使用agent-browser技能，经本机Chromium/CDP访问仅含合成数据的localhost；有意义内容、三个工作区及实际操作可见，errors/console命令未报告页面错误；容器浏览器启动配置失败已记日志，未把失败静默删除。截图不含访问令牌。
