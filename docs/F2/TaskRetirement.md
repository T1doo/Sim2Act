# 合成完成任务证明与来源退休（E14）

这是一条有界的P-B工程来源：**LOCAL_DECLARATIVE_TASK**实际可信CSV读取/求和、独立整数oracle通过，固定目标`fixed_csv_exact_sum.v1`才SUCCEEDED。未通过的任务保留FAILED。不是F1 Run，不把历史PARTIAL或PREVIEW改成功；不是模型生成/通用任务引擎。候选及新输入执行仍为PREVIEW_ONLY，未实现Release或完整AT10。

## 接口与来源链

1. MOCK环境`POST /api/projects/{pid}/local-csv-tasks`：`resource_id`、`column`、`request_key`、`synthetic_fixture:true`、`goal:"fixed_csv_exact_sum.v1"`。可信读网关实际执行，独立oracle核查；任务原始输入/输出仅在退休前持久留存。GET `/api/local-csv-tasks/{id}`只返回最小证明/状态；FAILED可核查，不可提取。LIVE模式创建拒绝，零模型调用。
2. 退休前`POST /api/local-csv-tasks/{id}/extract`：`expected_proof_fingerprint`、同项目不同hash新CSV `resource_id`、`name`、`request_key`。复核原始输入/结果/工具回读与oracle，独立任务证明锚定候选，显式授权新应用只读新CSV；运行变量仅column。禁止递归PREVIEW提取，不能假冒generation或删除来源。
3. `POST /api/local-csv-tasks/{id}/retire-source`：`expected_proof_fingerprint`、`expected_source_hash`、`retain_minimal_proof:true`、`policy:"erase_source_retain_minimal_proof_require_current_grants.v1"`。仅当前owner/有效来源授权且证明版本匹配时，原子写退休回执、清空旧资源content（保留id/hash元数据，format=retired）、清空该文件对应本地任务input/output。不在产品存储另存旧内容或答案。不能退休F1 Run、目标卡或现有应用正在使用的源；其他完成任务候选共享源也拒绝，保留既有行为。未知策略或不同证明默认拒绝。
4. 退休后全新Store/API会话打开候选，通过最小证明/退休回执和当前授权验证，读取当前新CSV执行；不重开旧CSV内容、不返回原答案缓存。目标运行及错误历史沿用现预览接口。重试同一提取/退休请求仅返回已有记录，退休后不新增候选。

## 证明、授权与边界

最小证明只包含版本、task/source/owner/project定位和source hash、固定目标、输入输出指纹、可信工具/独立oracle版本及PASS、参数化范围、0模型请求；不包含旧CSV单元格、原始列值/列名、原会话或原答案。证明由可信本地任务完成时一次写入，产品没有编辑证明API；候选快照与独立任务/提取/退休记录交叉锚定，防候选协调改写及重算自身hash。不是针对整个数据库及全部锚点同时恶意重写的密码学认证。

退休**不是撤权**。命令不新增、恢复或延长旧来源grant；其前后grant完全相同。当前来源用户与项目runtime的`resource.read`/`data.aggregate_csv`grant仍作为最小证明复用的保守门，任何撤权/过期即拒绝。来源内容GET和工具读取即使grant有效也因退休拒绝。新CSV依旧同项目固定绑定，每次读取/执行检查当前用户/项目runtime/应用runtime权限交集及hash；跨owner/project、target撤权/过期拒绝，无副作用。仅内容依赖移除，不宣称独立于来源授权。

既有PREVIEW来源路径仍每次回读原资料审计，不套用退休豁免。此策略仅实现显式退休但保持有效授权的合成固定求和切片；若将来要撤权后继续运行，需要另作产品决定，当前默认拒绝。未增加真实模型规划、通用变量归纳、任务族泛化、完整发布/实例/AT09—22。F1/Win11/Release仍独立未签收，真实浏览器/手机视觉BLOCKED。

三张表`local_csv_tasks`、`task_extractions`、`resource_retirements`仅由已有显式`python -m sim2act.cli migrate`/Setup迁移角色创建；API/worker不建表。应用角色只业务CRUD；旧环境升级后需原授权路径覆盖新表业务CRUD，不授予DDL。
