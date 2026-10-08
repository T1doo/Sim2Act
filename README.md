# Sim2Act

让想法成为会行动的应用。当前开发分支 `dev/f1-foundation`，处于 **F1 工程底座**，尚未通过 F1/R0 验收。

[动态计划](docs/Plan.md) · [F1 任务](docs/F1/Plan.md) · [实际日志](docs/F1/Log.md) · [V5 产品设计](docs/平台产品设计.md)

[本机安装与只读预检](docs/Installation.md)：MOCK 工程体验；真实 Win11 普通用户首次启动仍未测。

[CSV 列绑定局部修改](docs/F2/ColumnBindingPatchQuickstart.md)：同一求和节点 amount → quantity 新草案、精确版本确认、实际只读检查和无关对象保持证明。离线工程候选未验收，旧应用不覆盖，正式发布关闭。

[固定 CSV 三步 DAG](docs/F2/FixedCsvDagQuickstart.md)：在同一应用保存预览 → 求和 → 固定文字报告计划，复用既有 Worker 与持久步骤回执，支持精确确认和冷恢复。离线工程候选未验收。

已成功内部 CSV 任务的有界复用入口：[最短上手说明](docs/F2/RegisteredRunQuickstart.md)。保持本机 MOCK，不代表完整 P-B 或正式发布。

本增量支持：本地身份、三个工作区、项目内文本材料、异步持久任务、独立 API/worker、受控工具与回执、幂等提交、租约/fencing、暂停/取消、授权撤回、有限模型循环和跨进程配额账本。
默认 **MOCK 工程模式**，没有真实书生运行证据。工具链完成显示 `PARTIAL`，不代表目标语义、应用生成或 R0 验收通过。P-A、P-B、发布、增量修改在 F2 实现；不会用空按钮冒充。

## 运行边界

- 目标：Windows 11 x64 原生、Python 3.12 x64、PowerShell 7、PostgreSQL。Windows 精确 OS/依赖组合及脚本实测 **BLOCKED**。
- 已测：云端 Linux、Python 3.12.14、临时 PostgreSQL 17.9；SQLite 仅用于工程夹具，应用启动拒绝 SQLite。
- 云端Windows Server2025工程已测：Python3.12.10 x64、临时PG17.11、六PowerShell接口及111项回归通过；[CI结果与限制](docs/F1/WindowsCI.md)。目标Win11原生验收仍待实测。
- 审计发现的owner环境继承已[本地修复](docs/evidence/F1-env-isolation-20261005/README.md)，Linux PG114项通过；修复后的Windows CI未运行，旧111项不能作为该修复的验证。
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

不要让测试 URL 指向用户数据数据库。Linux沿用requirements.lock；Windows Setup使用独立requirements-windows.lock，完整版本集合及首次py-launcher安装已在Server CI验证，详情见[Windows CI](docs/F1/WindowsCI.md)。目标Win11及其他平台仍需独立验收。

用应用环境变量执行 `python scripts/manage.py doctor|start|status|stop`，用迁移角色显式执行 `python -m sim2act.cli migrate`。API/worker 不自动迁移，也不搜索 `.env`、隐藏凭据或系统文件。PowerShell 仅载入用户显式指定的本地配置。

## 书生接入（LIVE BLOCKED）

运行模型限定 `intern-s2`，固定官方非流式 Chat Completions 端点；开发辅助模型不会进入运行链。适配器使用 HTTP 请求，关闭隐藏重试，严格校验工具参数、结构和结束原因；所有请求共用数据库配额主体。账号被其他程序共用时仍可能遭上游限流。

本轮没有设置真实 token、没有调用收费 API。未来由用户在自己的安全环境设置 `INTERN_API_TOKEN`（或原专用名称 `SIM2ACT_INTERN_TOKEN`），确认有限请求/Token/工具/修复/时限预算，明确设定 `SIM2ACT_LIVE_ENABLED=true` 和 `SIM2ACT_MODEL_MODE=live` 后才能启用。默认工程上限不是用户已批准的 LIVE 预算。

名称优先级：非空 `SIM2ACT_INTERN_TOKEN` 优先；专用变量为空或未设置时读取 `INTERN_API_TOKEN`；两者都为空或未设置则无 token。`.env.example` 中的空专用变量不会遮蔽通用别名。PowerShell 显式配置载入接受这两个名称；Python 仍不自动搜索/读取 `.env`。由用户亲自在私有环境输入，不把值发到聊天、日志或提交；设置 token 本身不会打开 LIVE。

