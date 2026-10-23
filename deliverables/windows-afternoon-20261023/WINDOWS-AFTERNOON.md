# 今日 Windows 最小交付验收交接

> 已被用户“下载直接用”的要求取代。以下为旧开发安装方案的保全记录，**不要在用户电脑执行安装命令**。今天只按 [READY-TO-RUN.md](READY-TO-RUN.md) 解压成品预览并双击；不需用户 Python、pip、SDK 或编译器。

**实机条件更新：已知只有 Python 3.14.6，未证实 3.12。本文件的现有 3.12 + venv 安装路径当前不能直接执行。** 改用先交父级决定的 [官方免安装 3.12 便携方案](PORTABLE-312.md)，不偷偷安装系统运行时。测试项和清理边界仍按下文。

电脑唯一执行任务：`01a1673b-54ea-75a3-b515-03d6282e4028`。本云端任务不操作用户电脑。仅安排一条尚缺的**用户实际 Windows 上安装 wheel、原生页面首次使用和原目录冷重开**；不重复 Server 2025 CI、大套件、Source 回读、G0 或长 `prepare-pa` 演示。

## 冻结包与来源

- 产品源码：`7794748c78041682c82f0e7fda239d2601dc91b5`。包 181 条目 / manifest 180 文件；178 个源码/配置与 Git 同源，wheel 158 成员核对，含当前网页及 `synthetic_workspace`，没有应用原生二进制。
- ZIP：`Sim2Act-local-candidate-7794748c7804.zip`，**2357007 字节**；SHA256 **`c7754eee09759e157ceb39a6898ba63f33533191fcd54a721aa4532d6a5e906b`**。
- ZIP 内 wheel：`wheels/sim2act-0.1.0-py3-none-any.whl`；SHA256 **`29c344e4d5931a2b8c9a97fb1d1ae222356bbbd6a2b58a928f960fb443f0aad5`**。
- 直接下载（下载后必须核上述 hash）：`https://raw.githubusercontent.com/T1doo/Sim2Act/dev/production-trial-stages-20261018/deliverables/windows-afternoon-20261023/Sim2Act-local-candidate-7794748c7804.zip`。本交接最终回复另给不可变提交链接；不能仅信浮动分支 URL。
- 源对应入口：`https://github.com/T1doo/Sim2Act/tree/7794748c78041682c82f0e7fda239d2601dc91b5/src/sim2act`；本目录 `candidate-manifest.json`、`package-verification.json` 为逐项校验依据。

构建和包独审已完成，**本新包尚未执行 Windows 安装**。既有包内 LocalCandidate/Installation 文档含其他历史流程，本次以本文限定命令为准，不运行旧 PG 安装或长自然生成演示。

## 先核既有条件，不代装系统软件

记录真实 Windows 版本/架构；只有实际 Win11 才能认 Win11。需现有 **CPython 3.12 x64（明确现有 exe 绝对路径）**、普通 PowerShell（5.1 即可）、已安装且签名有效的 Microsoft Edge。不要用可能自动下载运行时的 launcher 代替明确 Python 路径。无需 Git、Node、Playwright、PowerShell 7、PostgreSQL、Docker/WSL、C 编译器或 SDK。

项目依赖仍须来自既有受信任 wheelhouse 或正常获准的 Python 包源，按包内 `requirements-windows.lock` 安装二进制版本。缺 wheel/解释器/浏览器、下载拒绝、签名或执行策略拒绝即停止此部分，不尝试源码编译、替代镜像、新 SDK/许可证、管理员、ExecutionPolicy Bypass、TLS/Defender/沙箱例外。依赖安装限 10 分钟，功能验收限 15 分钟，正常清理预留 1 分钟；首次网络不慢时总计约 15–25 分钟。建议 E 盘可用 **1 GiB**；预计项目实际峰值约 300–700 MiB，需实测，超过 1 GiB 停止扩张并清理自有项。

## 目录与缓存约束

仅新建 `E:\temp\Sim2Act-7794748c`，先确认它不存在，且 E:\temp/祖先不是 reparse point/junction。所有下载、解包、venv、SQLite、日志、截图、pip/TEMP/TMP、浏览器 profile/cache 在其内部。只对本次 shell 设置环境，不改用户/系统环境、注册表、PATH 或配置文件：

