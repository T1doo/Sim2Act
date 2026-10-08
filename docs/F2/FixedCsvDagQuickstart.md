# 固定 CSV 三步 DAG：离线工程候选

在现有 CSV 求和应用内保存新计划：预览来源 → 对指定列求和 → 生成固定文字报告。原应用定义、旧预览、布局、来源绑定和版本保留。只生成既有 Run 的结果与三张只读步骤回执；没有 Report artifact、业务写入、模型调用或正式发布。

1. 使用本分支的本机 MOCK API 和既有 worker，保持 LIVE=0；安装与启动沿用 [Installation](../Installation.md)，本增量不配置凭据或改变数据库权限。
2. 在自己的隔离项目保存 `tests/fixtures/column-binding.csv`：A 的 amount=10、quantity=7；B 的 amount=20、quantity=8。独立验算 amount=30、quantity=15。
3. 保存已有 CSV 求和应用，打开其交付图并显式推导当前图。固定三步面板选择 quantity，保存草案。核对精确 `plan_fingerprint`、原候选/图/来源指纹及三步定义。此时尚未运行。
4. 勾选确认该精确计划，再点运行。既有 worker 按固定拓扑执行；点击读回运行回执，最终看到 quantity=15、行数2、文字“列 quantity；行数 2；合计 15”。每步展示输入/输出/前驱指纹、action revision、来源 hash、检查结果和 operation ID。
5. 页面中的暂停、继续、取消复用既有版本化命令。只在已提交步骤之间停止；明确继续不会重复已提交步骤。重开页面重新连接，再读历史、核对运行回执，无需另建计划或运行。
6. 若接受响应丢失，使用恢复按钮保留原请求键、列和精确版本；不要更换键猜测是否成功。来源变化、撤权、锁或版本失效会拒绝原证明，页面清空旧结果；仅保留本人运行状态和停止控制。失效计划显示 INVALIDATED，不能把它当作当前结果。

API 顺序为 `POST /api/projects/{pid}/apps/{aid}/csv-dag`（严格字段 `expected_candidate_fingerprint`、`expected_graph_fingerprint`、`column`、`request_key`），再 `POST .../csv-dag/{plan_key}/runs`（`expected_plan_fingerprint`、固定 consent `CONFIRM_EXACT_OFFLINE_CSV_DAG`、`request_key`）；GET 原计划和 `/api/csv-dag/runs/{run_id}` 重新核证明。GET `.../csv-dag` 读持久历史；GET `/api/csv-dag/runs/{run_id}/status` 仅返回 NOT_VALIDATED 控制元信息。计划和运行键限制 ASCII 字母、数字、下划线、连字符1–100字符；控制字符与坏代理字符在 SQL/框架编码之前拒绝。每应用至多50计划及50运行接受回执；旧记录不删除。

这是一项固定、有界、受控 schema 的工程实现。任意 JSON 定义、代码、动态工具、循环、隐藏依赖、新权限都不能由客户端注入。纯文字投影执行器 `intern.csv_report.v1` 只接受精确聚合回执 schema，不能进入模型工具列表，不读取资源或保存 artifact。原普通单节点 CSV/Report 应用接口和交付图 PLANNING_ONLY 断言继续保留。

原 V5 §5.2–5.5 允许固定注册能力与有限类型化 DAG，并要求完整 preflight/权限交集；§8 要求既有持久 Run、step-intent、租约和冷恢复；§9 要求人工锁、未知范围和来源失效；§11 要求独立答案和诚实验收标签。本适配器使用既有 Store/Worker/Run/Operation/operation_intents/events 与项目事务锁，不新建表或执行引擎。每步本地有界计算和回执原子提交，事务入口与提交前核 fencing/lease/deadline；冷恢复从唯一已提交前缀重验全部回执和原始 CSV，未知 operation 不继续，通用工具调和不能替换固定步骤证明。

依赖从独立修复分支明确挑选：71ae9f3→1961fda、6ed920b→bb92ccb、c19ae75→5848bdf（slash-key）；7a890f5→e406085、5b2adcf→ffd4efe、f40d975→e912945（全控制键与框架 Unicode 边界）。`src/sim2act/column_patches.py` 与 f40d975 字节相同。审查候选 `4513b4eed9a9794333d7a30cf96b1ac9f88d48fb` 保持冻结；本分支不覆盖它。其原独审状态由父线程跟踪，不冒认 DAG 已独立签收。

验证证据见 [本轮说明](../evidence/fixed-csv-dag-20261008/README.md)。工程成功仍为 semantic UNKNOWN、owner PENDING、publishable=false；原生 Windows/Edge、真实任务 gold、通用 P-B、人工签收未完成。保留 Windows900 / Edge240 / Node150 标准，无新CI、main合并或部署。
