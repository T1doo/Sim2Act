# Report 晚回执修复的开发分支集成

本轮从重新发布的独立环境恢复，只沿用 GitHub 已推送进度，不读取或假定旧工作区共享。
远端开发基线为 `cc368dbbda1e4452df64efcac76e184dafe65e6d`，候选为
`bf939ac72298c4d0d5e6c94ed1e1aa0853eb2d7b`。实际 merge-base 等于开发基线，
在 `dev/f1-foundation` 正常 fast-forward 集成候选；不操作 main。
产品冻结仍为 `51487fd4787eae66f09f8ff2b01492d8f9c13503`。

## 新环境核验与限定范围

初始 HEAD `6f688e4dd80b5c81d41aecde90e360d3629f9c21`、分支 work、干净工作树，
只有初始 README。默认 GitHub HTTPS 和 ls-remote 成功。没有 Git merge/rebase/
cherry-pick/revert 状态，也没有 index.lock/refs 锁。空的 Codex 专用
`.git/codex-index-refresh.lock` 始终保留。仓库和当前 workspace 未提供 AGENTS.md
或本地 .agents/skills；读取 README、修复说明、原 evidence、展示契约和上手说明。
初次带 --track 的 switch 因环境仅配置 main fetch 映射失败；核对其已经更新的
index/工作文件后，用普通 switch 建立 dev 分支，随后干净快进，无 reset 或清理用户文件。

读取原限定独审及双后端证据，并依据本次明确授权集成；原证据仍保留为历史。
`source-verification.json` 核对 326 个 src/scripts/tests/.github 与锁定依赖文件，
全部逐字匹配冻结点。本轮只新增 docs 内集成证据和说明，产品、原断言及超时不变。

Python 3.12.14，Node 24.19.0，锁定 Python 依赖，私有 jsdom 30.1.2。
自有 PG 17.9 容器使用 `--network none`、空 listen_addresses、无映射端口和自有专用
Unix socket；仅使用新建合成测试库，pytest 创建并删除自己的随机 test schema。
LIVE=0 / SIM2ACT_LIVE_ENABLED=false，所有模型响应只用原 MockTransport。

## 验证结果

执行和终态见 `test-summary.json`、各日志、JUnit、逐例结果及加载脚本哈希。
执行时 HEAD 为 bf939ac，产品冻结为51487fd；最终提交只是本轮文档证据。
按 SQLite → PostgreSQL 串行运行，未并发矩阵、未放宽等待、未重跑全量。

SQLite 主回归44 PASS（241.812秒）加补充升级1 PASS（10.749秒），
PostgreSQL 45 PASS（501.454秒）；各后端45 PASS、0 FAIL、0 ERROR、0 SKIP。
旧JS负对照各1 EXPECTED_FAIL（SQLite 9.923秒、PG 16.352秒），同一原断言
“new page independently rereads protected presentation history”失败，文本 ALLOW、
两按钮 disabled，旧脚本加载哈希匹配。这两例不计入正向通过数。

- 新增14晚回执矩阵：definition/check × 同应用 ABA、另一应用、真实 connect
  身份切换、撤权、回读失败与显式恢复、已接受响应丢失、同上下文 DOM 刷新。
- 原两个实际 HTTP/产品 JS/jsdom 页面回归；每后端16页面病例、216驱动检查，
  保存回执和页面内容同时核对，实际加载的七份 JS 哈希匹配冻结源码。
- 原展示契约和 PROJECT 边界共26例，权限/来源/版本/锁/成员/损坏回执拒绝不写。
- 原两份实际旧 DAG 源码升级，旧历史和原始 JSON 存储字节保留，旧证明拒绝，
  新执行需要新精确确认；历史源码为5a5543c与1b65e94。
- 补充实际 ffda5b0 Report 源码创建旧展示草案、检查和历史，当前 Store 显式升级、
  冷读和原键重放；全部表和原始 JSON 存储字节保持，canonical 候选不变。
  新旧 db.py 本身逐字相同；功能无需新表，API/worker 没有自动 DDL。
- ffda5b0旧JS同应用 checks 负对照分别在两后端运行，按原断言预期失败。
- Ruff、53源文件 Mypy、JS语法和git diff检查。

补充升级脚本保存在本目录，不改变冻结 tests 或产品代码。复现时把两脚本复制到
自己的临时根目录，准备 ffda5b0 的 src/tests archive 至其 old-report-source，设置
SIM2ACT_REPORT_UPGRADE_ROOT 指向该根目录，用 PYTHONPATH=src:tests 和 -c pyproject.toml
执行本目录 test_owned_report_upgrade.py。其他页面和负对照步骤沿用
[原修复复现说明](../../F2/ReportPresentationLateReceiptFix.md)，两份 DAG archive
按原 tests/test_csv_dag_upgrade.py 指定环境变量准备，PG只指向自有测试库。

一次工具断连保全和恢复核验见 `reconnection-observation.json`。原测试进程持续运行，
没有重新启动 Git 或测试、删除锁/未知进程或修改网络安全设置。
依赖准备时首次 npm 日志重定向早于并行 mkdir 完成而失败，之后在既有私有目录
完成安装；未改依赖版本或产品。FastAPI/Starlette httpx 弃用警告原样保留。

## 保留的未验收边界

PG resources-history Future10秒、旧 DOM lost-check6秒及原探索矩阵超时继续 OPEN，
本轮通过不能解释或关闭这些问题。HTTP200损坏内容清空分支的新提示标记限制保留。
Windows900 / Edge240 / Node150 未验收；本轮 Node驱动/jsdom工程通过不构成原生验收。
未运行 Windows/Edge、后台轮询、全量、真实材料/真实模型或人工签收，也无部署、
强推、main修改、凭据/安全网络配置修改。

PROJECT PENDING/BLOCKED_PARTIAL，实际材料 PENDING，语义 UNKNOWN，人工 PENDING，
整体 NOT_ACCEPTED，发布关闭，LIVE=0。限定修复通过不代表整体验收。
