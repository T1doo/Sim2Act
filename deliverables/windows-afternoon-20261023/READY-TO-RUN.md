# Windows：下载、解压、双击

这次交付修正了“要用户自己装环境”的问题：**运行时和所需依赖已经在云端装进同一个 ZIP**。用户无需安装 Python、pip、Node、SDK、编译器或数据库。今天不执行本目录旧 `PORTABLE-312.md` / `WINDOWS-AFTERNOON.md` 的手工环境步骤，它们只保留准备记录。

仍须准确区分：这是可独立启动的 **SQLite 合成工程预览**，不是全部生产功能已完成。原 `synthetic-workspace` 明示公开测试身份、无真实模型/正式发布/生产账户；PostgreSQL 驱动没有打入这个预览。未改生产来源、授权或期限门。

## 固定包

`Sim2Act-preview-win64-7794748c.zip`，**18,974,609 字节**。

SHA256：`05933fea0ab45831dc0a5e28165979ba2aa718a3a0000f18fc22551a9e592f0c`。

产品源码：`7794748c78041682c82f0e7fda239d2601dc91b5`。新打包器/桌面启动器在本交接提交内单独冻结；包内原 app wheel 不变，SHA256 `29c344e4d5931a2b8c9a97fb1d1ae222356bbbd6a2b58a928f960fb443f0aad5`。最终回复给出不可变下载链接，不能仅信分支 URL。

1722 个文件，解压 49,568,956 字节；包内 manifest SHA256 `2d655d1b86e48a4e62bc23d58e8180328f53169d57a50440d8fc19e300252efa`。包含 CPython3.12.10 Windows x64、21 个锁定运行 wheel、原前端和服务。原 Python LICENSE.txt、依赖 dist-info/许可证保留，源地址/原文件摘要见 `THIRD-PARTY-SOURCES.json`。没有下载器、安装器、更新器、pip 或私密配置。

Python3.12.10 已被更新版本替代，本包仅做本次短时隔离合成验收，不部署长期生产服务。[Python 官方 embedded 文档](https://docs.python.org/3.12/using/windows.html#the-embeddable-package)支持随应用私有提供运行时及依赖；保留[官方许可](https://docs.python.org/3.12/license.html)及内置软件声明。系统原有 Universal C Runtime / Edge 仍是操作系统/浏览器条件，不偷偷安装；缺DLL或签名/SmartScreen/安全策略拒绝即停，不绕过。

## 唯一电脑任务执行（云端尚未执行）

仅由 `01a1673b-54ea-75a3-b515-03d6282e4028` 操作电脑。本任务未触碰用户电脑。

1. 在 `E:\temp\codex-win-tests-20261023-1329-01a14dbf\sim2act-portable-7794748c` 新子目录下载并核上列 hash；目标不存在、祖先非 junction/reparse point。使用 Windows 自带解压，将整个 `Sim2Act-preview` 文件夹保留在该子目录。**不要安装/使用电脑上的 Python3.14，不运行旧 Setup/CI 脚本，不设 GITHUB_ACTIONS。**
2. 核系统已存在 Edge、`ucrtbase.dll` 和包内官方 python.exe 的 Authenticode；有安全拒绝即停止。双击 `Sim2Act-preview\Start-Sim2Act.cmd`。脚本直接使用包内解释器，首次新建 `workspace data`，下次继续同目录；原 API/Worker READY 后才打开既有 Edge 的独立本目录 profile/cache。控制台实际 URL 只允许 `127.0.0.1` 临时端口，保留原 CSP/沙箱/认证。
3. 原生页面公开测试登录 `public-synthetic-blank-workspace`。建一个合成项目，保存并明确授权下面 CSV。在“应用草案预览 → 直接创建 CSV 固定模板草案”选择该材料，明确创建授权，选 `amount` 核预览 **30 / 2 条**。不发送自然目标模型任务。

   ```csv
   item,amount
   A,10
   B,20
   ```

4. 仅在原内部工程流程明确确认快照/核查后保存一个内部 Release，创建一个实例，明确选择 `amount`，**只提交一个持久 AppRun**。按原读取核 SUCCEEDED / v1 / 30；UNKNOWN 不重复发 POST。内部 Release 不等于正式发布。任一步失败保留原错误，不改数据库或补假证据。
5. 控制台 Ctrl+C 一次，原服务正常退出，核 `SYNTHETIC_WORKSPACE_STOPPED` 的 `worker_stopped:true / clean:true / data_preserved:true`。按提示回车关闭控制台并关闭测试 Edge 窗口。再次双击相同 CMD，用同目录核原项目/实例/Run/v1/30仍在，不自动新建 Run。再 Ctrl+C 正常退出。
6. 最多4张真实截图：宽屏结果、键盘Tab焦点、390 CSS px稳定viewport、冷重开原Run。390仅响应式模拟，不是Android/真机。原生启动/Ctrl+C/冷重开/像素只有这次实测才可签，不由云端单测追认。

不要求 Git、pytest、Node、.NET、MSVC 或其他开发工具。预计下载解压2–5分钟，功能10–15分钟，清理1分钟；目录程序约50MB，浏览器缓存另计，整目录按500MiB监测预算，超限停追加工作，不冒充原生硬配额。下载/安全拒绝不换源、不扩权限；不无限重复测试。

## 数据与退出清理

启动器只设置自己的进程环境；app数据、TEMP/TMP、Edge profile/cache在上述新子目录。不改PATH/注册表/默认浏览器/系统服务/计划任务/防火墙，不开启模型或读取用户模型配置。所有后端业务安全门保持原实现。单实例claim防误开；异常后未知存活保留claim，不删锁或强杀未知PID。

应用可约束自有文件，不能保证Windows事件/Prefetch/Defender/崩溃转储等系统痕迹绝对无目录外写入。不得因此关闭安全服务或清系统痕迹。用户若要求系统层绝对零外写，本包无法承诺，须在运行前明确。

先由父级既有通道回收非敏感结果/截图，核本次自有API/Worker/Edge终态，再删**唯一** `...\sim2act-portable-7794748c` 子目录。不删 E:\temp、父级根或其他项目。文件仍锁定如实报剩余，不提升ACL/管理员、不按进程名杀用户浏览器，不能追认清理PASS。

## 已验证与未验证

云端完成：锁定输入hash/依赖来源核查、ZIP逐文件manifest、原wheel/前端字节保留、无PG driver依赖启动检查、12项定向测试（0.61秒）、静态代码独审。初次测试10PASS/1FAIL是断言误将SQLAlchemy自带PG方言文件当成外部driver，已收窄到包路径；没有产品失败被隐藏。

**Windows二进制尚未运行。** 此包不是Python系统安装/venv验收，不是生产PG/可信账户/真实模型/G0/P-A/P-B/整体R0通过；成品交付缺口中，这次仅补“免用户装开发环境”的实际可运行预览和用户实机首次体验。仍需后续独立完成真实生产产品门。