上游约束与参数来自 [书生官方 API 文档](https://internlm.intern-ai.org.cn/doc/docs/Chat/) 和 [模型列表](https://internlm.intern-ai.org.cn/doc/docs/模型列表/)，账号能力仍需实际探针确认。能力报告当前保留 LIVE BLOCKED；未知 usage 保留 null，不记为零、不估算费用。

遇到未核对的在途模型请求，恢复进入 `WAITING_RESOURCE / OUTCOME_UNKNOWN`，不会盲目重发。此增量尚未提供人工核对与重新批准该请求的完整界面，属于下一步工作。

## F1-2 离线检查与人工核对

安装既有锁定依赖后，可运行 `python -m sim2act.cli probe --output offline-report.json`。命令在读取环境配置之前执行，用临时工程库及固定 MockTransport 检查适配器/工具反馈和错误分支，不读取账号、不产生外部请求；模型列表明确 SYNTHETIC，LIVE 仍 BLOCKED。请将报告输出到本地数据目录，避免提交运行数据。

未知模型请求在项目成果画布提供人工核对：记录已有完整响应后保持暂停，需另点“继续”；无法确认时结束任务，保留未知用量和已有效果。依据必须对应原请求指纹；不会靠自动重试抹掉未知请求。详见 [核对规则](docs/F1/Reconciliation.md)、[候选契约校验](docs/F1/Contracts.md) 和 [实测证据](docs/evidence/F1-2-TestReport.md)。

## F1-3 升级与阶段边界

升级既有数据库前先 Stop API/worker；通过已配置的**迁移角色**显式执行 migrate（沿用上文 migration.env / Setup -InitializeDatabase），仅创建新增 run_contracts、operation_intents、local_effects 三表。管理员给运行角色这些表的 SELECT/INSERT/UPDATE/DELETE，再 Doctor/Start；运行角色不做 DDL。没有新凭据发现或自动迁移。

历史任务没有冻结快照时显示 LEGACY_UNFROZEN，不能悄悄按当前内容恢复执行；不要删除旧记录，可明确结束并提交新的授权任务。新任务冻结目标/输入哈希/模式/预算；旧配置或worker无法扩大原上限。

候选清单预检和未知工具核对提供HTTP API，详见 [契约](docs/F1/Contracts.md)、[核对规则](docs/F1/Reconciliation.md)；这不是应用发布或F2运行器。[F1/F2边界及Windows/LIVE验证步骤](docs/F1/Scope.md)明确剩余条件，当前F1未验收。

## F2 本地并行工程：CSV 应用草案预览

F1 仍未签收，F2 正式准入尚未满足；本轮用户明确授权隔离并行开发。先按既有说明由迁移角色执行 migrate（新增 app_drafts/app_previews 表），再向应用角色授予这些表的业务 CRUD 权限；API 不自动建表。

1. 在“资源”保存并授权当前项目的 CSV（最多 32 KiB/1000 条记录）。
2. 打开“应用”，选择 CSV、填写目标说明，点击“创建草案并授权读取”。仅授权该应用读取/汇总这一个材料 24 小时。
3. 选择可用数值列并运行新预览；可更换列得到新的结果/预览 ID，也可回读历史。错误列显示 FAILED，保留历史；不偷偷重试或制造成果。

草案使用 1.0-draft ActionSpec/AppManifest 的固定单节点声明式模板、当前用户与应用 Grant 交集、冻结材料哈希和候选指纹。预览与 F1 任务、发布/实例业务数据分开；最近 50 条历史可回读。撤权/到期或材料变化后需处理授权或重新创建草案，历史接口也会重新授权。界面和 API 使用同一可信读取网关。

这是 MOCK_ENGINEERING 的纯本地受控计算，0 模型请求，0 业务写入；不是自然语言 P-A/P-B 完成、正式发布或 R0-alpha。同步有界只读预览没有后台长任务/暂停取消恢复；这些仍属于后续 F2 完整链路。见 [计划与门槛](docs/F2/Plan.md)。

## 通用目标卡（F2并行草案）

项目页可人工整理任意目标的已知、假设、未决项、硬条件和验收检查，并选择同项目授权材料。保存追加版本，旧窗口版本冲突时重新打开目标卡，未保存文字保留；历史可回看最近50版。目标卡不会启动模型、执行任务或发布应用，不能代替P-A/P-B生成或正式验收。

更新现有安装时，先由迁移角色按既有migrate说明创建goal_cards/goal_card_versions，再为应用角色授予两表业务CRUD；API不自动DDL，不把迁移身份交给API/worker。撤权或材料版本改变会阻止相关旧快照回读/修订。工程边界与证据见docs/F2/Plan.md和docs/evidence/F2-goal-cards-20261005。


## 已保存目标 → MOCK固定能力候选 → CSV预览

1. 在项目目标卡绑定已授权CSV并保存，打开该目标卡。
2. 在“从已保存目标创建候选”选择绑定CSV及可信“CSV数值列求和”，点击“创建候选并授权预览”。使用已保存版本；未保存编辑不会混入。仅给这个preview应用所选CSV的读取/求和授权24小时。
3. 应用页明确显示MOCK、目标来源版本、未验收/未发布。选择数值列运行，查看新结果/历史；“返回来源目标卡”可回到最新卡并从候选列表重新打开。刷新后重新连接，已保存目标、候选及预览历史仍可回读。

取消提交前不创建候选。提交已接受后“返回编辑”只停止页面跳转，候选仍保留；同步事务不是可暂停/取消的后台AppRun。失败保留编辑；相同请求键重试返回同候选且不重复创建身份/Grant。旧目标版本候选不随目标修订改变；所有来源材料在候选详情/预览重新校验权限及hash，旧快照不能恢复撤权。候选列表仅元信息，不作为执行授权。

P-A只支持人工目标分项+用户明确选择固定声明式模板的工程子集，没有自然语言理解、任意应用生成或语义验收；完整P-B仍未验收；成功内部CSV任务→已有授权新CSV→冷运行的有界子集见[上手说明](docs/F2/RegisteredRunQuickstart.md)。零真实模型请求，候选PREVIEW_ONLY，不是Release。更新既有安装仍需迁移角色显式migrate创建goal_candidate_requests并给应用角色该表业务CRUD；API/worker不自动DDL，不发现凭据。测试边界见docs/F2/Plan.md。