```powershell
$Run = 'E:\temp\Sim2Act-7794748c'
if (Test-Path -LiteralPath $Run) { throw 'Already exists; do not overwrite or reuse' }
New-Item -ItemType Directory -Path $Run | Out-Null
foreach ($Name in @('temp','pip-cache','edge-profile','edge-cache','evidence')) {
  New-Item -ItemType Directory -Path (Join-Path $Run $Name) | Out-Null
}
$env:TEMP = Join-Path $Run 'temp'
$env:TMP = $env:TEMP
$env:PIP_CACHE_DIR = Join-Path $Run 'pip-cache'
$env:PIP_DISABLE_PIP_VERSION_CHECK = '1'
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:PYTHONNOUSERSITE = '1'
$env:PYTHONPATH = ''
$env:SIM2ACT_MODEL_MODE = 'mock'
$env:SIM2ACT_LIVE_ENABLED = 'false'
$env:SIM2ACT_MODEL = 'intern-s2'
$env:SIM2ACT_INTERN_TOKEN = ''
$env:INTERN_API_TOKEN = ''
$env:SIM2ACT_DATABASE_URL = ''
Set-Location $Run
```

**不能默认承诺零目录外副作用：** Windows 事件/Prefetch/Defender、崩溃转储及 Edge 后台组件可能由系统自行写入其他目录。测试本身不配置或清除这些，不禁用安全服务、不安装更新器、不改默认浏览器或关联、不建服务/计划任务/防火墙规则。若父级对用户授权的解释是“系统也绝对不能在 E:\temp 外写任何痕迹”，本方案不能保证，启动前应停止而非隐瞒该限制。

## 安装和启动（电脑任务执行，云端未执行）

将 `$Python` 设置为刚核过的现有 Python 3.12 x64 exe；不要在脚本中猜路径或自动安装。下载 ZIP 到 `$Run\candidate.zip`，核 hash 后解压，再安装 venv 内的依赖及 wheel。以下 pip 网络参数不允许重试；若现有网络/包源被拒绝，不换源绕过。没有启用任何系统级安装：

```powershell
$Zip = Join-Path $Run 'candidate.zip'
$Download = 'https://raw.githubusercontent.com/T1doo/Sim2Act/dev/production-trial-stages-20261018/deliverables/windows-afternoon-20261023/Sim2Act-local-candidate-7794748c7804.zip'
Invoke-WebRequest -Uri $Download -OutFile $Zip -UseBasicParsing
# 下载到 $Zip 后先核；不使用用户 Downloads 或其他项目缓存。
if ((Get-FileHash -LiteralPath $Zip -Algorithm SHA256).Hash -ne 'c7754eee09759e157ceb39a6898ba63f33533191fcd54a721aa4532d6a5e906b') { throw 'ZIP hash mismatch' }
Expand-Archive -LiteralPath $Zip -DestinationPath (Join-Path $Run 'pkg')
$Pkg = Join-Path $Run 'pkg\Sim2Act-local-candidate'
& $Python -c 'import sys,struct; assert sys.version_info[:2]==(3,12) and struct.calcsize(chr(80))==8; print(sys.version.split()[0])'
if ($LASTEXITCODE -ne 0) { throw 'Existing interpreter is not CPython 3.12 x64' }
$Machine = & $Python -c 'import platform; print(platform.machine())'
if ($Machine -notin @('AMD64','x86_64')) { throw 'Existing interpreter is not x64' }
& $Python -m venv (Join-Path $Run 'venv')
if ($LASTEXITCODE -ne 0) { throw 'venv failed' }
$Py = Join-Path $Run 'venv\Scripts\python.exe'
& $Py -m pip install --no-deps --only-binary=:all: --no-cache-dir --retries 0 --timeout 30 -r (Join-Path $Pkg 'requirements-windows.lock')
if ($LASTEXITCODE -ne 0) { throw 'Pinned Windows wheel dependency install failed; no fallback' }
$Wheel = Join-Path $Pkg 'wheels\sim2act-0.1.0-py3-none-any.whl'
if ((Get-FileHash -LiteralPath $Wheel -Algorithm SHA256).Hash -ne '29c344e4d5931a2b8c9a97fb1d1ae222356bbbd6a2b58a928f960fb443f0aad5') { throw 'Wheel hash mismatch' }
& $Py -m pip install --no-deps --no-index $Wheel
if ($LASTEXITCODE -ne 0) { throw 'App wheel install failed' }
& $Py -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Dependency mismatch' }
& $Py -c 'import sim2act; print(sim2act.__file__)'
# 输出必须在本 Run\venv\Lib\site-packages，不能从源码/import path 偷跑。
& $Py -m sim2act.cli synthetic-workspace --new --data-dir (Join-Path $Run 'workspace data')
```

