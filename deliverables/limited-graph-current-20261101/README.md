# Linux限制候选：完整Graph当前版本读取

源码 `35eaa941f544ca016ddeeefb839178d316fc1c6b`，开发版本0.1.0，非正式Release；旧2ad包保留。

| 文件 | 大小（B） | SHA256 |
| --- | ---: | --- |
| [Sim2Act-local-candidate-35eaa941f544.zip](Sim2Act-local-candidate-35eaa941f544.zip) | 3,270,375 | `927501b0a87aee143ed152f998073be31631b4104cec642cfe697e8fdd49155b` |
| ZIP内 `wheels/sim2act-0.1.0-cp312-cp312-linux_x86_64.whl` | 1,788,586 | `e5cb821f14f26261ae6a9272608b2ce1d82abd2874ad2f82e87ebec00727f68a` |

这是实际安装并运行过的**同一枚wheel**，没有再次编译后混用旧验收。224项包库存、190个Git源码成员与四个原生扩展均核，安装内容与ZIP内wheel逐字节相同。无DB、私人配置、token或依赖wheelhouse；[完整库存](candidate-manifest.json)／[解包与秘密值扫描](package-verification.json)。

隔离venv、源码目录外启动，普通API保存CSV sum30／版本1、原键复用、正常停止、首次新进程重开及两次exit0/clean通过。已有锁定依赖通过显式测试.pth共用，不是全新机器下载依赖验收。默认模型关闭，自由目标明确拒绝；显式单文本真实模型合同沿已有接口，本轮安装验证0新真实调用。

同规模真实墙钟Mock+SQLite的两笔保存、完整G1和首次只读重开通过；较本轮276基线，snapshot总计113.804/116.194降至87.406/94.006秒。G0仍35.420/37.580秒，writer仍51.985/56.426秒；**原普通30秒仍在G0安全拒绝，不是性能整体达标**。原完整动态授权、撤权、取消和原子性保留；[源码、匹配对照、失败与实际范围](../../docs/evidence/graph-current-real-clock-20261101/README.md)。

仅Linux x86_64／CPython3.12、当前glibc2.41及已有依赖环境验证；不是Windows EXE，新Windows／正式PG／大型live／任意目标语义／人工验收与完整交付未通过。无本机操作、新Windows CI、部署或正式发布。

解压后按 `docs/LimitedTextCandidate.md`：

1. 在已有依赖环境安装 `python -m pip install --no-index --no-deps wheels/sim2act-0.1.0-cp312-cp312-linux_x86_64.whl`。
2. `python -m sim2act.cli synthetic-workspace --new --data-dir /绝对路径/新合成工程`，父目录须存在、目标须新目录。使用本次READY回环URL及公开合成身份；普通CLI端口随机，不冒充已验Windows独立窗口。
3. Ctrl+C后等待STOPPED/clean与exit0；同data-dir重开去掉 `--new`。
4. 只在该Python环境执行 `python -m pip uninstall sim2act`，默认保留工程／导出／日志及共用依赖。先正常停止，不删除未知锁；工程永久删除前自行备份并明确选择。
