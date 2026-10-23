# 已有 Python 3.14 的电脑：最小应用私有 3.12 方案

> 已被用户“下载直接用”的要求取代。以下仅保留云端准备/输入来源记录，**不要在用户电脑执行这些手工装配步骤**。今天唯一执行入口为 [READY-TO-RUN.md](READY-TO-RUN.md) 中已云端装配的离线 ZIP。

适用当前已核条件：Python3.14.6、Edge155、普通 PowerShell；不要求 pytest、Node、.NET SDK、Windows SDK、MSVC、CMake 或系统 Python3.12。**本方案未在用户电脑执行；需父级先决定是否接受新的应用私有运行时及下列开源条款，不能默认全局安装/新许可。** 唯一电脑任务仍为 `01a1673b-54ea-75a3-b515-03d6282e4028`。

## 官方来源和范围

使用 [Python 官方 3.12.10 64位 embeddable ZIP](https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip)，11133606 字节，SHA256 `4acbed6dd1c744b0376e3b1cf57ce906f9dc9e95e68824584c8099a63025a3c3`。云端已下载一次并与[官方 release 页](https://www.python.org/downloads/release/python-31210/) MD5 对应，再计算此 SHA256；不是另行声称已验证 Sigstore。3.12.10 不是当前最新安全修复版，只作为与原 Windows 锁/CI 同系列的短时隔离合成验收，不部署长期服务。

[官方 embedded 文档](https://docs.python.org/3.12/using/windows.html#the-embeddable-package)支持应用私有解释器和随应用提供第三方包；该版本不带 pip，不应把它当普通安装用 pip 管理。故在 E 盘直接展开解释器及锁定 Windows wheels，不运行安装器/ensurepip/get-pip/venv，不改注册表、文件关联、PATH 或已有3.14；3.14仅运行标准库 zipfile 解包。

[PSF-2.0及内置软件声明](https://docs.python.org/3.12/license.html)包含免版税的使用/分发许可及保留版权、许可与修改说明条件；原 ZIP 的 LICENSE.txt 全保留。23 个依赖就是现有锁内运行闭包（不含测试/开发工具），每个官方 PyPI 直链、SHA256、版本及元数据许可见 `portable-inputs.json`；源码包地址仅列官方实际提供的项目，`psycopg-binary` 的该列表为空，不补造对应源码链接。保留所有 wheel 的 `.dist-info`/licenses/RECORD 和内置 LGPL/MIT/BSD 等声明，不删除/改写，不伪称全部PSF许可。此处是来源及条款交接，不是整体合规签收；不接受这些条件时不执行新运行时。

已静态核对 23 个 wheel 的 SHA256 与官方 PyPI JSON一致、28项Windows/CPython3.12依赖关系闭合、无路径穿越或symlink项；唯一`.data`是greenlet头文件，不涉及运行数据搬移。下载共约 **23.71 MB**（Python11.13MB、23 wheels10.22MB、产品ZIP2.36MB），wheels解包36.98MB，程序/下载预计 **100–200 MiB**。Edge私有profile/cache需另计，建议整个子目录按 **500 MiB监测预算**，超额停追加操作；不是原生硬配额或精确峰值保证。预计下载/准备3–8分钟，功能10–15分钟，清理1分钟；网络慢则不反复重试。

## 精确 E 盘私有目录

只在父级已建根 `E:\temp\codex-win-tests-20261023-1329-01a14dbf` 的新子目录 `sim2act-7794748c`。先核父目录/祖先没有junction/reparse point，子目录不存在。创建其 `downloads`、`runtime`、`temp`、`edge-profile`、`edge-cache`、`evidence`；本次 shell 的 TEMP/TMP/PIP_CACHE_DIR 也指向此子目录，PYTHONPATH置空、模型token置空、LIVE=false。不改永久环境。设 `$Python314` 为已核现有3.14 exe的绝对路径，不能猜路径或触发launcher自动安装。

先只创建上述全新子目录及其 downloads/runtime/temp/edge-profile/edge-cache/evidence，TEMP/TMP 指向其中 temp（按主文档仅改本次shell）；若子目录已存在，停止而非覆盖。父级随后将本目录精确提交版 `portable-inputs.json` 和产品ZIP下载到该子目录，核最终交接提供的manifest hash及ZIP hash。以下 `$M` 必须来自核过hash的manifest，不接受用户任意JSON。目标机器不依赖pip：

```powershell
$ErrorActionPreference = 'Stop'
$Run = 'E:\temp\codex-win-tests-20261023-1329-01a14dbf\sim2act-7794748c'
if ((Get-FileHash -LiteralPath (Join-Path $Run 'portable-inputs.json') -Algorithm SHA256).Hash -ne '026c86d94d0081f3044c87b46cc96f0d247151cc4471496b990892446e84a5cc') { throw 'Portable manifest mismatch' }
$M = Get-Content (Join-Path $Run 'portable-inputs.json') -Raw | ConvertFrom-Json
$DL = Join-Path $Run 'downloads'
$Runtime = Join-Path $Run 'runtime'
$Site = Join-Path $Runtime 'Lib\site-packages'
New-Item -ItemType Directory -Path $Site -Force | Out-Null
# 下载只限manifest固定官方host，一次请求；任何拒绝或hash不符即停，不换源。
foreach ($A in (@($M.python) + @($M.wheels))) {
  $U = [Uri]$A.url
  if ($U.Scheme -ne 'https' -or $U.Host -notin @('www.python.org','files.pythonhosted.org')) { throw 'Unapproved asset host' }
  if ($A.filename -notmatch '^[A-Za-z0-9_.-]+$') { throw 'Invalid frozen filename' }
  $Dest = Join-Path $DL $A.filename
  if (Test-Path -LiteralPath $Dest) { throw 'Do not reuse partial/old asset' }
  Invoke-WebRequest -Uri $A.url -OutFile $Dest -UseBasicParsing -MaximumRedirection 0 -TimeoutSec 30
  if ((Get-Item -LiteralPath $Dest).Length -ne $A.bytes -or (Get-FileHash -LiteralPath $Dest -Algorithm SHA256).Hash -ne $A.sha256) { throw 'Asset mismatch; stop' }
}
& $Python314 -I -S -B -m zipfile -e (Join-Path $DL $M.python.filename) $Runtime
if ($LASTEXITCODE -ne 0) { throw 'Private interpreter extraction failed' }
foreach ($W in $M.wheels) {
  & $Python314 -I -S -B -m zipfile -e (Join-Path $DL $W.filename) $Site
  if ($LASTEXITCODE -ne 0) { throw 'Frozen wheel extraction failed' }
}
$App = Join-Path $Run 'app'
if ((Get-FileHash -LiteralPath (Join-Path $Run 'candidate.zip') -Algorithm SHA256).Hash -ne 'c7754eee09759e157ceb39a6898ba63f33533191fcd54a721aa4532d6a5e906b') { throw 'App archive mismatch' }
& $Python314 -I -S -B -m zipfile -e (Join-Path $Run 'candidate.zip') $App
if ($LASTEXITCODE -ne 0) { throw 'App extraction failed' }
$AppWheel = Join-Path $App 'Sim2Act-local-candidate\wheels\sim2act-0.1.0-py3-none-any.whl'
if ((Get-FileHash -LiteralPath $AppWheel -Algorithm SHA256).Hash -ne '29c344e4d5931a2b8c9a97fb1d1ae222356bbbd6a2b58a928f960fb443f0aad5') { throw 'App wheel mismatch' }
& $Python314 -I -S -B -m zipfile -e $AppWheel $Site
if ($LASTEXITCODE -ne 0) { throw 'App wheel extraction failed' }
[IO.File]::WriteAllText((Join-Path $Runtime 'python312._pth'), "python312.zip`n.`nLib\site-packages`nimport site`n", [Text.Encoding]::ASCII)
[IO.File]::WriteAllText((Join-Path $Runtime 'LOCAL-CHANGES.txt'), 'Only python312._pth adds private Lib/site-packages. Python binaries and vendored wheels are unmodified; original license notices retained.', [Text.Encoding]::ASCII)
```

此解包程序不会执行下载代码。正式启动前应核官方 python.exe 的 Authenticode 状态及系统原有 `ucrtbase.dll`；官方embedded不提供Universal C Runtime。缺DLL、签名/SmartScreen/安全策略阻止则停，不装VC redistributable、不Unblock-File、不改安全权限或点“仍要运行”。不使用新增外部DLL源。

```powershell
$Py = Join-Path $Runtime 'python.exe'
& $Py -I -B -c 'import sys,struct,sim2act,fastapi,uvicorn,sqlalchemy,pydantic,httpx,psutil,psycopg; assert sys.version_info[:2]==(3,12) and struct.calcsize(chr(80))==8; print(sys.version.split()[0]); print(sim2act.__file__)'
if ($LASTEXITCODE -ne 0) { throw 'Private runtime import failed; no fallback' }
# 路径必须在本 Run\runtime\Lib\site-packages，不是现有3.14或源码。
& $Py -I -B -m sim2act.cli synthetic-workspace --new --data-dir (Join-Path $Run 'workspace data')
```

按 `WINDOWS-AFTERNOON.md` 只做一个CSV=30/2、一个内部AppRun/v1、Ctrl+C clean、原目录冷重开与最多4张原生页面截图。重开去掉`--new`，继续同一个私有 `$Py`。这项是**便携嵌入运行时验收**，不能冒称venv/pip系统安装通过。Edge155使用本Run私有profile/cache；原生系统日志/Defender/浏览器后台可能写E盘外，不能保证绝对零外部痕迹，父级仍须先界定；不清系统痕迹。

完成后按既有步骤确认自有API/Worker及测试Edge窗口退出，先通过父级通道回收允许的证据，再删唯一 `...\sim2act-7794748c`；不删除父级根中其他项目。任何锁/清理失败只报告，不提权、不杀未知PID。云端仅准备来源/包/静态校验，没有运行Windows、签署新许可或操作用户电脑；以唯一电脑任务实测为准。
