# 未安装的生产准入与账本 policy 内核

基线 `842a5b46d52131581edcbfa235ef067cc44b809b`，普通分支 `dev/production-policy-kernel-20261018`，root唯一仓库写入者；开工HEAD与远端一致、clean、约23GB可用。父级给出更具体的独立内核范围后，纠正此前“无安全独立生产切片”的过宽结论：真实来源缺失阻止当前执行，却不阻止分离并实现准入/状态策略。旧结论及sealed原件完整保留，本轮新增真正状态转换代码，不再抽已有adapter或加恒拒绝包装。

先独立审查设计，再实施两个生产文件：`natural_live_admission.py`提取原上下文检查，新增`production_trial_policy.py`实现不可变内核。没有API/Worker/sender导入或安装新模块，不新增executor、Grant、表/DDL、注册、HTTP可选issuer/source或有效LIVE许可。现有resolver继续恒缺来源拒绝；原软件anchor/pin、synthetic账本和发送路径均未改。

## 实际实现

原`admit`的批准/phase/Run身份、版本/fence、取消、有限租约检查提为`_run_context`，原生成目标frozen核对提为`_generation_context`。旧synthetic顺序仍是context→exact SyntheticOnlyFeeAuthority/test_only/sqlite→verify→原_approved→generation frozen→原SYNTHETIC_ONLY/livefalse Permit。新增worker_id仅只读标量；没有把合成来源升级为生产。

新`check_run`在调用者当前transaction内使用这些共同检查，返回内部`RunCheck`快照，包含原要求/批准/阶段指纹、实际Run/runtime/version/fence/worker及有限deadline。reserve和record_attempt每次重新验证；不能把之前的快照当可反复使用的许可。

来源单独采用内部`SourceVerificationResult`接口和`check_source`：校验完整要求指纹、账户/唯一canonical quota、provider/model/endpoint、decision、明确权益/强制不可收费/撤销状态和有效期。当前没有真实producer；构造对象或ALLOW不证明任何provider事实。测试全部是明确合成内部结果，不是账户验证。来源观察时间不被要求在30秒内，测试明确接受600秒前观察但仍在有效期内的输入；expires_at是内部结果受原试验范围约束的决策有效期，不要求provider提供不存在的签章或续签接口。

当前合同仍精确绑定原ChatAPI和intern-s2。Source结果中的channel identity只是待比对数据，不会选择HTTP目的地；错channel拒绝。这个既有试验绑定不等于比赛硬限制。比赛可选书生模型/渠道的后续需求，应在明确新合同、实际合法账户来源和独立审查下接入；不会自动替换endpoint、模型或账户，也不把新端点资料嫁接旧端点。父级传递的官方资料与用户截图未被本轮作为免费、余额、强制禁付费或执行授权证据；本轮不读取/转发密钥、不要求新建Token或提额。

`ReservationIdentity`绑定完整要求、原批准/阶段、Run/runtime/version/fence/worker、账户/配额、Attempt标识和实际wire字节长度/SHA。Attempt标识是内核预留身份，不声称本轮创建了真实生产Attempt或provider归档。错原合同、账户、quota、wire、worker、approval或channel都拒绝。原key仅在完整原身份一致时返回历史；不重新扣槽或授权重发。

不可变`Ledger`、`Slot`和`AccountQuotaCursor`联合transition表达原3/2/2、总7、每阶段64000/总192000保守envelope、1024输出上界与1 RPM试验约束。恢复状态也验证prefix：所有非末槽须已接受，相邻预留至少60秒，不能从多个未结算槽或同秒历史继续。该约束属于既有试验策略，不把它等同provider公开限流。

