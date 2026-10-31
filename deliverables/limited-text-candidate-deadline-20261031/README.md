# Linux限制候选：更早执行截止

完整应用源码`2ad3227621b48793a4d03747463b33207139147e`，开发版本0.1.0，非正式Release。前版2d41/1a23 ZIP保留，未覆盖。

| 文件 | 大小（B） | SHA256 |
| --- | ---: | --- |
| [Sim2Act-local-candidate-2ad3227621b4.zip](Sim2Act-local-candidate-2ad3227621b4.zip) | 3,188,692 | `6b6e42d909089ad001a6ff889976b7eff0e65ab7e4229fd95f15377b57efe81d` |
| ZIP内 `wheels/sim2act-0.1.0-cp312-cp312-linux_x86_64.whl` | 1,718,647 | `2933d54b4bf6620549a9e3963d9165433441776dcbb2132de32cd657b1f15552` |

[candidate-manifest](candidate-manifest.json)为完整库存／source_commit／构建身份，[实际核对](package-verification.json)与[完整工程／未完成范围](../../docs/evidence/cold-earliest-deadline-boundary-20261031/README.md)另列。223项包库存，4个原生扩展实际导入并核完整源hash；无数据库、真实令牌、venv或依赖wheelhouse。

本轮仅修signed120也必须受原更早state.deadline约束；不新增预算／权限或开启计划缓存。源码307、安装44项定向回归均零失败／跳过，二者重叠不相加。两笔大型Mock+SQLite在显式120合同下保存／首次重开通过，但G0为31.09/30.96秒、writer区段45.45/49.60秒、total76.54/80.56秒，较匹配基线更慢。**未解决原普通30秒大型Cold稳定性，不是全产品交付。**

仅本轮Linux x86_64／CPython3.12、已有锁定依赖环境验证，系统glibc2.41；不是Windows EXE或Windows下载即用，其他ABI和干净机器下载依赖未验。

安装和使用按解压后`docs/LimitedTextCandidate.md`：

1. 在已有依赖环境安装`python -m pip install --no-index --no-deps wheels/sim2act-0.1.0-cp312-cp312-linux_x86_64.whl`。
2. `python -m sim2act.cli synthetic-workspace --new --data-dir /绝对路径/新的合成工程`；父目录已存在，目标必须新目录。使用本次READY回环URL和公开合成登录，默认模型关闭。
3. Ctrl+C后等STOPPED/clean及exit0；同data-dir重开不加--new。普通CLI端口随机，本包Linux入口为本地服务页面，不冒充已验Windows独立窗口。
4. 卸载只在安装该包的同一Python环境用`python -m pip uninstall sim2act`；默认保留工程、导出、日志和共用依赖。先正常停止，不删未知锁。清理专用venv/解压目录前确认没有混入自己的文件，工程永久删除须先备份和明确选择。

新包实际CSV30/v1正常保存／重开／同键和四次正常关闭、专用环境卸载保留6文件／30共享METADATA已验。显式`--exact-read-live`才复用原已配置免费Intern令牌开放单文本逐字合同；本轮对旧1a真实结果仅做私有副本兼容回读，**0新真实模型调用**，不重签旧live证据。通用自然目标／正式PG／新Windows／大型live仍未验，发布与人工／语义安全门不变。
