# 修改后固定项目 CSV 的新材料与无内容逻辑：实现前独审

2026-10-11，实际环境 `/workspace/Sim2Act`。初读核得干净产品基线 `d96e20e0f82793c5fe460d408ca48ff69fc0e01f`，分支 `dev/project-column-revalidation-20261011`。root 为唯一产品写者；本审查仅在 `/tmp/project-csv-reuse-independent-20261011` 写材料。workspace/repo 无 AGENTS.md，workspace .agents 未见 Markdown 指令。本报告只读审构架，新增实现与 worker/UI 探针尚未运行，等待 root 冻结。

已读 V5 分阶段计划全文、产品 §4 P-B、F2-T03/AT10 子项、新材料与无原材料内容说明/安全合同，并读当前 `ProjectColumnMaterialReuse20261011.md` 实现前合同。最小合同可实施：direct material 保留 fixed source 已批准的 default_column，同名数值列不成立就拒绝；无内容逻辑只保留规范化三步结构，目标另行明确选择新列并形成目标自己的 default。两种授权语义不得合并。

表中行号对应初读 d96e HEAD；root 已开始授权实现，当前工作区产品改动是其实现，非本审查写入。哈希文件分别记录 committed baseline 与未冻结 working bytes，不能以该临时快照签收新增实现。

## 不能直接解禁的源码证据

| 位置 | 当前实际假设 | 直接解禁后的问题 |
| --- | --- | --- |
| `csv_material_reuse.py:87–94` | `instances.closed(plan)` 默认检查 composition；随后要求 `source.composition` 非空并复制它 | fixed project 原计划没有 composition；来源无法通过，不是仅前端按钮缺失 |
| `csv_dag_instances.py:47–54` | `closed(..., fixed=True)` 要求 exact fixed namespace、稳定三步、无 composition/wiring/branch/reuse marker | 必须先证明 fixed 来源，再服务端生成 allowlist 结构；不能接受 caller workflow |
| `csv_logic_reuse.py:73`、`:186`、`:154–158` | canonical 只接受旧二/三步版本；授权复用 material.recipe；load 从封存源版本重建 canonical | 去掉 source 拒绝还不足以通过 mint/cold audit；更不能默认复制 fixed overlay/default |
| `web/csv-dag.js:543` | material options 禁 two-sum/fixed | fixed 需要完整后端适配后才能开；two-sum 拒绝应保留 |
| `web/csv-dag.js:792` | material receipt 要求目标 shape.version 与来源 execution.version 相同 | fixed 来源规范化为普通三步 composition 后，目标 shape 是普通 REPORT；需有限且精确的 fixed→REPORT 映射 |
| `web/csv-logic.js:11`、`:41` | recipe 仅对旧 REPORT 加 report，seal allowlist 仅旧二/三步版本 | fixed tag 不补精确三步映射会丢报告或拒绝回包 |
| `csv_dag_instances.py:135–158`、`web/csv-dag.js:625` | 普通 target REPORT snapshot 不保存 default；冷页面只为 fixed family 选 default | 新目标 columns 为 amount,quantity，已绑定 quantity，却可能冷打开默选 amount |

## 最小安全适配

