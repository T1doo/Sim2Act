# F1-2 契约语义工程接口

基线 V5 §5；Schema 版本仍为 `1.0-draft`。本增量提供候选校验，不创建动作、授权、应用或执行任务。七类草案没有升级成发布契约。

## ActionSpec

- 依赖项为闭合的 kind/ref/version 对象；tool、check、prompt 必须在可信注册表，resource 必须是逻辑资源 ID；拒绝重复依赖。
- 权限需求是 tool_ref/resource_ref 的申请声明，不生成 Grant。工具必须在执行器能力内；本地写入只允许项目逻辑 ID，读取只允许资源逻辑 ID。
- 注册工具执行器不能声明其他工具；bounded_agent 只允许 intern.agent 和注册工具。effect、idempotency 必须与可信工具实际读写类别一致；external_write 拒绝。
- 输入输出使用类型明确的 JSON Schema 子集：object 必须闭合；字段上限 32、Schema 深度 8、array 上限 1000、string 上限 32768、enum 上限 20；只接受对应类型关键词，数值上下界必须有限且有序。bool 不作为 number/integer 接受。
- preconditions 仅允许 exists/eq/in；必须引用输入字段并满足其类型，in 最多 20 个值；无表达式求值、脚本或远程引用。
- 只接受独立回执检查 receipt.readback.v1，现有平台预算上限只可收紧。

`POST /api/projects/{pid}/contracts/validate` 接收 action 和可选 input，核对项目所有权、依赖资源和权限申请的实际用户/项目运行身份授权，再检验输入/前置条件。返回 VALIDATED_DRAFT、publishable=false、execution_performed=false；不保存或执行候选。权限声明不等于取得权限。

## AppManifest

嵌套 views、workflow、action_bindings、data_bindings、runtime_identity_requirements、permission_requirements、dependency_lock 使用闭合类型。纯函数 validate_manifest 校验来源约束、有限无环 DAG、唯一步骤/动作绑定 ID、步骤绑定和输出字段引用、可信组件与检查注册表。task_run 来源必须保留 source_run_ref，goal 来源不能声称任务证据。

尚未实施完整清单编译：ActionSpec 修订解析、节点输入输出类型连通、数据绑定完整性、AppRelease 锁定及应用运行授权交集在后续门实现。Manifest 没有发布/执行 API，草案校验结果不能用于发布。GoalSpec 与运行快照的完整冻结语义仍需后续补齐。本次没有进入 F2 的 P-A/P-B、发布或增量验证。

验证：test_contract_semantics.py；生成 Schema 位于 schemas/ActionSpec.json、schemas/AppManifest.json；真实回归见 ../evidence/F1-2-TestReport.md。
