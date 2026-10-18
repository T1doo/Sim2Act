# 可冷重开的空白合成工程入口

基线 `c861d92dbb91dfd8d3b9b7ed56015340758a9565`。先对照原产品 §9 与 F2-T07 核查：有限 CSV 列/材料/Goal 修订、有限 DAG 接线、自然配方前序依赖切换、人工锁和保守扩验均有实现；Report 的 decision→explanation 只是归档展示，不是可执行版本的修改。手工正文改版、更宽规则/节点、跨文件组合及 Schema 迁移尚无已冻结的通用依赖/保留合同，不能通过换一个字段、工具或忽略未知 PROJECT 依赖来补称完成。本片不继续这些小变体。

转推进原产品 §6.2、§6.5 和 F1-T02/安装运行、F3/AT-27 的交付入口代码子项。现 wheel 包含页面但没有 console entry；CLI 只有 migrate/init-user/schemas/probe。现有 first-use 是退出清理的测试，natural_activation_demo 预置固定项目，local_candidate_demo 预先生成成果且 serve 只读。它们不是从安装包开始、自己创建项目并可冷重开的空工程。

原方案依据：[F2-T07](../分阶段开发计划.md#4-f2两条生成路径与最小增量闭环) 要求稳定 ID、类型边、指纹、依赖失效、未知依赖保守重验与锁冲突；[产品 §9](../平台产品设计.md#9-交付图与增量修改) 不能因一个新字段就把通用修改计为完成。已实现的直接代码是 `csv_column_revisions.py`、`csv_goal_revisions.py`、`natural_logic_patches.py`、`delivery_graph*.py`、`manual_locks.py`、`report_presentations.py`。本片核查确认原材料 file picker 和空项目页面也已存在，不重复实现。

后备交付入口依据：[产品 §6.2—6.5](../平台产品设计.md#62-各组件在哪里运行)、[F1-T02/F3-T06/AT-27](../分阶段开发计划.md)。这里只补安装包入口及 Linux 合成工程复现代码；原方案的 Win11、独立 API/Worker 进程与 PostgreSQL 要求保留。本入口的 Worker 是启动器持有的同一真实服务进程中的线程，不据此签收这些原始要求。

## 实现前合同

- 安装包提供显式 `sim2act synthetic-workspace --new --data-dir <新目录>`；后续不加 `--new` 打开同目录。新建只做原 test-only SQLite schema、基础 quota 和公开合成身份，项目/资源/应用/Run/结果全空。不依赖 checkout、测试目录、旧包、现成数据库或作者结果。
- 复用普通 `create_app`、原 `Worker`/租约/账本与原页面；只允许127.0.0.1和有效端口，默认动态端口。Worker 使用原一秒服务节拍及拒绝模型的对象，不创建替代执行器。Settings显式mock/token空/LIVE false/生成provider disabled；不读取.env、环境凭据或DSN，不提供生产连接选项。
- 数据目录及父级不能是链接；new拒绝已有目录，失败保留已创建内容。冷开只接受精确marker、已有普通数据库文件、匹配schema和原合成身份，不自动迁移/初始化/重置已有库。不删除文件、不杀未知进程、不改ordinary PostgreSQL启动或SQLite拒绝。
- 网页明确显示合成工程范围及公开测试登录，不用于敏感材料。用户通过原页面自己建项目、保存CSV/完整Goal、选择固定能力、确认内部版本/实例并提交任务；没有预置项目/候选/成果，不激活真实自然模型。
- Ctrl+C只停止本命令持有的API/Worker并保留目录；冷开沿用同项目/身份/历史。停止不会伪装取消Run，未完成任务仍服从原租约/恢复规则。不能把本地合成入口当生产启动、独立发布、Windows或真实用户数据迁移资格。

最小实测：从当前源构建wheel并安装到独立venv（明确复用现有锁定依赖路径，不声称重新下载依赖）；在checkout外启动真实进程/loopback API，从空页经完整页面建立CSV工程、完整Goal和固定CSV应用，确认内部版本与实例，原Worker实际得到30。停止进程后检查数据保留，另启进程从安装包冷读同一Run/成果；心跳按精确Worker对象分别计量。加有限目录/marker/凭据环境隔离及普通Store拒绝SQLite检查；不重跑故障矩阵。完整命令、执行字节、HTTP、claim与原始失败分期留存。

## 实际结果与保留限制

可用入口见[上手说明](BlankSyntheticWorkspaceQuickstart.md)。最终生产代码复用原 `create_app`、`Store(test_only=True)`、`Worker`、原页面和运行账本；没有新 executor、Grant 或生产模型配置。首次只初始化55表、1个公开合成 principal 和1个基础 quota；启动后只多本命令持有 Worker 的心跳，无业务预置。冷开核对精确 marker、同身份、表/列类型/nullable/PK/unique，不迁移原目录。首页仍经过原安全 middleware。

最终有限边界测试 **8 PASS / 5.33秒**，外层8.028秒；原警告1条。包括新/冷空库、未知/链接目录保留、marker先拒绝、同列异类型/约束拒绝、`?`目录先拒绝、环境凭据/DSN隔离、普通Store继续拒绝SQLite，以及一个禁止模型任务由原Worker标失败后继续可用。首轮修前4PASS、修复中8PASS分开留存，不累加为新测试数。

安装包 `sim2act-0.1.0-py3-none-any.whl`：940289字节，SHA256 `3f0224488c4f7f710fb2136afe1a36ad5e55a3d3462631e15f9053e43f26b6d0`；构建前后146输入零漂移。独立venv使用 `--no-index --no-deps` 安装本wheel，并显式用 `.pth` 引用现有锁定依赖目录；未重新下载依赖。包/CLI/入口均来自新venv，`sys.path`无checkout/src，逐wheel包文件hash一致。构建隔离仅从显式公开PyPI取得锁定setuptools；不代表干净机依赖安装已测。

完整新建页面 **13检查 PASS**（真实loopback HTTP、JSDOM原页面事件；102请求=92GET+10POST），依次创建项目、CSV、完整Goal v1、固定能力候选、实际预览30、另行确认内部Release/实例及后台Run。成功队列Run为 `run_4d9148440a58446fbb430c02905eccee`，内部AppRun为 `iapprun_3313632374a14e499933f80d7ed1fe65`；不可变binding精确关联两者。成功任务只有一次CLAIMED/fence1，typed结果version1、sum30/count2，完整Goal快照/指纹保存在该内部Release。工程中另有一个被拒绝模型任务，所以总共2次CLAIMED、1个FAILED MOCK Attempt（UNSUPPORTED_CAPABILITY、usage unknown/null）；不抹去其原reservation/账本。真实provider/模型请求0，固定CSV成功任务模型Attempt0。

新进程Ctrl+C clean停止并保留数据。随后同一目录冷开，原完整页面 **9检查 PASS**、46请求全部GET，同principal/project/instance/Run读取结果30，不创建新任务。首Worker `worker_a884fcd8c28b44668428b259f3d57435` 与冷Worker `worker_46bf64f6b45e45c1a84e4620fe6f572d` 单独核对；55表只有heartbeats变化，另外54表相等，已停止首Worker行不再变化。冷开后也clean停止。

原失败未覆盖：第一轮安装、checkout外来源、空库启动和首页三安全头通过，JSDOM逐eval在第二脚本`$ is not defined`，尚未连接或创建业务；原驱动/日志/库保留。改用既有script节点加载后，在同安装wheel的新空目录完成上述新建页面，外层却混淆core Run与内部AppRun ID，StopIteration使完整runner仍FAIL。后续仅纯解析纠正ID关联，再从同一已停止工程完成冷开，不重跑创建链。**修正后的全新完整runner NOT_RERUN**，不得把分期通过写成首轮全绿。

原始包源、driver/runner、安装和进程日志、页面每个响应、55表JSON快照、失败原件与精确hash见[证据索引](../evidence/blank-synthetic-workspace-20261018/README.md)。本片未测试 Windows、原生浏览器/视觉、独立API/Worker进程、PostgreSQL、真实模型/语义/用户人工签收或远端CI；不关闭F1-T02/F3-T06/AT-27，也不把合成工程当完整产品验收。原真实账户来源资格仍SOURCE_MISSING。未做Git远端/auth重试、推送、部署或发布。
