# Sim2Act

让想法成为会行动的应用。当前开发分支 `dev/f1-foundation`，处于 **F1 工程底座**，尚未通过 F1/R0 验收。

[动态计划](docs/Plan.md) · [F1 任务](docs/F1/Plan.md) · [实际日志](docs/F1/Log.md) · [V5 产品设计](docs/平台产品设计.md)

本增量支持：本地身份、三个工作区、项目内文本材料、异步持久任务、独立 API/worker、受控工具与回执、幂等提交、租约/fencing、暂停/取消、授权撤回、有限模型循环和跨进程配额账本。
默认 **MOCK 工程模式**，没有真实书生运行证据。工具链完成显示 `PARTIAL`，不代表目标语义、应用生成或 R0 验收通过。P-A、P-B、发布、增量修改在 F2 实现；不会用空按钮冒充。

## 运行边界

- 目标：Windows 11 x64 原生、Python 3.12 x64、PowerShell 7、PostgreSQL。Windows 精确 OS/依赖组合及脚本实测 **BLOCKED**。
- 已测：云端 Linux、Python 3.12.14、临时 PostgreSQL 17.9；SQLite 仅用于工程夹具，应用启动拒绝 SQLite。
- 前端是随 Python 包分发的静态 HTML/CSS/JS，无 Node 构建依赖；默认本机 API 提供资源，不启动每应用服务器。
- API 仅绑定 `127.0.0.1`。关闭网页不会取消任务；停止 worker 或关机会停止处理；未完成模型请求的结果/用量可能未知。
- R0 不执行模型生成的 Python、JS、Shell、SQL，不安装模型指定依赖，不读取任意路径，不支持真实外部写入。

## Windows 原生复现说明（待实测）

安装 Git、Python 3.12 x64、PowerShell 7 与 PostgreSQL。PostgreSQL 17.9 仅为本轮 Linux 测试版本，尚不能据此冻结 Windows 验收版本。不要修改全局 PowerShell 安全策略。

```powershell
git clone --branch dev/f1-foundation https://github.com/T1doo/Sim2Act.git
Set-Location Sim2Act
Copy-Item .env.example .env
# 在本机编辑 .env；保持 MOCK，配置本机数据库应用角色和明确数据目录。
# 不把密钥发到聊天，不提交 .env，不沿用示例密码。
pwsh -NoProfile -File .\scripts\Setup.ps1
```

数据库应预先由本机管理员建立：独立数据库、迁移角色（可建表）、应用角色（仅业务表读写）。应用角色不授予超级用户、建库、建角色、任意 schema 建表或管理员权限。用单独本地配置文件 `migration.env` 指向迁移角色后执行：

```powershell
pwsh -NoProfile -File .\scripts\Setup.ps1 -Config migration.env -InitializeDatabase
# 管理员随后仅向应用角色授予目标 schema 的 USAGE，及业务表的 SELECT/INSERT/UPDATE/DELETE。
pwsh -NoProfile -File .\scripts\Doctor.ps1 -Config .env
# 载入明确指定的应用配置，在本机初始化身份（令牌只显示一次，请私下保存）。
. .\scripts\Common.ps1
Import-Sim2ActConfig '.env'
Invoke-Sim2ActPython -Arguments @('-m', 'sim2act.cli', 'init-user', '--name', '本机使用者')
pwsh -NoProfile -File .\scripts\Start.ps1
pwsh -NoProfile -File .\scripts\Status.ps1
```

浏览器打开 Start 输出的地址，用本机访问令牌连接。创建项目 → 在资源工作区保存并授权 TXT/MD/CSV/JSON 文本 → 回到项目提交目标 → 查看后台状态、成果和可展开的来源回执。资源授权当前为 24 小时；撤回或到期后重新读取和派发拒绝。令牌只保存在页面内存，刷新后重新连接。

```powershell
pwsh -NoProfile -File .\scripts\Test.ps1 -Suite Engineering
pwsh -NoProfile -File .\scripts\Stop.ps1
```

Stop 只停止启动器记录且身份匹配的 API/worker，保留数据库服务、日志和数据；不存在自动清库/卸载操作。PID 文件不含令牌或数据库 URL。端口冲突拒绝启动，不终止其他程序。启动/状态输出分别报告 API、worker、数据库和数据目录。

`Test.ps1 -Suite R0` 明确拒绝：完整首版验收尚未实现，不能把工程 pytest 作为 R0 通过。

## Linux 工程验证

```bash
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/python -m ruff check src scripts tests
.venv/bin/python -m mypy src
.venv/bin/python -m pytest -q
# 可选：仅显式指定隔离测试 PostgreSQL URL，pytest 自动建立并清理自己的 test_* schema。
# SIM2ACT_TEST_DATABASE_URL='<隔离测试数据库>' .venv/bin/python -m pytest -q
```

不要让测试 URL 指向用户数据数据库。完整依赖锁由本轮 Linux 安装生成；跨平台安装及 Windows 原生运行需独立验收。

用应用环境变量执行 `python scripts/manage.py doctor|start|status|stop`，用迁移角色显式执行 `python -m sim2act.cli migrate`。API/worker 不自动迁移，也不搜索 `.env`、隐藏凭据或系统文件。PowerShell 仅载入用户显式指定的本地配置。

## 书生接入（LIVE BLOCKED）

运行模型限定 `intern-s2`，固定官方非流式 Chat Completions 端点；开发辅助模型不会进入运行链。适配器使用 HTTP 请求，关闭隐藏重试，严格校验工具参数、结构和结束原因；所有请求共用数据库配额主体。账号被其他程序共用时仍可能遭上游限流。

本轮没有设置真实 token、没有调用收费 API。未来由用户在自己的安全环境设置 `SIM2ACT_INTERN_TOKEN`，确认有限请求/Token/工具/修复/时限预算，明确设定 `SIM2ACT_LIVE_ENABLED=true` 和 `SIM2ACT_MODEL_MODE=live` 后才能启用。默认工程上限不是用户已批准的 LIVE 预算。

上游约束与参数来自 [书生官方 API 文档](https://internlm.intern-ai.org.cn/doc/docs/Chat/) 和 [模型列表](https://internlm.intern-ai.org.cn/doc/docs/模型列表/)，账号能力仍需实际探针确认。能力报告当前保留 LIVE BLOCKED；未知 usage 保留 null，不记为零、不估算费用。

遇到未核对的在途模型请求，恢复进入 `WAITING_RESOURCE / OUTCOME_UNKNOWN`，不会盲目重发。此增量尚未提供人工核对与重新批准该请求的完整界面，属于下一步工作。
