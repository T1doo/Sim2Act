# 本机安装与首次启动（MOCK 工程体验）

目标环境是 Windows 11 x64 原生、Python 3.12 x64、PowerShell 7 和本机 PostgreSQL。本说明与新增预检在 Linux 验证；**真实 Win11 普通用户安装/启动未测**，不能据此签收 AT-01、AT-27 或 F1。MOCK 不需要模型账号，当前工程能力与正式产品验收边界见 [README](../README.md)。

本切片基线为 `e828c066ec63689fe5de5d66f650eda33c0086e8`。安装切片源 `e700db211378e67ca99529f4a5270f0ea6162769` 已正常整合至当前开发工作副本；拉取分支使用 `dev/f1-foundation`。本说明不要求管理员权限来运行 API/worker；数据库建库、建角色和授权由本机数据库管理员另外准备。

## 1. 准备软件与拉取代码

从 [Git](https://git-scm.com/downloads/win)、[Python](https://www.python.org/downloads/windows/)、[PowerShell](https://learn.microsoft.com/powershell/scripting/install/installing-powershell-on-windows)、[PostgreSQL](https://www.postgresql.org/download/windows/) 的官方入口手动安装所需软件。Python 选择 **3.12 x64，并包含 `py` 启动器**；PowerShell 使用 7（命令 `pwsh`，Windows 自带的 `powershell` 不是本说明的启动环境）。数据库需本机服务和独立应用数据库；`psql` 不在 PATH 不代表数据库服务未安装。安装后重新打开终端，先检查：

```powershell
git --version
py -3.12 --version
pwsh --version
```

Python 必须显示 3.12，PowerShell 必须显示 7.x。没有 `py` 时先修正 Python 安装，不进入 Setup。这里不需要 Node、Docker 或 WSL，也不要修改全局执行策略、ACL、UAC 或浏览器沙箱。若单位策略阻止运行脚本，联系本机管理方处理，保留阻止信息。

在 PowerShell 7 中进入你自己的可用目录（路径可以包含空格），再执行：

```powershell
git clone --branch dev/f1-foundation https://github.com/T1doo/Sim2Act.git
Set-Location Sim2Act
Copy-Item .env.example .env
notepad .env
py -3.12 .\scripts\install_preflight.py --stage setup
```

`.env` 是本机私有文件。保持 `SIM2ACT_MODEL_MODE=mock`、`SIM2ACT_LIVE_ENABLED=false`，两个模型 token 留空。管理员提供的应用角色数据库 URL 填入 `SIM2ACT_DATABASE_URL`；不要沿用 `LOCAL_PASSWORD`。含 URL 特殊字符的用户名/密码需要百分号编码，由本机管理员提供正确 URL。`SIM2ACT_DATA_DIR` 建议填写本人可用的明确绝对目录；值不加引号，不使用 `$env:...` 或 `%USERPROFILE%`（配置加载器不会展开它们）。配置采用 UTF-8、每行 `KEY=value`，等号前后不要加入空格。

预检仅确认本机依赖及配置是否存在、配置行格式和必填值是否非空；不会判断密码、URL、预算、模式或目录权限是否有效。复制模板也可能 PASS，**必须亲自替换数据库占位值**。它不读取环境变量或自动搜寻其他配置，不显示密钥，不安装软件，不启动进程，不改系统设置，也不连接数据库或模型服务。

输出 `[BLOCKED]` 时按该项 `Next` 处理后重跑。全部 PASS 后再进入安装步骤。退出码 `0` 表示本阶段存在性检查通过，`1` 表示阻塞，`2` 表示命令参数错误。输出可用 `--json` 转为结构化报告；不要把配置文件、令牌或原始数据库异常发到聊天。

## 2. 安装项目依赖，显式准备数据库

```powershell
pwsh -NoProfile -File .\scripts\Setup.ps1 -Config .env
.\.venv\Scripts\python.exe .\scripts\install_preflight.py --stage start
```

Setup **会安装**仓库锁定的 Python 依赖，首次安装需要访问软件包源；新增预检本身完全离线。启动前必须使用 `.venv\Scripts\python.exe`，用系统 Python 检查另一套包会误导诊断。`dependencies` 阻塞时按 Setup 安装或修复依赖；不要随意升级锁定版本。

数据库是首次启动的真实前置条件，预检无法代替这一项：管理员预先建立独立数据库、迁移角色（用于建表）和应用角色（业务表读写，不是超级用户，无建库、建角色或任意 schema 建表权）。管理员按照 [现有数据库说明](../README.md#windows-原生复现说明待实测) 完成角色及业务表授权。不要把管理员或迁移 URL 填进日常 `.env`。

由本机持有迁移配置的操作者执行以下已有接口；`migration.env` 与 `.env` 使用相同格式，但数据库 URL 是迁移角色，文件保持私有且不提交：

```powershell
pwsh -NoProfile -File .\scripts\Setup.ps1 -Config migration.env -InitializeDatabase
# 管理员随后为应用角色授予目标 schema 的 USAGE 和业务表的 SELECT/INSERT/UPDATE/DELETE。
pwsh -NoProfile -File .\scripts\Doctor.ps1 -Config .env
```

Doctor 会实际连接应用角色数据库并只读查询 PostgreSQL 系统目录。输出 `STRUCTURAL_READY` 表示当前代码声明的表、列、主键/唯一键、有效 schema/名称解析及逐项 CRUD 权限匹配，且当前/登录身份及可达角色没有管理员、数据库/schema/业务表 owner 或 schema CREATE 能力；不是写入、RLS、身份、worker 或产品验收通过。`database=UP` 仅表示连接成功，不能代替 `status`；`BLOCKED` 返回非零退出码。SQLite/未知数据库不能建立 PostgreSQL 资格。输出不含数据库 URL、凭据或原始异常，也不读取用户业务行。每次升级涉及新表时，由迁移角色显式迁移，再由管理员授予新增表 CRUD；API/worker 不自动建表。Doctor 缺表/结构不符时交迁移操作者，缺权限或过高权限时交数据库管理员；它不执行迁移、授权、身份创建或自动修复。列/权限目录无法核实时也保持 BLOCKED。此检查已在独立合成 PostgreSQL 16 库一次执行 23 项目录/权限负例并通过；[限定证据与边界](F2/R0DatabaseReadinessLog.md) 不代表用户实际数据库、业务写入或 Win11 安装通过。无需本机管理员权限即可使用已准备好的应用角色。 检查只给出读取时的目录诊断，不作为后续操作的授权凭证；操作仍走原有当前身份和权限校验。自定义触发器、RLS策略、业务写入和干净 Win11 尚未实测，不能由 `STRUCTURAL_READY` 推断通过。

## 3. 初始化本机身份与启动

在仓库根目录的 PowerShell 7 中执行；`init-user` 的本机令牌只显示一次，私下保存：

```powershell
. .\scripts\Common.ps1
Import-Sim2ActConfig '.env'
Invoke-Sim2ActPython -Arguments @('-m', 'sim2act.cli', 'init-user', '--name', '本机使用者')
pwsh -NoProfile -File .\scripts\Start.ps1 -Config .env
pwsh -NoProfile -File .\scripts\Status.ps1 -Config .env
```

仅首次创建身份时执行 `init-user`；日后启动沿用已有本机身份与令牌。浏览器打开 Start 输出的 `127.0.0.1` 地址，输入令牌连接。令牌保存在页面内存，刷新页面后需要重新连接。

第一次体验可以使用以下合成材料（无模型调用）：创建项目 → 在“资源”保存 `demo.csv` 并授权给当前项目 → 在“应用”创建 CSV 草案并授权读取 → 选择 `amount` 列运行预览，应该得到 `30`。用新预览 ID 和结果确认这一次运行，而不是把旧历史当新结果。

```csv
item,amount
A,10
B,20
```

继续体验“私有草案 → 人工确认内部版本 → 独立实例 → 新 AppRun → 结果与冷会话历史”，请按 [第一次使用](FirstUse.md) 的实际按钮顺序操作；资源入口粘贴 CSV 文本，预览列与持久任务列必须分别选择。

这是固定能力 CSV 本地预览，不代表自然语言生成、正式发布或完整 P-A/P-B 验收。已有成功内部 CSV 任务的有界复用路径另见 [RegisteredRunQuickstart](F2/RegisteredRunQuickstart.md)。

完成后运行：

```powershell
pwsh -NoProfile -File .\scripts\Stop.ps1 -Config .env
```

关闭网页不取消后台任务；停止 worker 或关机会停止处理。Stop 只停止启动器记录且身份匹配的 API/worker，保留数据库服务、用户数据与日志。不要为了排错删除数据库或数据目录。

## 常见阻塞与下一步

| 现象 | 下一步 |
| --- | --- |
| `py` / `pwsh` 未找到 | 手动安装指定组件，重新开终端，检查版本；不修改安全策略 |
| 配置缺失或格式阻塞 | 在本机编辑显式选择的文件；不贴出内容；相对 `--config` 路径按仓库根目录解析 |
| `.venv` 不存在，或虚拟环境选择阻塞 | 完成 Setup，随后用仓库 `.venv` 的 Python 运行启动前预检 |
| Setup 下载或依赖安装失败 | 检查软件包源网络及本机代理，再运行既有 Setup；不要换掉 lock 或关闭 TLS 校验 |
| Doctor 无法连接数据库 | 确认本机 PostgreSQL 服务、数据库、应用角色和 URL；由管理员核查，预检 PASS 不证明这些有效 |
| `relation does not exist` / `permission denied` | 由迁移操作者与管理员确认显式迁移、schema USAGE 和业务表 CRUD；不把应用角色升为管理员 |
| `Port occupied; no process started` | 不杀其他程序；选择空闲端口，例如 `Start.ps1 -Port 8001`，Status 同样指定 `-Port 8001`，使用 Start 输出地址 |
| Start 子进程退出或身份验证失败 | 保留本机日志，先 Status；核对应用配置与依赖，按固定诊断逐项排查，不自动无限重试 |
| 网页刷新后未连接 | 重新输入已有本机令牌；不重复创建用户，不改数据库 |

## Linux / macOS 方向与本切片验证

预检使用 Python 标准库，非 Windows 不要求 `py` 或 `pwsh`。以下是安装/配置存在性检查方向，不是 macOS 原生或 Linux 完整首次启动验收：

```bash
python3.12 scripts/install_preflight.py --stage setup --config .env
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock
.venv/bin/python -m pip install -e . --no-deps
.venv/bin/python scripts/install_preflight.py --stage start --config .env
```

Python 生命周期入口不自动载入 `.env`，Linux 完整运行需要由操作者在私有环境显式设置应用配置，遵守相同数据库角色分离规则；见 [Linux 工程验证](../README.md#linux-工程验证)。本切片不新增跨平台配置加载器或自动启动入口。

独立合成测试（无需安装项目依赖）和静态检查命令：

```bash
python3.12 -m unittest discover -s tests -p test_install_preflight.py -v
python3.12 -m ruff check scripts/install_preflight.py tests/test_install_preflight.py
```

覆盖缺配置/编码/格式、必填键、解释器/架构、Windows 命令缺失、平台 lock、错误虚拟环境、包缺失/版本偏差、固定诊断脱敏及退出码。真实 Win11、PowerShell 执行、PostgreSQL 服务、首次网页流程、macOS 均须后续实测；此工具不会将它们报告为 PASS。

本切片实际验证记录（2026-10-07）：Linux x86_64、Python 3.12.14；13 项独立 unittest 全部通过（0 失败/0 跳过），Ruff 0.15.6 check 通过。Ruff 使用 `/tmp` 内隔离开发工具环境，未改项目 lock 或系统软件。真实 CLI 从仓库外目录读取显式合成配置：setup 返回 0/PASS，start 返回 1/BLOCKED（仓库虚拟环境及锁定依赖未准备），缺配置返回 1/BLOCKED；配置/环境秘密哨兵不出现在输出，配置字节与临时目录文件列表保持不变。独立审查另以合成平台/包元数据覆盖 Windows/Linux 两阶段及坏配置/缺命令；文件 SHA256 不变，网络/进程启动陷阱未触发，未发现阻塞问题。按审查建议，实际 CLI 测试允许缺先决命令时正确返回 BLOCKED，避免要求测试机先完成产品安装。Windows 合成分支不是 Windows 实测；未运行整套产品回归或新 CI，因为本切片没有改既有产品源码。

主开发已正常 cherry-pick 本切片的三个新增文件，并在 README 加入说明链接、将拉取分支切回 `dev/f1-foundation`。安装切片未修改产品核心、生命周期入口、权限、迁移或 workflow。后续 Win11 普通用户验收按上述步骤记录真实阻塞、介入、进程及首次 CSV=30 结果，不以预检测试数替代可用性结论。