1. 在 `material.recipe` 增加 fixed 家族专门分支，完整保留 `lifecycle.read_release` 当前权限、实际 patched Run、project origin、精确 overlay/whole-group approval 与 family 双 seal 的门，再用 `closed(plan, fixed=True)` 核固定结构。服务端构造规范化 `read → aggregate → report` composition，不从来源 candidate/overlay 复制自由描述或接线。原两/三步路径、two-sum、branch、递归 material/logic 前缀拒绝保持。
2. direct material 对 fixed 来源仅批准其 `execution_source.default_column`。目标需同 owner/project、已有注册且 graph/current 权限有效、不同 resource ID 和真实 hash，该同名列为有限数值列。missing/malformed/不同列显式拒绝，不能自动回退。仍用完整 source execution、target candidate/graph/auth/rid/hash/column、源 cap 和原 key 冻结 binding，事务预编译后保存双 origin；不新增工具、Grant、Principal 或自动执行。
3. target 新 Run 通过现有 worker、真实读/算/报告、独立 oracle；成功后另行 prepare/commit/create instance。只在本切片明确 material/logic 来源标记范围内，从实际目标 plan input 和成功 aggregate receipt 重建 default_column，并要求它属于当前 target numeric enum。不可从旧 source default 或公共 template 猜测。冷页面依据该已证明不可变 default，原 source overlay/default 不改。
4. logic canonical 可以将固定 source tag 精确映射为同一 allowlist 三步 recipe；公共对象保留有限 tag 与 cap/身份/expiry/实现承诺，严格不包含原 column/default、CSV/hash、goal、overlay/graph、input/output/结果。private audit 仍只有既有 opaque ID 与 source snapshot/approval 指纹。授权时用完整实时来源门；授权后 `audit` 仅 hash 封存 JSON、核 opaque joins 与 family/seal，不调用 read_release/snapshot_from_origin 来重新读取旧 CSV。
5. 公共逻辑移除旧列意味着后续 target 必须显式选择新列，而不是继承旧 quantity。该新列允许出现在 target binding/plan/snapshot/新结果中，不能反向进入 content-free registry。保持 24h fixed expiry、不可逆撤销、logic ID 从原 key 派生、reserved prefix、双 origin、project 锁及每步/最终 typed commit 的 current grant/version/fence/预算门。
6. 页面允许 fixed material 时严格验证来源 fixed tag→目标标准 REPORT 形状、稳定 aggregate/report ports、完整 target 定义/default 与 body/原 key。fixed 授权接受不明，仅 GET 可从冻结 body 计算的原逻辑 ID；plan 接受不明仅 GET 原 plan key。任何坏 200 或迟到跨 identity/project/selection 的响应，不应缓存/paint 错对象或继续旧请求。原 old-family 流程不需扩大权限或调整恢复语义。

## 应冻结的有限验收

- direct fixture 应先注册目标再生成 project checked group；保留源实时图/授权门。若在 source group 保存后新增注册令原 source 授权指纹失效，仍须拒绝，不用适配放宽旧 proof。
- direct 新 target 数值/行数与旧量不同，列顺序 amount 在 quantity 前，运行并保存新 REPORT 版本后冷页面仍默认 quantity；比较全部旧 group/release/instance/typed 与无关 app/manual lock 的 ID/内容不变。
- logic fixture 先 mint 明确授权，再注册新目标、derive 当前图，撤销 user/runtime 的旧资源 Grant 并删除仅 fixture 自己的旧 CSV。原 source Run/Release/CSV GET 必须拒绝，logic registry/cold target 执行成功。target 用 net/units 而不含 quantity，明确所选新列成为 default，新输入得到新结果。
- 通过 SQL 捕获和工具回执确认复用未 SELECT 旧 resource、Operation input/output、Run result/context；FrozenRunContract.resources 与每个实际工具只指 target。public JSON 用精确键集合与旧 sentinel/hash/列/结果负断言，不能只检查无 CSV 字节。
- missing default/坏数/同资源或同 hash、source overlay/default/run/approval 损坏、跨 owner/project、target grant/graph/version 变化、预算收紧、logic expiry/revoke、enqueue 后撤权、cancel/late commit 必须拒绝，失败历史留存且无 typed 成功写。
- 原 key exact replay/GET 零重复写、同 key 换 target/column/body 拒绝；fixed UNKNOWN 授权/plan 只原键 GET，合规迟到接受可保全回执但不跨代次绘制。共同剥 marker/origin、重签 canonical、递归 material/logic 提取不能降级。
- 保存 target 版本、cold instance 另列新运行及保留旧历史；真实 source default 与 target default 对照，避免只测新 plan 初次值。

范围为固定 CSV 工程子项，不签完整 P-A/P-B/AT10、语义/owner acceptance 或发布。PG、Windows/native、旧源码升级、真实模型/付费 API 本轮 NOT RUN，不重试浏览器拒绝路径。当前没有实现验收 PASS/FAIL；源码/合同哈希在 `architecture-source-sha256.json`，后续最终独探必须以 root 冻结的新实际文件为准。