用现有 Edge 打开 READY 输出的实际 loopback URL；不要猜固定端口或处理占用端口的他人进程。只开独立本次 profile，并保留沙箱/CSP/TLS：已有 Edge 的启动参数为 `--user-data-dir=E:\temp\Sim2Act-7794748c\edge-profile --disk-cache-dir=E:\temp\Sim2Act-7794748c\edge-cache --no-first-run --no-default-browser-check <实际URL>`。不要复用用户日常 profile、登录同步或默认浏览器会话；记录本次自有窗口/进程身份，不按进程名批量结束 Edge。

## 只做这组验收

1. READY 后公开合成登录 `public-synthetic-blank-workspace`。确认新工程无项目，在精炼后的低频创建入口建一个项目；到资源粘贴 `item,amount\nA,10\nB,20\n`（真实换行），保存并明确授权。到“应用草案预览 → 直接创建 CSV 固定模板草案”，填写名称/目标，选该材料，明确创建并授权；选 `amount` 跑一次预览，核 **30 / 2 条**。不去自然目标任务框发模型任务。
2. 在内部工程入口核查快照、勾选原确认后保存一个内部 Release，创建一个独立实例，再次明确选 `amount`，只提交 **1 个持久 AppRun**。按原刷新读到 SUCCEEDED / v1 / 30；UNKNOWN 不重复 POST。这是内部版本，formal publication 仍关闭，owner/语义状态保留原值。
3. 截图最多 4 张：真实宽屏任务/结果、键盘 Tab 焦点、窄 viewport 稳定布局、冷重开同原 Run。可用 Edge DevTools 390 CSS px 响应式 viewport，但必须标为模拟 viewport，不是手机/Android 真机。记录真实窗口/viewport；确认无横向遮挡、焦点可见、当前项目/授权说明和只读状态未删。不重复全部工作区 CI。
4. 完成当前操作后 Ctrl+C，等控制台 `SYNTHETIC_WORKSPACE_STOPPED` 且 `worker_stopped:true / clean:true / data_preserved:true`。不 `--new`，重新执行 `& $Py -m sim2act.cli synthetic-workspace --data-dir (Join-Path $Run 'workspace data')`。页面重新输入公开 token，核原项目/实例/原 Run/v1/30 存在且没有自动创建新 Run。最后再次 Ctrl+C 等 clean。只在该入口启动合成 Worker，不启动系统服务。

任一步失败保留失败阶段与屏幕，停止追加操作；不盲重跑、不改数据库/marker、不延租约、不删未知锁。不运行 `Setup/Start/Doctor/Windows*CI.ps1`，它们有不同 PG/CI 前提，不能伪造 GITHUB_ACTIONS 环境绕过。

## 退出、取证与清理

电脑任务负责先把允许的非敏感结果/截图传回父级（或云端归档），不把 E 盘“留作证据”拖过今天下午。记录实际 OS/Python/Edge版本、安装路径、包 hash、RunID/result、两次 clean 回执、实际峰值和端口/进程终态。没有授权结果上传目的地就先由父级现有通道回收，不外发到新服务。

仅在自有 API/Worker 正常退出、独立 Edge 测试窗口关闭、安装器已结束后，父级持有的精确自有句柄核对退出。不要清用户浏览历史、全局 pip 缓存或系统日志，不停止用户其他浏览器。恢复/关闭本次临时 shell 后，从 Run 外删除唯一新建的 `E:\temp\Sim2Act-7794748c`；只删这个精确路径，不删 E:\temp 或其他项目。删除失败（例如 profile 文件仍锁定）停止并报告精确剩余项，不能通过改 ACL/管理员/杀未知 PID 解决；不能声称清理通过。

本项只补实际 Windows 的隔离安装/固定 CSV 原生体验/持久化/冷重开缺口。它不替代普通 PG 应用角色 Setup、真实模型/自然语义、P-A/P-B、G0、Android 或整个 R0 验收。缺既有 Python/Edge 或无法遵守路径/副作用边界时，此项为 BLOCKED，父级可继续其他项目，不现场铺新平台。
