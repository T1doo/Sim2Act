# 安装包空白合成工程：有限交付证据

从本地基线 `c861d92dbb91dfd8d3b9b7ed56015340758a9565` 接续。[原方案依据与实际范围](../../F2/BlankSyntheticWorkspace20261018.md)；[可操作上手入口](../../F2/BlankSyntheticWorkspaceQuickstart.md)。本片补安装包的空白、可保留重开合成工程入口；不关闭完整F2-T07、Windows/原生安装或产品语义验收。

## 资格与原件

| 窗口 | 实际结果 | 原始证据 |
| --- | --- | --- |
| 最终有限边界 | 8 PASS / 5.33秒，外层8.028秒，1条原警告；源码前后不变 | [命令](raw/final-boundary-command.json)、[stdout](raw/final-boundary.stdout) |
| wheel构建/安装 | 940289字节，SHA256 `3f0224488c4f7f710fb2136afe1a36ad5e55a3d3462631e15f9053e43f26b6d0`；146构建输入前后相等，139包文件与安装字节全等 | [构建](raw/wheel-build-command.json)、[安装来源](raw/installed-path-probe.json)、[包文件hash](raw/installed-wheel-files.json) |
| 第一完整runner | **FAIL**：安装/checkout外来源/空库/首页安全头已通过；页面第二脚本逐eval词法环境不共享，`$ is not defined`；尚未连接或建业务 | [完整结果](raw/first-full-runner-FAIL.json)、[页面失败](raw/first-boot-FAIL.json) |
| 第二完整runner | **FAIL**：同wheel新空目录的完整新建页面13检查PASS，102请求=92GET+10POST，实际后台结果30/v1；随后外层误将core Run ID当内部AppRun ID，StopIteration | [完整FAIL](raw/second-full-runner-FAIL.json)、[真实页面PASS](raw/new-page-PASS.json) |
| 同库纯解析＋冷开 | **PASS**：修正关联原不可变binding，不重放新建；新进程同identity，冷页9检查/46全GET，原Run结果30；55表仅heartbeats变化、另外54表相等 | [continuation](raw/same-fixture-cold-continuation-PASS.json)、[冷页](raw/cold-page-PASS.json) |

独立venv以`--no-index --no-deps`安装wheel，显式引用既有锁定依赖目录；未重新下载运行依赖。构建隔离只访问显式公开PyPI安装锁定setuptools。JSDOM通过真实loopback HTTP加载已安装包139文件中的原页面JS，使用原事件；不是原生浏览器/视觉资格。Worker是启动器持有的同一真实服务进程内线程，原Worker/租约/账本未替换。

冷页46个GET实际为45个200、1个400：可选`/protocol/contracts`返回`RESOURCE_UNAVAILABLE / Evaluation asset unavailable`。本轮交付的CSV同Run正向链未受影响；该可选评价能力未随安装包获得资格，不能把“全GET”写成“全部HTTP成功”。

成功core Run `run_4d9148440a58446fbb430c02905eccee` 与内部AppRun `iapprun_3313632374a14e499933f80d7ed1fe65` 由唯一immutable binding关联，同实例 `iinstance_5a2d62a7c941efa6904db33875f38ad9`；成功任务实际CLAIMED一次/fence1。完整工程另有一个被明确禁用的模型任务，合计2次CLAIMED、1个FAILED MOCK Attempt/UNSUPPORTED_CAPABILITY（usage unknown/null，保留原reservation和账本）。真实模型/provider请求0，固定CSV成功任务模型Attempt0。首Worker `worker_a884fcd8c28b44668428b259f3d57435`、冷Worker `worker_46bf64f6b45e45c1a84e4620fe6f572d` 分开核对；各自Ctrl+C clean、数据保留、已停止首心跳不变。

**修正后的全新完整runner NOT_RERUN**。不把两个外层FAIL改写成全程绿，不累加首轮4PASS和修复中8PASS；本轮没有新的恢复故障矩阵。第一修前wheel另行保留且未启动。

## 封存

[作者完整原件](author-originals.tar.gz)：9492853字节，SHA256 `749ef698b232051bdcf302a57fae5dadf2258e00498ca4ce50f6dba4a019a352`。内含已关闭合成DB/55表快照、所有页面请求/响应、执行前后source/driver/runner、原失败、安装包、venv与进程日志；共享运行依赖目录本身未打包。保留原绝对路径/venv symlink，只供核证，重装wheel请遵循上手说明。

[作者seal](raw/author-sealed-manifest.json)文件SHA256 `64d27c735ec69e89e9b9aca730bbf949582f9675fe924b5104d726acf96d4cc5`，1382普通文件/33866540字节，另列symlink；files投影SHA256 `7fa692d9684ec105c9b43d7a0ecab515614d4bc06d206bcc65c3a0b8f16524bc`。作者目录封存后只读；[闭合检查](raw/author-closure.json)、[9个最终交付源](raw/final-source-hashes.json)。[可读副本映射](raw-copies.json)逐份对应作者原件，未改写内容。

有限独审 **LIMITED PASS，本片未见剩余P1/P2**：[最终报告](final-independent-review.md)、[机器核验](final-verification.json)。独审只读源码/闭合原件，1368非DB文件SHA、14DB仅stat、25symlink仅readlink；不另执行产品或读取DB内容，55表比较基于作者原JSON导出。[独审全部原件](independent-originals.tar.gz)18356字节，SHA256 `c9befabef0d6b0c07f5ff892ad7b80ada557fccd782c741c4c4cd0e866fbff09`；[独审seal](independent-sealed-manifest.json)文件SHA256 `c790b4b54c1e4155990e32104bdf9cf072153295a48ac80f9d1ac87f887e36f9`，24普通原件73051字节。独审自身三次observer假设错误也保留，最终纯文件audit通过，不计作产品执行。

补充静态检查：Ruff、Node语法及diff通过；[mypy两修改源文件](raw/mypy-command.json)使用`--follow-imports=silent`通过（[stdout](raw/mypy.stdout)），不是整个仓库类型检查。该检查在作者seal后执行，原件位于delivery目录并逐字复制于此，不混入作者原seal。

未实测Windows、PG、原生浏览器/视觉、独立API/Worker进程、真实模型/语义/用户人工签收或远端CI。真实账户来源资格仍SOURCE_MISSING；旧满盘环境最终独审缺证NOT_RECOVERED。沿用已知远端访问拒绝，未进行Git/auth/network重试、push、部署或发布；当前远端HEAD未知，local remote-tracking只是旧元数据。交付精确commit SHA及相对上次acknowledged `a7403b379b1278fd1be533ca21d790f0311244af` 的本地未推送差异由提交后的delivery记录固定。
