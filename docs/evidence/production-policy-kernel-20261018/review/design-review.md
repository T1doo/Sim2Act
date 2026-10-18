# 未安装生产策略内核设计独审

结论：**可按收敛后的纯 immutable policy ledger 设计继续实现**。它是有独立行为的身份和预算状态机；无需安装生产来源，也不产生 LIVE 许可。前一轮把“缺可信来源所以不能开放 LIVE”推成“不能开发独立策略代码”的结论过宽；本报告按本次明确授权纠正该范围，旧封存原件不改。

基线 `842a5b46d52131581edcbfa235ef067cc44b809b`。此次只读源码/Git及文件字节；父级已开始唯一生产修改，当前仅看到 `natural_live_admission.py` 上下文抽取 WIP。未执行产品、pytest、HTTP、SQL、数据库、网络、模型或 Worker。当前是设计/局部 WIP 静审结论，不是内核实现或测试通过。

## 与原方案及已有实现的关系

V5 产品原文：账号共享限流主体（`docs/sources/V5/平台产品设计.md:323`）、请求前保存步骤与预算（331）、未知保守占额及不臆定免费（343）、租约/fence 与未知不重发（349–355）、取消后核对在途效果（366–372）。阶段计划 `:325` 明确工程层可用 stub，模型/用户价值仍需真实书生与授权材料，`:402–411` 保留未知费用。这支持离线策略内核开发，不支持把它标成 LIVE/F2 整体验收。

既有 `natural_trial_budget.py:62–76` 已固定 3/2/2、7 槽、32768 wire、1024 输出、64000/192000 envelope、7168 输出、Run≤300/lease30/paid cap0；`:163–197` 的 `_active` 仍只接受 test_only SQLite 的 SYNTHETIC_ONLY。`:229–267` 已有持久化 reserve/统一账户配额锁；`:280–344` 已有迟到用量保留、单向 UNKNOWN→KNOWN、不退款与不恢复发送。`pa_trial_dispatch.py` 的原发送标记/归档/exact-wire 链也已存在。本切片不复制、改名或冒充替代这些实现。

生产缺源仍由 `production_evidence.py:188–196` 的 NoReturn resolver 拒绝，`production_trial_admission.py:97–111` 没有来源覆盖入口。新 SourceCheck 仅内部事实容器，无 producer/issuer；其构造成功或 bool/hash 匹配不是真实权益证据。30 秒旧诊断约束是工程选择（`production_evidence.py:161–162`），不应变成新内核要求供应商每 30 秒续签的前提。

## 最小可实现接口与不可放宽边界

1. **共享当前上下文，而非共享 Permit。** 当前 `_run_context` (`natural_live_admission.py:861–892`) 与 `_generation_context` (`:895–906`) 的 WIP 拆分可用。旧 `admit` 保持 `_run_context → exact SyntheticOnly/test_only/sqlite → verify → _approved → generation frozen → 原 Permit` (`:910–931`)，抽取未把 frozen 校验移到 authority 之前。新增 worker_id 是只读标量，不扩大原许可。新 reserve/record_attempt facade 在调用者既有事务内每次重新执行完整上下文及 generation frozen；要求 `c.in_transaction()`，先原 owner/project 授权，ContextCheck 只是当次证明快照，不能持有后反复充当 capability。

2. **纯状态与身份不可变。** 新 module 不被 API/Worker/sender 导入，不增 DB namespace/迁移/Grant/executor，不改旧 `budget._active` 或增加任意 `policy=` 插槽。可复用 `scope_for`、STAGES、`_known`、`_recovery` 的纯规则。严格内核状态应由不可变嵌套结构或入口防御性重建构成；frozen 顶层不能保留可变 list/dict 别名。身份绑定原 user/project/trial/contract/approval/stage/Run/runtime/version/fence/实际 worker、account/唯一 canonical quota、Attempt ID、实际 wire 长度和 SHA。使用唯一 `canonical_quota_subject`（`production_trial_admission.py:81–84`）。内部检查结果不返回 FeeProof/Permit。

3. **先匹配完整身份，再处理原 key。** reserve 原 key 重复只读原历史，不补新槽、不重新扣额、不返回重发资格；不同身份/账号/quota/wire/worker 同 key 拒绝。record_attempt 必须消费原 reservation 内的一次标记，相同 Attempt 只能返回原记录，不能开启第二次发送。wire 检查输入若是 bytes，就独立量测/hash；只接元数据时必须明确只能证明元数据一致，不声称 transport 已捕获原字节。所有 PolicyReceipt 恒 `live_allowed=false` / `dispatch_authorized=false`。

4. **结算保账与授权分离。** 先核原 owner/scope 和 stored identity，再接收原正确回执事实；当前取消、过期、撤回、lease/fence/worker 漂移或 fresh source 失败，仍保留已知/未知 usage 与已占槽，只能 `accepted=false`、单向 halt。错误的 supplied original identity 拒绝修改；正确的原 worker 回执在当前 worker 漂移后可以作为非接受事实记录，不能成为提交/再次发送权限。UNKNOWN 保持 null、不退款；若允许单次 UNKNOWN→KNOWN，必须原 response hash/bytes 及所有已知分量不变，恢复后仍 halt、不新增槽、不再发送。

5. **限流和持久性诚实限定。** 纯 ledger 只能约束传入 state 内的时间与次数。若需表达同账号跨 trial 共享桶，显式输入不可变 AccountQuotaCursor 并联合输出 ledger+cursor；未来持久化调用者须对两者原子 CAS。此轮不声称全局/跨进程 RPM、durable once-only 或实际事务已安装；JSON roundtrip 只验证可序列化、完整验证后仍保留占槽历史。旧数据库账户配额锁完全不动。

## 本次必要资格边界

后续定向验证可只覆盖共享上下文旧合成兼容及新 kernel 身份/状态转换：实际合成 SQLite 原批准与 claimed generation 上下文；错原合同/账号/quota/wire/worker 拒绝；reserve 后 cancel/revoke/expiry 的保账、unknown 不退槽不重发；序列化后原 key 历史不重置。应明确内部 SourceCheck 为合成测试输入，不冒真实 fee source 或软件生产资格。无需重跑 UI、旧撤销/取消安装窗口或长链矩阵。

缺少可信 account/source、生产 Permit、durable controller 和受审 sender 继续阻止 LIVE；它们不是本次“可以开发策略内核”的阻断。设计范围内当前未发现必须先扩大权限才能实现的事项；具体代码和最终资格仍待独审。

## 工具与证据限制

本次早期只读 `rg --files` 将 `/tmp` 一并列入时，`/tmp/codex-daemon-1000` 返回 Permission denied；没有绕过或重试该路径。随后仅核 `/workspace/.agents`（空目录）及 repo 中 AGENTS/SKILL 路径，无相关文件；`/workspace/AGENTS.md`、repo AGENTS.md/.agents 不存在。另一次文档 glob `docs/Sim2Act*` 不存在，随后以实际 `docs/sources/V5` 路径读取。均为只读定位结果，不是产品/测试失败。未运行任何产品模块导入或测试。
