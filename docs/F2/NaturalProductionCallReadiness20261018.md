# 自然生产调用接线：实际缺口与语义候选准备

基线 `5a348ce97325ebbe450c2beb09dff767a4376252`，普通分支 `dev/natural-call-readiness-20261018`；指定新环境checkout与远端一致、clean，约23GB可用，root唯一仓库写入者。按后续明确指令先核源码并独立设计审查；开发授权持续有效，没有工具访问拒绝、待批操作或不确定外发。没有回旧满盘实例、依赖旧bundle或修改任何旧sealed目录。

**设计结论：NO_SAFE_INDEPENDENT_PRODUCTION_SLICE。** 本轮未找到在当前无受信来源、无生产许可且禁止注册/真实调用的条件下，既新增实际行为又能独立交付的生产调用接线。生产实现本轮未新增；这是当前接口依赖与实际源码核查结论，不是声称生产接线已经完成。现有exact-wire adapter/原总账调用链已实现，再抽同一helper或加一层恒拒绝包装没有新增行为。

## 已有实际调用链及确切缺口

| 实际函数/路径 | 已有行为 | 尚缺的生产条件 |
| --- | --- | --- |
| `model.InternModel.request_serialized_captured / _request_serialized / _deadline_request` | 固定endpoint、exact bytes、原wire_guard、全请求deadline、捕获完整或部分body，无重定向/自动重发 | 这是实际adapter，不是自然应用生产许可；不能用其存在推断免费权益或整体准入 |
| `pa_trial_dispatch.reserved → _sent → request_captured → _archive → settle_verified/reject` | 原预算预留、原Run/Attempt/worker/fence/当前权限、发送标记、不可重发、响应归档与保守结算；generation与natural runtime实际调用 | `_binding/request_captured`强制exact MockTransport，`_identity`绑定MOCK；`_metadata`属于该受限归档链但自身无独立mode条件，发送标记livefalse |
| `goal_applications`调用`request_captured`；`natural_spec_runtime.advance_model/enabled/sender_guard` | 已使用同一InternModel及原生命周期；自然节点guard重查原Run、版本/取消/租约/Goal及operation | 自然runtime明确test_only/mock，授权头为synthetic；不是可替换mode字符串的生产路径 |
| `production_evidence.resolve_account` | 原批准后缺来源默认LIVE_BLOCKED，无记录/回调/registry覆盖参数 | 无受支持账户/权益/强制不可收费证据来源；候选诊断始终非权威 |
| `natural_live_admission.admit / Permit` | 完整原批准、阶段/Goal、Run身份、版本/fence/取消/有限租约重新核验 | 仅exact SyntheticOnlyFeeAuthority；Permit只SYNTHETIC_ONLY/livefalse，没有生产发行者 |
| `natural_trial_budget._active` | 原七槽、共享quota、Run/阶段/版本/fence及期限边界，非退还/未知停止逻辑 | 明确只接受SYNTHETIC_ONLY及test_only SQLite，尚无独立生产policy |
| `production_trial_admission._qualified` | 原精确literal软件资格门 | 当前后置检查NOT_REACHED；未修改anchor/pin、未重开已永久取消的旧窗口 |

这些门是相互依赖的同一信任链。当前支持来源为零，无法把opaque ID、hash、paid_cap0、mock成功或开发者自述digest换成合法免费与强制不可收费事实。增加allow_live、放松身份MODE、让合成Permit进入生产账本或用无来源issuer签令牌都会改变这些安全保证，本轮不这样实现。

## 最小接口依赖

