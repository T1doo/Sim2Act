# amount → quantity 列绑定草案

这是完全离线的固定 CSV 工程病例，0 模型、0 业务写入、正式发布关闭。新定义是原应用同一求和节点的 schema 约束列绑定覆盖层；保存草案及检查回执不会覆盖原 canonical 应用、预览、内部版本或实例，不会切换已运行实例。检查 PASS 只证明有限类型/来源/版本/读回条件，语义 UNKNOWN、用户 PENDING，不是人工签收或通用 P-B。

1. 检出 `dev/offline-column-patch-20261008`，按现有安装说明用既有配置启动，保持 MOCK/LIVE=false；本次没有新增表/迁移/授权需求。已有用户数据不清除。先确保原交付图表已通过现有迁移程序建立。
2. 在自有项目保存并授权这份合成 CSV，再通过既有“直接创建 CSV 固定模板草案”入口选择它创建草案（沿用原只读授权步骤）。已有同样材料的应用可直接使用：

```csv
item,amount,quantity
A,10,7
B,20,8
```

3. 打开该草案，选择 amount，运行原预览，核对 SUCCEEDED、sum=30、count=2。该旧预览继续留在历史。
4. 在原“派生图与影响规划”区域点“保存派生图锚”，然后“读取当前图与规划历史”。原节点规划仍是 PLANNING_ONLY，不会自动执行。
5. 在同一区域“CSV 列绑定局部修改”，明确原列 amount、新定义列 quantity，点“提交新定义并保存草案补丁”。查看新绑定、patch_fingerprint、保持对象和新图；此时 DRAFT_PATCH、checks NOT_RUN。
6. 从“已读回的精确草案”选择此指纹，核对新定义/来源/版本后勾选确认，点“确认版本并执行受影响检查”。看到 CHECKED_CANDIDATE、有限检查 PASS、baseline amount=30、patched quantity=15、source_hash 一致，GOAL/SOURCE/REQUIREMENT 保持证明。无需启动模型或后台 AppRun。
7. 刷新页面后重新连接原身份，打开原应用并显式读图/历史；新草案与检查回执可冷读，旧 amount 预览仍存在。读回会清掉确认勾选。丢失接受回执时使用原“原键恢复未知回执”，不要用新键重复提交；原键只保存在本页面内存，整页刷新后先读历史。

撤权/到期/来源变化会阻止旧草案和结果继续作为证据。锁冲突保留原内容；锁变化后需重新派生图并提交新定义，旧草案以 INVALIDATED 显示，不能用旧指纹继续。来源改变仍遵循既有创建新草案的规则。PROJECT/语义/模型候选不确定依赖显示 UNSUPPORTED_CAPABILITY，不能在此固定检查器内宣称完整核查。原内部发布/实例入口继续消费原 canonical 应用，列绑定候选没有新增 Release/部署入口。

API 复现同一页面链路：先 `GET /api/apps/{aid}`、`POST /api/projects/{pid}/apps/{aid}/delivery-graph/derive` 并回读图；在 `POST .../delivery-graph/column-patches` 发送闭合请求：expected_candidate_fingerprint、expected_graph_fingerprint、request_key、kind=`csv.column-binding.v1`、baseline_column=`amount`、column=`quantity`、change（原 action:aggregate 的 node_id/expected_revision/expected_content_fingerprint）。随后 `POST .../column-patches/{原request_key}/checks`，仅提交 expected_patch_fingerprint 和新的 request_key。`GET .../column-patches` 回读，所有入口沿用既有 Bearer 身份和当前授权，不接受客户端 graph/context/schema/代码。

原键路由修复候选为 `dev/column-patch-key-fix-20261008`，原冻结分支不改动。定义键可包含 `/`、Unicode、空格及字面 `%`，放入 URL 时对完整键编码一次（Python `urllib.parse.quote(key, safe="")`、浏览器 `encodeURIComponent(key)`）；不要双重编码。`independent/key` 的原路径与 `independent%2Fkey` 编码路径都定位同一草案，`independent%252Fkey` 定位字面 `%2F` 键，不能代替前者。新的控制字符或 `.` / `..` 路径段键在持久化前返回 INVALID_INPUT；已有可定位原键的定义/检查幂等、指纹及历史结构保持。新增真实 HTTP 回归为 `tests/test_column_patch_keys.py`。

后续完整控制字符修复候选为 `dev/column-patch-control-fix-20261008`：定义、检查 body、解码路径和恢复读取共用 SQL 前校验，键为 1–128 个字符，拒绝 Unicode 控制字符和无法编码的代理字符。控制字符不得通过 JSON 或 URL 编码绕过；原始 HTTP 非法目标由 HTTP 解析器拒绝，编码换行也可能在路由层返回 404，均不会保存回执。合法字面 `%00` 仍可使用，路径须编码成 `%2500`；检查 body 原键保持字面内容，不另做 URL 解码。旧 SQLite 异常键记录不会删除：授权历史读返回 `unsupported_keys` 元数据（UNSUPPORTED_KEY），页面标明保留但不作为当前证明；合法特殊字符、原键指纹与幂等冷读继续保持。

开发者定向验证（Node/JSDOM 只供工程测试，产品无 Node 依赖）：

```bash
SIM2ACT_MODEL_MODE=mock SIM2ACT_LIVE_ENABLED=false .venv/bin/python -m pytest -q tests/test_column_patches.py
NODE_PATH='<自己的临时jsdom目录>/node_modules' SIM2ACT_LIVE_ENABLED=false .venv/bin/python -m pytest -q tests/test_column_patch_ui.py tests/test_delivery_graph_apps_ui.py
```

PostgreSQL 只显式给自有隔离测试库 URL：既有 env fixture 建独立 test_* schema，结束删除。不要传用户数据数据库。实际本轮验证来源、精确 SHA、失败和清理见 [证据](../evidence/column-binding-patch-20261008/README.md)。Windows/受保护 Edge 本轮未运行，原 900/240/150 秒标准不变；旧全量 1591 的结果不能证明这个改动。

本工程病例每应用最多保存 50 个列绑定定义和 50 个检查回执；超出时新请求在接受前明确拒绝，历史不删除，原键恢复仍可用。这个容量约束防止已接受回执被历史窗口静默遗漏。
