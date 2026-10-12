# 四步骤文本 r8 冻结独立静态复核

**STATIC_BLOCKED / NOT_EXECUTED。** 本轮不执行测试或探针。完整 source/tests 414 文件前置核对与作者 r8 freeze 相符，source map `c35164dc31a6692f805c98528d3cda3ef2bd64c4708c4f2543457bb081eb1d08`，实际 HEAD `1ab405fa5a413e9812744d39b7c0d51c9265ee3d`，branch `dev/pb-text-multistep-20261012`。本目录保存准确桥接源码复制、freeze、前后完整核对与 manifest；旧未冻结静态报告/快照不改、不重签。

五项原发现中的 ①③④已在这份代码中闭合；②⑤仍有下面具体残留，因此不能签“原发现全部已修复”，也不签实际 HTTP/Worker/UI、语义、owner 或发布 PASS。当前测试由其他审查者执行，其结果不计入本报告。

## 原发现复核

| 原发现 | r8 静态结果 | 依据 |
| --- | --- | --- |
| ① JOIN-only 历史漏失败任务/typed 版本 | 修复路径已闭合 | `text_workflows.verify_instance_records:713` 独立取 AppRun IDs、binding metadata、ACCEPTED event、RunScope 两边集合并对齐；逐项要求 Run 存在/所属范围及 verify_job；typed 成功双向集合、严格 int data_version 与连续版本一并核验 |
| ② 持久 JSON Python 宽等 | **部分修复，仍阻塞** | marker/Goal/proof/text_goal 改规范 FP，实际 AppRun output 先严格 schema 再 FP；但 `app_jobs.load_binding:313` 的实际 AppRun input 仍用宽等 |
| ③ 未核 seal 的 scope 投影与坏 binding 指针门 | 修复路径已闭合 | `scope_gate:222` 在读取 private draft 前核完整 identifier-only ScopeInput 双 seal、response FP、aid/user/pid/runtime 与 draft rid 投影后 authorize；`job_scope_gate:245` 使用独立 RunScope pair、Run identity metadata、ACCEPTED/Instance/app scope，先于 full Run/context/binding，不依赖可变 binding 指针来确定原权限域 |
| ④ 另项目 source body 先读再拒 | 修复路径已闭合 | `verified_source:678` 的 expected_pid 在 full body 前检查；options/create/verify_origin 均传选定 pid，且 initial_only 在原 source private body 前限定初始来源 |
| ⑤ 无输出状态/error 宽松免检 | **部分修复，仍需收紧** | 无 residue 分支规范 FP 比较 AppRun/Run error，FAILED 必须保留错误；CLAIMED/WORKER_LOST 例外已有 metadata 依据，但 CLAIMED 尚未限定 0 已提交步骤 |

### ②剩余 P1：实际 AppRun.input 仍可以单边污染

`app_jobs.py:313` 保留 `a["input"] != s["input"]`。对正常 accepted input 的 `emit_report=true`，仅将实际 AppRun JSON 改为 `emit_report=1`，其独立保存的 fingerprint 字段不改，Python 字典比较仍相等。后续 bound/verify_job 严格核的是正确的 binding snapshot.input；source proof 的 input_fingerprint 也来自 snapshot，没有核实际 AppRun.input 的规范 FP。于是代码逻辑仍会把损坏的实际 AppRun 输入与原请求视为一致，属于第②原缺口的残留。

必要修复：用实际 AppRun.input 与 snapshot.input 的规范 fingerprint 比较，或重建并比对完整实际 request FP。不能用正常 input schema 校验替代精确原请求比较：新家族原来允许错误输入入队后留下 FAILED 历史，schema-invalid 原请求的只读 GET 应能保留；精确 FP 可同时保证坏原输入忠实保存和单边污染拒绝。

本轮仅静态推导，没有执行污染或其他攻击 probe。该修复位置已发送 root，需待所有活动测试停止后修改和重新冻结。

### ⑤剩余 P2：CLAIMED 例外不要求尚未提交任何节点

`text_workflows.py:663` 的 just_claimed 仅要求 `job RUNNING + AppRun QUEUED + 当前 fence 的 CLAIMED event`。实际第一节点提交后 advance 已把 AppRun 同步为 RUNNING；但当前代码在有 1–4 个 VERIFIED 步骤时，只把 AppRun.status 改回 QUEUED，仍会用同一次 CLAIMED 事件解释为正常初始窗口。

必要修复：just_claimed 额外要求 proved 为空且 tools=0，再按真实普通 claim/resume 的错误保留语义核验。WORKER_LOST gap 目前接受任意历史 WORKER_LOST；建议绑定能够解释当前 fence/status 的相关 lost event，避免多次恢复后的旧事件长期授予状态例外。它不是无限新异常测试范围，而是原⑤状态一致性的精确定义。

## 有限契约静态核查

