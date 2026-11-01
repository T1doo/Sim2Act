# 内部Linux限制候选：桌面生命周期修复源码

精确应用源码：`7bf6fd84fd694efe8348e1b565b01ad2e0765c40`。

文件：`Sim2Act-local-candidate-7bf6fd84fd69.zip`，**3,566,239字节**。

SHA256：`6c803b44ba2222df43ee055b0251ae47267ef75e6cd4ec3a91fa04dd2b7954cb`。

wheel：`sim2act-0.1.0-cp312-cp312-linux_x86_64.whl`，SHA256 `d381ea157928379ab965a77f41895ff9ed6f4bd4113760fa108a1dd85aceb8df`。包中源码与指南按manifest核对，未放入数据库、`.env`或模型令牌；四枚原生扩展已在隔离安装中实际加载。本轮没有联网下载依赖。

本候选适用已有锁定依赖的Linux x86_64／CPython3.12环境。解压后按`docs/LimitedTextCandidate.md`执行离线应用安装，以`python -m sim2act.cli synthetic-workspace --new --data-dir "新的绝对路径"`启动；看到真实READY才打开服务URL。当前实测CSV=30/v1、同键不重放、正常停止、首次进程重开同结果。有限文本live须显式选择并复用已有令牌，本轮没有新增真实模型请求。

停止使用原CLI的Ctrl+C并等待STOPPED/clean和实际退出。卸载用安装它的同一个隔离Python环境执行`python -m pip uninstall sim2act`，只移应用，保留工程、结果、控制库和共享依赖；需要清理解压目录／隔离环境时先确认进程已退出且没有混入其他文件。原工程不自动删除，未知锁和进程不得为了重试而删除或强杀。实际卸载后三份工程文件摘要未变化。

包含新版Windows宿主源码和固定构建脚本，但本包是Linuxwheel，**没有当前Windows EXE，也不是Windows下载即用包**。不能拿Linux包替代同源Windows wheel及四扩展的实编、窗口和重开验收。新版Windows所缺动作与当前测试／性能范围见[证据](../../docs/evidence/desktop-startup-lifecycle-20261101/README.md)。旧5db／5af候选保留，本候选不覆盖原包，不发布Release。
