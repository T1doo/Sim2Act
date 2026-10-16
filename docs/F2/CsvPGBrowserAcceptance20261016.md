# CSV 普通用户流程：本轮资源阻塞

本轮结论为 **BLOCKED，四步产品验收 NOT_RUN**。核查源为已接受的 `f82869db2dbb53e1616f9c14b108696bb893662f`。没有用 SQLite、JSDOM、纯接口或历史 PG/浏览器记录代替这次验收，没有修改产品代码。

## 开工核对与写入范围

指定环境 `/workspace/Sim2Act`，开工 HEAD 与远端 `dev/natural-offline-budget-gate-20261016` 均为上述完整 SHA，工作树干净；`main` 为 `6f688e4dd80b5c81d41aecde90e360d3629f9c21`。现有 `463167fd308889bf81ae7730310a86da24909897` 和 `8fc70cc43a6ac81cd522249e8a3d367cd66c9238` 均为祖先。可用空间约 26 GiB（`/workspace`）、8.8 GiB（`/tmp`）。

root 是唯一仓库写入者；独审仅只读仓库、在自己的 `/tmp` 写报告。新普通分支为 `dev/csv-pg-browser-acceptance-20261016`。没有回旧实例写入/删除，也没有碰未知锁、main、费用、凭据、安全权限或部署。产品、测试、脚本、锁文件及工作流与 f828 均无差异；本轮新增仅报告和证据。

## 实际前置检查

| 目标 | 实际动作和结果 | 状态 |
| --- | --- | --- |
| PostgreSQL | Docker Engine 28.4.0 可读；`docker image ls` 空，`docker ps -a` 空；8 个检查的 DSN/PG 环境变量均未配置；PATH 无 postgres/pg_ctl/psql/pg_isready，无 `/usr/lib/postgresql` 或 `/var/run/postgresql`，进程清单无 PG。没有可指向的既有 PG 服务或连接。 | 缺失，未尝试连接或启动 |
| 真实浏览器 | 已安装 Chromium `151.0.7922.173`，复用仓库已有 playwright-core `1.63.0`；仅一次 `chromiumSandbox:true` 启动，移除既有 driver 列明的弱化安全默认项，未添加禁用沙箱参数。 | BLOCKED，进程退出 SIGABRT，driver RC1 |
| 浏览器具体阻止 | Chromium 原始 stderr：`The SUID sandbox helper binary was found, but is not configured correctly.` 未返回 Browser handle、未打开产品页面、未取得截图/CDP 命令行或下载文件。 | 环境启动阻止；没有降级或重试 |

原始浏览器错误中保留完整启动参数、PID `37073`、退出 signal 和 launcher 自有临时目录 cleanup。随后只读 `ps`：37073 已消失；本次同秒启动的 `37088 chrome_crashpad` 与 `37091 chromium` 为 PPID1、STAT `Z`。它们是僵尸条目，没有活动浏览器；不声称进程表全部清零，也不操作 PID1 或未知进程。

初始有界资源盘点还遇到 `/root/.cache/ms-playwright` 的 `Path.exists` EACCES，以及 `/tmp/codex-daemon-1000` 的 find EACCES；这两处停止且未重试/换工具绕过。它们未被用于推断内部内容。没有自动审批拒绝或待批准动作；浏览器是正常启动时自行中止，PG 是资源未提供。

## 产品流程执行范围

| 用户步骤 | 本轮执行 |
| --- | --- |
| CSV 本地文件选择、预览及显式保存授权 | NOT_RUN |
| 明确保存内部版本、创建实例、提交持久 Run 并读真实结果 | NOT_RUN |
| 下载本次 CSV 结果并检查实际落盘内容 | NOT_RUN |
| 停止并重启 API/worker、关闭并重开浏览器，找回原实例/Run/版本 | NOT_RUN |

产品 pytest/单测为 **0 执行**，PG 连接/事务、Worker、模型请求均为 **0**；没有声称测试 PASS。Ruff、mypy、Windows、真实语义/人工场景、远端 CI 均未运行。浏览器前置启动失败不能计为产品用例通过或产品流程失败。

独立静态审查发现一个待实测功能缺口：[`use.js`](../../src/sim2act/web/use.js) 的普通 CSV 结果和历史目前只渲染文本，没有结果下载按钮；[`app.js`](../../src/sim2act/web/app.js) 的“下载文件”下载的是授权材料，不能替代运行结果；[`internal.js`](../../src/sim2act/web/internal.js) 的 JSON/Markdown 下载属于自然规范成果。这是源码发现，未冒称本轮真实浏览器复现。未在缺少验收资源时增加未经实测的产品改动。

## 可继续的最小条件和路线

继续需要在授权环境中已准备好、可明确指向的隔离 PostgreSQL，以及能保持现有安全设置正常启动的真实浏览器。数据库应沿用既有迁移/应用 CRUD 角色边界、现有本机合成身份和显式私有配置；本轮没有搜寻 `.env`、读取凭据、新建角色/密码、下载镜像、安装软件或申请安全权限。

资源具备后按 [`FirstUse.md`](../FirstUse.md) 的普通页面入口，用新合成项目和 CSV（amount 10/20、quantity 7/8）：文件选择后证明尚未保存 → 显式保存 → 创建草案/预览 → 人工核查并确认内部 Release → 创建实例 → 明确提交 amount Run 得 v1/30 → 下载此 Run 结果并核对文件、Run/实例/版本 → 正常停止及重启自有 API/worker和浏览器 → 原身份/项目/目录找回同一实例与 v1、原 Run，确认恢复只读、没有新 Run。另列 quantity 新 Run 得 v2/15 是明确的新提交，不能混入重启回读。静态发现的 CSV 结果下载入口应在此真实环境中实现和复验；材料下载不能替代它。

只复用既有控制器、权限、幂等 intent、版本和 Worker，不另造 executor/Grant。浏览器运行需要保留真实页面/HTTP/下载落盘/服务重启原件及后台 PG 类型证据，不能仅凭 driver 断言或 API 响应宣称整条用户路径已通过。既有 [`offline_verify.py`](../../scripts/first-use/offline_verify.py) 固定使用 SQLite/JSDOM，不是本轮所需验收。

原始证据及独审见 [证据索引](../evidence/csv-pg-browser-acceptance-20261016/README.md)。本轮没有发现可归因并修复的产品实测故障；未完成的目标是上述完整 PG + 真实浏览器流程及 CSV 结果下载功能验证。