- 编译确为 private closed profile：严格 AppManifest/ActionSpec/GoalCardInput、schema_check、完整 candidate 对 canonical FP。稳定 read/A/B/report、三固定 action refs、四 action bindings、两个独立词、boolean eq 条件、全部 wiring/locks/permissions/effect/check/budget/outputs 均一起固定。新 report ref 没有进入全局 registry，不构成任意 DSL。
- 每次 advance 只派发一实际节点，分别提交 Operation/Intent/Receipt/counter/event；下次冷读重建 verified prefix、typed input/output、前驱 FP、source hash、条件及独立 oracle。两 lookup 的逻辑前驱都只有 read，report 依赖两者，source/引用从当前真实 bytes 独立核验。没有将单 literal 或 preview 合成四条 source success proof。
- false 报告保留三 VERIFIED 与单独 SKIPPED Receipt/event，最后 Run/AppRun PARTIAL、typed row/成功版本无增加；只 SUCCEEDED+完整四步+report 可提取。零命中有确定性明确空引用输出，semantic UNKNOWN。
- `verified_source(initial_only=True)` 在读取原完整 source body 前检查 immutable Release 的 source_run_ref metadata；已存 derived app 的 verify_origin 同样使用这条门。正常图的提取深度限制为一 hop，二 hop 不能通过来源入口。原 source 仍是当前审计依赖，撤权/删除/Goal head 变动失败关闭；不是此前无旧内容 literal authority。
- GoalSpec 真实 card_id/goal/constraints/unresolved+最后的 version/FP 锚，与完整 accepted binding.text_goal、原独立 Run FP 及 current native head/body 对照。source_goal_card=None 的原因成立：内部 AppRun 不冒充原普通 GoalRun accepted 格式。≤15 unresolved 不截断，完整 native Goal 的其余项在 binding 中保留。
- `commit_guard` 调 lock_live/fence/lease，重新核原 snapshot/current Goal/source/Grant/current limits，精确 Instance revision/Release/runtime/project/app，tools/time 取当前/声明/冻结 min。Operation 前后、SKIPPED 前后、typed insert+data_version CAS+AppRun output 后均有事务内 guard。最后 typed append 与状态写在同一事务，预期失败整事务回滚；本轮不把“存在代码防线”签成实际回滚/撤权/租约/取消测试 PASS。
- stop 分支用受独立 Run FP 保护的 load_binding(authorize=False)，保留撤权后停止入口而不读取 source private bytes。来源/meta 与持久 JSON 坏状态不能成为写入另一 AppRun 的权限。实际行为仍由其他独审验证。
- 请求/repair/reserved counters 有严格 int0 检查，新 process 不调用模型、Replay 或 provider；逻辑 tools≤4。私有 contract 文档已披露实际零模型与全 Run 时间 cap；这不是原 global preflight 的 Action 限额求和证明。
- owner 保持 PENDING/semantic UNKNOWN/formal publication false，新 family 当前逐项人工提交明确 UNSUPPORTED。旧 Goal/ACCEPT 不继承；UI 禁止把工程运行成功解释为人工语义签收。
- 全局 contracts/preflight/Worker/db/tools/CSV与旧 text_apps pure bytes 在本轮 bridge 的 Git diff 中未改。text_workflows 加入明确 CHANGED bridge，只能在最终来源和旧有限续接实际回归重新 qualify 后签兼容，本静态报告不借用该结果。
- 合同文档 `docs/F2/TextFourStepExtraction20261012.md` 已说明 current native head 对历史读取也生效，Goal/材料/权限变化失败关闭，原 source/目标仍为审计依赖。因此本轮不承诺撤权后 private 历史可读；这与普通原 key 准确恢复不同。r8 为 schema-invalid FAILED 输入添加保留原失败的只读核验路径，该路径必须继续避免因第②精确比较修复而一概拒绝原坏请求。

## 证据与局限

`source-before.json` / `source-after.json` 是完整 414 source/tests map、pyproject 与 implementation map 的哈希核对，不执行产品代码。实际 r8 模块与桥接已复制在本目录，源行号针对这些 bytes。文档允许 root 继续修改，不纳入 frozen source/tests map。

本轮测试 0、探针 0、仓库写入 0。未运行 root 作者测试、其他独审测试或其 HTTP/JSDOM/Worker 驱动，也不沿用其分母。需要第②输入规范 FP 和第⑤ claim 状态例外收紧后另行精确 freeze；旧 r8、旧静态快照及全部红轮保留。

末尾完整复核发现当前 `src/sim2act/app_jobs.py`、`src/sim2act/text_workflows.py`、`tests/test_text_workflows.py` 已不同于 r8 freeze，当前 source map 为 `13e46cf6768a7d5bba19e838d1f919696ce0a0868d399fcf30c243d9f99fb181`，implementation map 也已变化，pyproject 保持相同。`source-after.json` 完整保留这些差异。本报告只针对复制时已匹配 c351… 的准确 r8 bytes；不声称 freeze 从前到后未变，不把后续修复重签为 r8，也不签后续改动已消除残留。
