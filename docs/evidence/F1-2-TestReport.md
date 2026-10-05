# F1-2 实际工程检查

记录时间：2026-10-05T03:28:49.450701+00:00。基线 5c930bc3e668294f1f55f3fc60a5d13a485c4c20；分支 dev/f1-foundation；Linux / Python 3.12.14 / 临时 PostgreSQL 17.9。工程源码提交：[637cca93aeb7022cb1062c73bb43ff40cab9c29d](https://github.com/T1doo/Sim2Act/commit/637cca93aeb7022cb1062c73bb43ff40cab9c29d)；后续仅文档追记。

## 实际命令与结果

| 命令 | 实际结果 |
| --- | --- |
| .venv/bin/pytest --junitxml=docs/evidence/F1-2-sqlite.xml | 63 PASS、1 SKIPPED（实际 PostgreSQL 进程用例）、1 warning，2.90 秒 |
| SIM2ACT_TEST_DATABASE_URL=postgresql+psycopg://postgres@127.0.0.1:55432/postgres .venv/bin/pytest --junitxml=docs/evidence/F1-2-postgres.xml | 64 PASS、1 warning，9.88 秒；各测试独立临时 schema 并清理 |
| .venv/bin/ruff check src scripts tests | PASS；最后新测试局部 import 排序问题已自动修复 |
| .venv/bin/mypy src | PASS，11 modules |
| node --check src/sim2act/web/app.js | PASS |
| .venv/bin/python -m sim2act.cli schemas | PASS，重新生成草案 Schema |
| .venv/bin/python -m sim2act.cli probe --output docs/evidence/F1-2-offline-probe.json | PASS，仅 httpx.MockTransport 合成链路；不读取环境配置/凭据 |
| git diff --check | PASS |

Starlette 测试客户端的 httpx 弃用警告仍存在，未隐藏。64 个工程检查是 35 个既有回归加 29 个新增检查，不等于 AT-01—28 全通过。新增检查涵盖闭合嵌套契约/类型/有限条件、草案 DAG、授权候选无副作用、人工核对双路径/版本与权限/取消意图/未知工具效果/重复 JSON 键、慢模型期间独立心跳、并发不同任务领用、无效响应保留已知失败用量、离线探针不读取环境凭据。

## 浏览器及账本证据

使用 agent-browser + 已有 Chromium/CDP，仅访问合成 localhost 页面。真实 API 与 worker 独立启动；准备合成失联 Attempt 后停止 worker，无上游请求。

- close_unknown：浏览器填写依据并确认成本，Run CANCELLED，Attempt CLOSED_UNKNOWN，usage unknown/null；截图 F1-2-reconcile-before.png、F1-2-reconcile-after.png。before 保留早期长指纹导致列溢出的现场；已改为短标签/完整 title、弹性列 minmax(0,...)。
- record_response：填写明确合成的保存响应，提交后 Run PAUSED、工具 Operation 数为 0；截图 [核对前](F1-2-reconcile-import-before.png)、[暂停后](F1-2-reconcile-import-paused.png)。修复后实际视口宽 1280、页面 scrollWidth 1265，没有水平溢出。
- 明确点击“继续”后，独立 worker --once 执行，Run PARTIAL、一个已核验读取回执；截图 [继续后](F1-2-reconcile-import-partial.png)。goal_acceptance 仍 NOT_RUN。
- 无浏览器 errors；[账本引用与核对审计](F1-2-browser-audit.json) 保留实际 Run/Attempt/Operation ID、版本、USER_SUPPLIED 事件、未知用量。导入前无工具效果由数据库实际断言。
- 截图首次相对路径保存失败，改用绝对仓库路径成功；没有改代码掩盖该工具问题。
- 收尾 manage.py stop 成功，另一次 status 为 OFFLINE；浏览器关闭，保留临时 PostgreSQL 和数据供后续复查；没有部署公开服务。

## 能力探针与边界

[F1-2-offline-probe.json](F1-2-offline-probe.json) 使用临时 SQLite 工程库和固定 httpx.MockTransport；2 个合成 wire 请求，经真实 Intern 适配器/Worker/工具反馈代码。Attempt 模式都是 MOCK、响应用量 unknown/null，模型列表明确 SYNTHETIC、权重版本 unknown。测试禁止 Settings.from_env；此命令没有 LIVE 开关，也不能调用真实账号。

LIVE 实际模型列表、账号额度、正式反馈链和 Windows 原生 PowerShell 仍 BLOCKED/NOT_RUN。探针工程接口完成不表示真实能力通过。完整清单编译/发布、GoalSpec/Run 冻结语义、跨系统未知效果恢复和 F2/P-A/P-B 尚未实施。F1 整体 IN_PROGRESS，原阶段门和规格未降低。

源码指纹：[F1-2-source-hashes.json](F1-2-source-hashes.json)。V5 sources 原始文件未修改。测试口令都是显式 synthetic，不含实际凭据；临时数据/进程记录/虚拟环境不提交。