reserve产生占槽状态；record_attempt只能标记原reservation一次，且每次重核当前context/source；settle先核原owner/scope/identity，再将已知/未知用量与当前接受权限分离。取消、撤销、到期、worker/lease/fence漂移或source失效不删除占槽/已收到用量，只能拒接受并单向halt。UNKNOWN保留null与已知分量，不补零、不退款；原key重复是只读历史，新Attempt不能绕过halt或pending。当前settlement一旦记录即不可替换；未新增旧预算的迟到恢复安装路径，也未重复原恢复矩阵。

所有`Transition`固定`UNINSTALLED_POLICY_ONLY / live_allowed=false / dispatch_authorized=false / real_source_verified=false`。它不是FeeProof或Permit，实际测试确认旧`budget._active`拒绝消费此对象。旧synthetic路径类型、门、DTO和存储字节不变。

## 状态和执行边界

本内核返回ledger+cursor数据，没有持久化、发送或业务提交副作用。未来调用者须仅装载可信服务端状态，在原权限/proof事务中对ledger与同账户cursor原子锁定/CAS持久化并重新验证，不能由HTTP caller选择旧/空state。当前没有该controller安装，JSON roundtrip只证明序列化及占槽历史不丢失，不等于durable once-only、DB全局/跨进程RPM或真实外部IO原子性。

生产source/准入发行者、精确软件资格、持久controller及受审sender仍缺；这些是实际执行的后续依赖，不再作为拒绝开发本内核的理由。当前不能把内部accepted字段提升为真实免费、业务结果或人工验收通过。

## 有界验证及原件

生产源码冻结 `c62bfb90d23234c6ce56c78bf6c441d6ca1a7703`，一次19唯一定向节点全PASS：7个新policy节点及12个直接受context提取影响的旧synthetic节点；JUnit51.382秒/外54.792秒。没有模型请求、Worker.once、provider HTTP或凭据环境发现，运行级哨兵全部未触发。701输入/135生产及外部runner/guard before/after均零漂移。

闭合前补强取消结算oracle：原用例从未attempted槽结算，不能独立钉住fresh cancellation。仅测试函数修改冻结 `20a43aba27e6276046cd9ae25ac090f02bff89ba`，先从reservation生成marked分支，再取消；一支证明未标记槽不能新record_attempt，另一支证明attempted=true仍因取消而accepted=false、halt且用量8保留。只补跑此1节点PASS，JUnit3.145秒/外5.690秒。生产135文件完全相同，其余顶层AST节点未变；其他18不重跑。

合计19唯一节点、20次执行、20PASS/0FAIL，首轮原件完整保留，不把oracle补强说成产品bug或重复全套。两轮分别46和5个policy操作窗口，每窗口执行全55表严格before==after；仅保存逐表行数/指纹与执行断言，不导出全行、不冒独立DB重建。fixture自身正常创建材料/Goal/合成同意与claimed generation；模拟取消/撤权/版本等SQL修改明确发生在操作窗口之外。未创建生产Attempt或模型响应；产品权限结构未变，fixture沿用现有测试授权。

Ruff及source diff检查通过。设计与静审发现的恢复prefix/RPM P2已修；撤权错误码与prefix/RPM负例隔离也在冻结前修正。原报告分别保留，没有动态复现修前状态或签回旧证据。有限最终独审与原始命令、JUnit、输入/源码闭包和状态证明见[证据索引](../evidence/production-policy-kernel-20261018/README.md)。

最终有限独审通过，无当前确定P1/P2；只复核源码/Git与全部闭合非DB原件，不另跑产品/pytest/网络或打开DB。两轮20个fixtureDB文件仅stat，作者原行断言不冒独立重建。独审明确资格为18个未改节点承接首轮及1个补强节点新执行，不是最终SHA整套重跑；原P2与各阶段报告保留。独审目录含清单18文件59574B，已封存停止写入，不提前背书后续push。

本轮未运行UI、正向source/cold完整阶段链、真实模型/账户/费用/语义、Windows/native、PG或远端CI。原永久取消窗口未重开；旧满盘未落盘独审仍未补回。所有旧sealed目录未修改。
