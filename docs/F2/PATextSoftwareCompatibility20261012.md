# P-A 新软件与两个旧字面检索锚的有限兼容合同

本轮以 `6088dcfc93ecf9de48f10ab6a72b89ec4759fd91` 为基线，在
`dev/pa-text-compatibility-20261012` 开发。根代理为唯一产品写入者；原 owner
草案、main/core、旧锚、旧 seal、旧失败原证据保持不变。真实模型请求0，费用0。

## 实测根因

原 r4 675 节点扩验里的82项旧兼容失败分为：70项在预检409停止；12项未进入
测试要求的深层历史校验。新 `generation_approvals.py`、`pa_material_bindings.py`
首先触发完整文件集合检查；contracts/db/goal_applications/text_apps/worker的五个
非白名单文件摘要也改变。这是尚未证明的新软件资格，不是82个已经证明的独立
下游语义缺陷。两条当前6088代表红测真实复现了预检拒绝和 verifier 未调用。

已接受的 `a4fd476127a477006dbdb29a9a1f6c2f09e6a001` 源码在同环境独立只读快照
运行原两份测试，100 PASS，84.80秒；416源码/测试文件前后摘要一致。修复候选
使用相同旧测试及原始旧数据库 fixture，100 PASS，213.95秒，所有原82个节点逐名
映射为实际PASS；36份边界回执记录深层校验、真实SQLite私有单元校准及全库不变。
原失败与当前通过分别归档，不覆盖或改标SKIP。

## 精确的新软件资格

原 `text_software_anchors.json`、`ANCHOR_HASH` 与 `CHANGED` 文件名集合不改变。
未知旧fingerprint仍UNSUPPORTED_CAPABILITY。只有已经通过原锚完整性与旧files
fingerprint检查、但原软件比较拒绝的两个既有锚，才可以核对新
`text_software_qualification.json`。该JSON有代码固定的SHA、唯一字段与重复键拒绝，
绑定原anchor SHA、两个源fingerprint、审查a4fd/6088版本及完整70个实现PY的精确名称
和摘要。任意追加、删除、改变文件，包括原CHANGED里的文件，都不能按文件名豁免。

为避免证书摘要与包含证书pin的源码互相递归，只有 `text_continuations.py` 中唯一
module-level simple assignment `QUALIFICATION_HASH = "64hex"` 的64个字符置零后
计算资格摘要。AST校准要求唯一写入、顶层简单字符串常量及精确源片段；重复、嵌套、
表达式或注释/字符串代替赋值均拒绝。其它字节不规范化，不规范整行、函数或AST。
该唯一摘要孔只用于完整目标资格核对；实际implementation()、批准、Release、Run
仍使用全部70文件的原始字节fingerprint。pin改变也会改变实际软件fingerprint，旧
permission不会自动续用。config仍沿既有软件fingerprint规则排除，运行设置另受冻结
合同与当前权限门约束；打包明确携带新JSON。

新资格不是实例执行授权。原逐实例预检/明确consent/提交仍冻结完整旧候选、版本、
实例数据/历史、原生Goal、原Grant、预算、当前原字节软件fingerprint及精确key；
提交和实际Worker继续复验。其它实例、普通generic执行、新实例、撤权、过期、取消、
竞争、迟到结果及伪造来源不能继承资格。旧审批/候选/Release/任务/结果保持原seal；
只有明确批准的现有实例增加新的Release和软件permission，并按新输入实际重算。

## 差异逐项审查与有限证明

完整70项原锚/a4fd/6088/当前逐文件摘要与变更分类见本轮 `file-review.json`。
原白名单门外七处的行为审查如下：

| 文件 | 新差异与旧路径边界 | 实际复验 |
| --- | --- | --- |
| generation_approvals.py | 独立P-A namespace、精确Goal/Grant/预算、不可退款发送槽；旧literal实例不取得该批准 | 默认关闭、sender重核、未知usage/模型/工具/截断闭拒、late rollback |
| pa_material_bindings.py | 独立真实模型图typed槽来源；无关family只投影判族，不继承新来源 | 新材料cold NoModel、来源/graph篡改、撤权、CSV授权前ledger边界 |
| contracts.py | generation activation可选且普通None仍排除；旧字面执行schema/check不变 | 原旧fixture/Frozen合同、原始响应与旧形状历史、当前P-A主线 |
| db.py | generation来源按ID在完整私有载荷前授权；旧INTERNAL_APPRUN无generation标记 | 原旧100、深层history/private-cell校准、claim/inspect撤权fault |
| goal_applications.py | activation分支精确实收模型证据/结算/提交；无activation仍离线旧路线 | 普通旧形状/拒绝原响应、合成sender、结算immutable、精确批准 |
| text_apps.py | 新namespace需独立真实模型来源；原task_proof/字面kernel继续原检查 | 旧100、独立文本逻辑共享回归、新绑定否定案例 |
| worker.py | 新generation配额/预算/提交门有条件进入；失败回退只读取fence元数据 | 原旧cold Worker/历史/撤权/late、共享持久应用、新P-A最终事务 |

同样审查已在原CHANGED中的api/apps/text_continuations变更，并固定其当前摘要；
其余60个实现文件相对a4fd无变化。6088之后仅text_continuations实现资格核对，
另增加JSON、独立篡改测试和pyproject package-data，未重写执行器。

22个目标资格/篡改节点实际通过，含两个旧锚、七处门外文件与原白名单文件变动、
文件增删、manifest/anchor/pin、非简单赋值、重复JSON及未知源闭拒。真实旧100、
生成/新材料56、共享129及独立复验的精确终态和重叠见[执行证据](../evidence/pa-text-compatibility-20261012/README.md)。

此合同仍只覆盖两个既有单节点字面检索family与当前有限模型图复用，不能称自主
业务规划或自然目标语义通过。PG、Windows、原生浏览器、真实模型/费用、完整
P-A/P-B业务验收、部署及远端CI未跑。实际wheel构建尝试因缺setuptools失败，原错误
保留，未安装依赖；真实wheel冷安装NOT_RUN，不用静态package-data核对冒充构建。
