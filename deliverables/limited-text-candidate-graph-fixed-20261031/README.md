# Linux限制候选：图错误边界修复

源码：`2d41ad38b84630cb817d87374122bce31e357d0d`，应用版本0.1.0（开发候选），不是正式Release。

| 文件 | 大小（B） | SHA256 |
| --- | --- | --- |
| [Sim2Act-local-candidate-2d41ad38b846.zip](Sim2Act-local-candidate-2d41ad38b846.zip) | 3,188,641 | `85f4302bb32cadbdf45a484de653a6ae58c54aa25361473159fbc3063dfaf592` |
| ZIP内 `wheels/sim2act-0.1.0-cp312-cp312-linux_x86_64.whl` | 1,718,624 | `49904302f774a50a56bb3d8f963d12a2570801d70b0d2a00dabf7e68c9c43c01` |

完整库存和构建身份见[candidate-manifest.json](candidate-manifest.json)，实际新安装/原生模块核对见[package-verification.json](package-verification.json)，[应用及证据说明](../../docs/evidence/graph-fixture-and-installed-cleanup-20261031/README.md)。223项包库存，不含数据库、真实令牌、venv或依赖wheelhouse；使用已有锁定依赖环境的CPython3.12、Linux x86_64，本轮系统glibc2.41。**不是Windows EXE或Windows下载即用包**，其他ABI和干净机器依赖下载未验。

解压后，按包内`docs/LimitedTextCandidate.md`在既有依赖环境安装wheel（--no-index --no-deps）；默认运行`python -m sim2act.cli synthetic-workspace --new --data-dir /绝对路径/新工程`，在本次READY回环URL登录公开合成身份。显式`--exact-read-live`才读取已配置原令牌并开放单文本逐字合同，非自由目标通用完成器。Ctrl+C等待STOPPED/clean/exit后，同目录重开不加--new。Linux是本地服务页面入口，未冒充已验独立Windows窗口。

卸载仅在安装它的同一环境执行`python -m pip uninstall sim2act`；默认保留工程、导出、日志及共用依赖。先正常退出，不删未知锁；专用venv/解压目录可在确认没有混入文件后单独移除，工程永久清理需先备份和明确选择。本轮已在专用新venv实际安装、CSV保存/重开、旧真实结果回读、正常停止及卸载验证，6个工作区文件和共享METADATA未变；没有替用户清理数据。

原12项图失败已逐项闭合（11 fixture前置合同、1解除前置后暴露的产品AttributeError，未削弱完整门）；最终源码293、实际安装59均零失败/错误/跳过，测试范围有重叠，不累加宣称全仓。有效receipt、动态撤权、期限、取消原断言保留。包内manifest的BUILT_NOT_ACCEPTED表示构建时原状态；限定验收记录独立于冻结ZIP，不修改安全状态假放行。

本轮模型新请求0；先前真实Intern成功属于1a23源码，当前仅核历史兼容，不改签为当前新执行。新版Windows、正式PG、完整大型Cold live未验。大型30秒目标不稳定及长写锁仍存，不是全产品交付，main/Release未改。