1. **受信账户与费用来源协议。** 由服务端固定来源及版本解析原已批准principal/project/runtime/trial/approval/完整contractFP到真实opaque账户与唯一canonical quota。需要可核验来源正文/签章或等价可信读取、合法免费权益与强制不可收费两种事实、检查/生效/到期及当前撤销状态；原expiry不可延长。当前没有可选URL、接口响应格式或受支持服务，不能自行假定某provider endpoint能证明这些事实。缺源、错绑定、过期、撤销或未知均需在凭据/预留/发送前拒绝。
2. **生产准入发行接口。** 在原transaction内重核原_approved及当前stage/Run/版本/fence/租约/取消，再消费上一项真实证据。输出需绑定原批准、stage、原Run/Attempt、worker、账户quota、wire、有限deadline和来源指纹的服务端内部许可；合成对象和HTTP字段不得升级为此许可。当前接口未实现、未发行任何有效LIVE许可，也没有在本轮构造可用生产许可类型替代它。
3. **独立生产账本准入策略。** 复用现有非退还七槽、全局账户quota/RPM与reserve/send/settle时序，但必须单独定义何种服务端生产许可有效及何时重新证明，保持cancel/fence/版本安全。不得将原SYNTHETIC_ONLY条件直接改为通用bool或跨store绕过；未知结果/缺用量保留原占额和未知状态，绝不补零或自动重发。当前没有此生产policy，既有策略原样保留。
4. **生产controller身份与凭据选择。** 把已通过上述链的同一原Run/Attempt接到现有InternModel，不重建executor/sender；明确生产Attempt/归档/发送标记、原current guard、实际服务端凭据选择与exact wire/body/usage配对。该路径还需精确已审软件资格；mock验证不得替它签通过。当前未注册controller/sender、未查读真实凭据、未构建真实请求。上述接口将来的实现与实际执行需要各自独立审查，不能凭本次准备继续外发。

本轮评估了新`OfflineSoftwareQualification`对象的可能性并未实施：它可成为以后独立的test-only开发设施，但当前只会增加软件资格策略/信任输入，不能补生产来源/许可/policy。自述当前代码digest只证明字节身份，不替代原独立literal资格；没有为产出代码而放宽已有门。

## 已完成的独立语义准备

独立准备者在新外部目录制作并封存两份全新中性TXT：A 454UTF8字节/5行，B 519字节/5行，均在原1024字节/20行界内，与当前SOURCE/COLD开发夹具hash不同。另含两份完整Goal字段草案、人工rubric、两张空白独立评分表、单独私有语义参考草案与provenance。Goal的resource_refs仍为明确UNBOUND占位符，不能当前提交；没有创建resource、Goal、Run、Release、实例、Grant或预算。

材料与参考仅为候选准备，尚未取得材料owner确认、blind资格或人工语义验收。独立准备者和准备审阅者已接触内容；root仅复制核字节、程序校验Goal结构及文件约束，未将材料/参考用于实现、mock答案或测试。私有参考不是被测系统输出或已接受gold，也不能发送给未来目标模型。未来如有内容暴露或材料被用于开发，需重新判断是否另制留出集；封存不等于盲验。

文件资格核验只检查9个manifest条目、UTF8/LF/行数/大小/hash、GoalCardInput schema及未绑定占位、空表状态和字节新颖性。首核验器误要求assumptions非空，实际schema允许[]且两草案正确避免编造假设；保留首脚本/exit1/stdout/stderr，去掉这项无依据assert后，以独立日志重新运行文件核验通过。资产、源码、测试与资格门未因此改变；这两次是准备文件核验，不是产品pytest或语义评分。

没有运行产品/API/DB/Worker/MockModel/真实模型，没有生成被测答案或人工评分，先前9个pytest节点没有重跑或计入本轮通过数。生产source、fee authority、Permit/policy仍缺，生产链状态BLOCKED；实际来源/费用/真实语义、Windows/native、PG及远端CI均未执行。旧满盘未落盘独审缺口未补回。

准备资产、设计依赖、有限独审及原始文件核验记录见[证据索引](../evidence/natural-call-readiness-20261018/README.md)。本轮交付限定为精确依赖与已封存候选准备；不把文档或准备核验写成新生产功能。
