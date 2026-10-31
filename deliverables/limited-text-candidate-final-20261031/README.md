# 最终限制候选（Linux）

[下载候选ZIP](Sim2Act-local-candidate-1a23c032fdc5.zip)，**3,187,872字节**。

- 源码：`1a23c032fdc5ac83b4caf3ba07ed06f8a9d7669e`，应用开发版本0.1.0。
- ZIP SHA256：`b63d954d892023adafbdf062130ca23c5261cae38f6c108972c18988246f194e`。
- wheel SHA256：`7133424e80ae46513c046c393db30a66f4c1f85d5443192fbfb8e8dd4ba7fed2`。
- 平台：CPython3.12／Linux x86_64，四个原生扩展；不是Windows EXE或正式Release。

解压后读 `docs/LimitedTextCandidate.md`：在已有锁定运行依赖环境安装包内wheel，再运行 `python -m sim2act.cli synthetic-workspace --new --data-dir "新的绝对目录"`。显式增加 `--exact-read-live` 才启用单文本合同，使用进程已有令牌别名；包内不含令牌、数据库、运行时或依赖wheelhouse，不自动联网安装。

本精确包已新安装、从源码目录外启动：默认自由目标明确拒绝，正常Ctrl+C停止／首次重开保留；direct.v2单文本目标用同一前次失败文本，2次真实Intern、1739 tokens、6.391秒后独立核对并保存为SUCCEEDED，首次新进程同结果、原键无重放，两次exit0／双EOF。旧超时UNKNOWN、旧成功和格式失败原件完整保留。[全部证据、版本化测试范围与限制](../../docs/evidence/finite-lease-and-installed-v2-20261031/README.md)。

包内也含旧SQLite30秒结算／续租提交尾检修复，保留更窄state截止及原120秒合同。正确拒绝过期提交不等于解决性能：大图30秒目标仍不稳定，正式PG／大型Cold live／新版Windows未验。通用语义仍NOT_RUN、人工确认PENDING；此包只交付声明的有限目标及默认本地生命周期。
