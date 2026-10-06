# E17：固定内部 AppRun 的持久 worker

依据原 V5 F2-T09、产品设计 §8/§10。基线 1149816、事前范围提交 7e122c7；正确 /workspace/Sim2Act-pb / dev/f1-foundation。仅 E16 固定可信 Release/Instance 的内部合成运行；正式发布/实际部署入口仍关闭，不新增 CSV 功能或任意代码。

## 路径及原子边界

`sim2act.app_jobs.enqueue` 在一个事务中保存新内部 AppRun、既有 Run 队列、冻结输入契约及 `internal_run_bindings` 独立关联快照。返回 run_id/app_run_id 与版本后可以关闭会话；同 instance/user/request_key 同输入返回原回执，不把新输入当成缓存。原同步 E16 路径不改为伪造队列历史，同键不能跨同步/异步协议复用。

复用原 Worker.once/process 与 Store.claim/guard/heartbeat、fencing、事件/Operation 账本。运行状态以持久lease Run为权威，控制和终态同步AppRun，读取不会把未完成结果冒充SUCCEEDED。worker 在任何 model.reserve/request 之前路由内部分支。冻结 Run envelope 接受既有 runtime 或 appruntime 的格式；F1 submit 仍使用实际项目 runtime，内部队列固定实际已授权 app runtime，并逐次重新匹配 Run/binding/AppRun/Release/Instance 身份；没有创建或恢复 principal/Grant。沿用 F1.3 envelope 字段格式仅为了调度兼容，内部结果验收由 Release check 和独立 oracle 证明，不把旧 F1 语义目标改成功。

授权取输入和创建 PREPARED 意图使用短事务（project→Run→Instance→gateway Grant）；资源 hash/当前 user-project-app 交集均核实。固定注册工具 data.aggregate_csv 的同一计算实现对已授权输入快照在事务外执行，heartbeat 独立维护。没有在服务长事务中同步跑计算。

提交使用第二个短事务，重验当前 lease/fence/worker、暂停取消意图、实例 revision、原 Release 精确指纹、当前 Grant、实际 source bytes、完整 plan/input/specs/metadata。oracle 对当前授权的冻结字节，而非调用方可改 plan。实例结果版本及类型化数据、VERIFIED receipt、AppRun/Run SUCCEEDED 和事件在同一事务提交；同一 AppRun 的唯一数据行约束、实例锁及 data_version CAS 阻止重复追加。没有借 preview 历史充当执行。

新表 internal_run_bindings 经现显式 migrate/Setup 建立，运行期只有业务 CRUD；API/worker 不建表。原 Run GET/commands 路由内部绑定的持久读取和控制，不增加发布或 enqueue HTTP 入口。

## 控制与恢复

QUEUED pause/cancel 分别持久 PAUSED/CANCELLED，不会被领取；RUNNING 的请求在取输入前和提交前重验。不追加未发生的结果。owner 在撤权后仍可 pause/cancel；resume 要当前完整授权，取消意图不允许 resume 清除。坏输入保存 FAILED/error，结果版本不递增；后续显式新请求与历史失败并存。

PREPARED 在此固定纯读取/计算路径还未产生业务效果；worker 丢失后原 claim 先记 WORKER_LOST/RECONCILED、增加 fence，然后安全重排。旧 worker 即使算完也不能提交/覆盖新状态。结果本地原子提交后 worker 回报丢失，Run 已是 SUCCEEDED，不重排或重复追加。

任意 call_id 的 DISPATCHED/OUTCOME_UNKNOWN/RECEIPT_KNOWN 或未决模型尝试均阻止派发和结果提交；不覆盖旧账本。取消或失联仍有未知时保留 RECONCILING/cancel_intent，其他未知等待 WAITING_RESOURCE；resume 拒绝。未知外部效果只是合成注入负例，本轮没有外部 adapter 或真实外部恢复证明。

已接受 Run 冻结 Release 与实例 revision。期间切换指针导致前置变化，采用保守 VERSION_CONFLICT/FAILED，不静默换 Release、迁移结果或回滚数据。更广 V5 在途兼容迁移语义待后续明确。

失效/篡改绑定不能靠失败处理写到别实例的历史。失败路径也以独立 accepted Run fingerprint 核实 snapshot 与 owner/project/runtime/AppRun 身份；无法安全定位原 AppRun 时仅主 Run 拒绝，原残留 AppRun 不猜测修复、读取拒绝。该人工元数据损坏边界明确保留。

## 验证与阶段门

新测试 `tests/test_persistent_app_runs.py`，真实 PG 子进程 fixture `tests/fixtures/internal_app_worker.py`。覆盖原子 enqueue 回滚/冷 Store、双实例/并发幂等及版本、pause/cancel 派发前/提交前、独立 heartbeat、不持计算长锁、旧 fence/失联、当前三主体撤权/过期、FAILED、未知全 Run 与取消意图、source/metadata 篡改、失败绑定不损坏别实例、升级前置变化。四个真实子进程检查在最小 CRUD 角色运行现 Worker：提交前 os._exit、提交后 os._exit、实际计算阻塞窗口中的 pause/cancel与heartbeat；记录源和回执真实核对，fixture 不进入生产工具注册表。

实际结果及同工作区独立审查见 [证据](../evidence/F2-persistent-apprun-20261006/README.md)。原 AT05 文件和 V5/历史 AT02 不改。AT17 保持 OPEN：只读 sum 与内部 result ledger 不能证明 preview 写隔离，须后续受控写 fixture 真正验证。

正式发布/部署、通用业务数据与写动作、完整 P-A/P-B/AT10/F1/Win11/protected-browser 仍未验收。真实模型0，无业务外发/导出恢复包/安全策略绕过；本轮未新增浏览器视觉检查。

2026-10-06 E19更新：原E16/E17内部service现经[已认证内部工程API/UI](InternalEntry.md)接入，精确快照显式确认及既有可信只读worker、独立实例数据/控制/重开可用；旧文“未接HTTP”是E16/E17当时边界，正式发布/部署入口仍未启用。无新Grant/表/任意writer或真实模型调用。
