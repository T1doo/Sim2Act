# 接上已有数据库与免费 Intern 试运行

当前源码已接入固定免费 Intern，沿用用户已经确认的零费用账户；不要求再次确认费用。此处把已有配置和已批准的精确试运行接到正式 Worker，不创建数据库账户、模型 token、OAuth 或新的权限。已冻结的完整链源码为 9523d3e2bd5e6429c0a3744d0c2ec22e0a8abafc；完整链是7次合成 Mock+真实时钟文件SQLite，真实 Intern 提取另有证据。正式 PostgreSQL/真实模型全链尚未验证。

## 1. 私下选择已有应用连接

在本地明确选择的 `.env` 中填写数据库管理员已经提供的 **PostgreSQL 应用角色** URL；不能填管理员/迁移角色，也不能保留 `LOCAL_PASSWORD`。Python 不会自动寻找 `.env`。Windows 沿用 `Doctor.ps1 -Config .env`；Linux/macOS 可用：

```sh
.venv/bin/python scripts/manage.py doctor --config .env
```

这会实际连接选定数据库，复用现有表/列/键/角色/CRUD目录检查。诊断连接最多等待5秒，每条查询最多5秒、锁最多1秒；保留原有TLS/search_path选项。只读检查、不自动迁移/建用户/启动Worker/调用模型。`STRUCTURAL_READY`只证明读取时结构与权限，后续操作仍重新鉴权。配置文件不会执行shell表达式，也不会将DSN或token写入报告。

缺库或角色时由已有数据库操作者准备；缺表/权限交现有迁移操作者与管理员。已有 `Setup.ps1 -Config migration.env -InitializeDatabase`/`sim2act.cli migrate` 是显式初始化入口，不能用应用角色提权替代。第一次初始化需要原方案中的独立迁移角色；已有身份继续使用既有本机访问令牌，不重新 `init-user`。

## 2. 选择已有免费模型配置

正式试运行需要以下已有设置，均在服务端私下配置；网页不接收数据库密码或模型令牌：

```ini
SIM2ACT_MODEL_MODE=live
SIM2ACT_LIVE_ENABLED=true
SIM2ACT_MODEL=intern-s2
SIM2ACT_GOAL_PLANNER_PROVIDER=intern-s2
SIM2ACT_APPLICATION_GENERATION_ACTIVATION_ENABLED=true
SIM2ACT_QUOTA_SUBJECT=intern-ai-account-8a3c6e77f1e3dda560baf0a1a0789fc6dcfe955fe42543f8255f0e278685f56e
```

token继续使用既有非空 `SIM2ACT_INTERN_TOKEN`，否则使用既有 `INTERN_API_TOKEN`。不生成或复制到选择JSON；如令牌由环境注入，所选配置中不要用空同名行将其覆盖。固定endpoint为 `https://chat.intern-ai.org.cn/api/v1/chat/completions`，没有付费fallback。已有请求/工具/修复/token/输出/Run时限预算继续生效，只能收紧。配置不是精确任务批准。

旧数据库可能仅初始化了默认 quota。`QUOTA_SUBJECT_NOT_INITIALIZED` 表示固定账号额度行尚不存在；由**已有迁移角色**在同一个固定 `SIM2ACT_QUOTA_SUBJECT` 下显式执行原初始化流程。Doctor不会插入该行，Worker原检查也保留。

## 3. 在页面准备并选择精确试运行

用既有本机访问令牌连接页面，选择已有项目。在目标卡的“独立试验准备”中选择两张完整、各绑定一份已授权TXT的目标卡，读取并确认精确七槽范围。新建正式LIVE准备会绑定服务器的固定账号；Mock仍是原合成范围。恢复原key只读取原合同，不会将旧 `unconfigured:` 合同改绑成正式合同。旧准备需要按原流程明确结束/撤回后，另建新的准备并重新确认具体范围。

批准后打开“正式连接与启动选择”，点击“导出此试运行启动选择”。会重新GET原范围并鉴权，下载 `trial-selection.json`，只含 `user/project/trial/approval/account` 五个元数据，不含凭据、材料或授权凭证。当前页面准备的是 **P-A**；P-B必须使用原有P-B合同、recipe和来源链，不能将P-A改标签冒充P-B。

在同一私有配置下先检查，再明确启动：

```powershell
pwsh -NoProfile -File scripts/Doctor.ps1 -Config .env -SpecSelection trial-selection.json
pwsh -NoProfile -File scripts/Start.ps1 -Config .env -SpecSelection trial-selection.json
```

Linux/macOS等价入口：

```sh
.venv/bin/python scripts/manage.py doctor --config .env --spec-selection trial-selection.json
.venv/bin/python scripts/manage.py start --config .env --spec-selection trial-selection.json
```

Doctor会重新核原合同、软件字节、批准、当前资源/项目权限、固定账号及quota行；不会领取任务或发模型请求。Start在启动任何子进程之前重复原安装核验，拒绝时API和Worker都不启动；Worker只接收到明确选择的原试运行，并在每次真正执行时继续原检查。Start会处理原范围内已明确受理的任务；请只在确实要执行该精确范围时启动。过期、撤权、改材料/软件或旧key不能靠重导出续期/放行。

## 当前云端缺项与验收边界

当前执行环境的既有 `INTERN_API_TOKEN` 非空；没有注入应用数据库URL，也没有选定数据库中的真实principal/project/trial/approval。因而没有启动新的正式调用。最小缺项是已有应用连接、结构/权限及固定quota行，以及上述原批准选择；不是缺免费使用许可。

冻结Mock整链两次结算88.14/97.24秒，写入区段上界52.82/54.96秒，完整G1均结束并保存结果，使用原显式签署的120秒SQLite协议；本次最少约22.76秒余量。计时含被动监测，单次测量不能证明稳定性或因果提速，原30秒未通过。证据见 [完整回执与热点表](evidence/cloud-cold-deadline-20261030/README.md)。该SQLite合同不能移植为PG放宽。Windows新原生库、PG真实链、自然语义和owner签收分别验收，不由设置成功推断通过。
