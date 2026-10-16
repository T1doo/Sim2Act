# SQLite 自然任务第二次运行：最小验收候选

只读核查基线为 `87c1f0d0726f95270255a311983181ae1241bd09`。没有运行重 fixture，没有修改仓库。

## 原失败已证实的部分

- 原 `docs/evidence/natural-application-entry-20261016/f9-final.xml` / `f9-final.log`：PA-normal 在进入 Node 前，`prepared_pa(env, history=True)` 内第二个任务 `drive_to_success` 失败。该批为 1 FAIL / 5 PASS；不能整体改称通过。
- 原 `f9-pa-extra-history-failure-state.json`：第二个任务 `run_f84938d5ad05425280d986f2284c2324` 的结果为 WAITING_RESOURCE，错误 `RESOURCE_UNAVAILABLE: Heartbeat renewal could not acquire the database lock`。
- 原 `case-receipts.tar.gz` 两个 worker-claims JSON：第一个 `run_4a652a553a60492cadf061772b190976` 是一次 claim，fence 0→1 后 SUCCEEDED；第二个同样一次 claim，fence 0→1 后 WAITING_RESOURCE，之后 helper 在准备重试前先断言失败。两者 `lease_seconds=30`、原 accepted clock 间隔300秒；第二次没有实际进入第二次 claim。
- 原归档没有事务等待者/持锁者或原始 sqlite_errorcode，不能断定具体 SQL、线程或事务。最小v1→v2补测当时通过，不代表额外旧历史Run故障已经解决。

## 当前可疑路径：待新实测验证的假设

`Store.tx` 对 SQLite 一律 BEGIN IMMEDIATE，包括完整验证读。自然 `process_job` 在后台心跳启动时 `deadline=None`；`advance_model` 先在写锁事务里完成 binding/receipts 验证，之后才发布 numeric bounds。若第二个任务的首个完整验证事务超过首轮后台心跳等待，后台仍可能在 numeric deadline 尚未发布时遇到锁失败。这是源码推断，不是原失败已证实的根因。

root 已负责自然时序 SOURCE→COLD diagnostic；若自然时序未复现，下一步只增加一个有界受控调度，精确在被证明的事务边界制造实际 SQLite 竞争。不得盲目重复整 fixture，不得修改 busy_timeout、lease_seconds、run_seconds 或模型预算来求绿。

## 最小最终正例

候选 `/tmp/f2-heartbeat-design/test_natural_sqlite_second_run_candidate.py` 可只取保留断言集成 root 的 diagnostic；不要重复两条重测试。

1. 复用 `setup(env)` + `ready(data, 'single')`：正常HTTP保存SOURCE/Goal，3条生成MockTransport响应，既有确认/内部Release/实例流程。不预跑第二目标。
2. 正常HTTP `POST /api/internal/instances/{iid}/runs`，SOURCE runtime **只调用一次 Worker.once**，立即断言 SUCCEEDED、fence=1、仅1条 CLAIMED、单模型请求、原 clock 未改。
3. 读取原 artifact，保留原 bytes/SHA、source Run完整行、原AppRun完整行、v1 typed完整行、artifact resource完整行及app/Release/instance身份。
4. 同一app/Release/instance，使用原 `target_use(..., COLD, 'second-same-pa')` 保存新材料与Goal；只读review断言快照无写；明确consent POST `/pa-use-runs`，保存实际202回执。
5. COLD runtime同样只调用一次 Worker.once，立即要求 SUCCEEDED、fence=1、仅1条CLAIMED、单模型请求。失败时即失败，不resume、不轮询领取、不从新key补交，不使用最多3claims的 `drive_to_success`。
6. 原artifact重读bytes完全相同，原source Run/AppRun/v1 typed/resource行完全保留；新typed为v2，`typed.run_id` 是 **AppRun id**（不是执行Run id），通过artifact.app_run_id与internal_run_bindings精确关联。两份artifact返回同app/release/instance；instance只允许data_version从1到2，其revision/runtime/release/history均保持。两次实际执行Run id互异。
7. 新artifact内容精确来自COLD，PENDING/NOT_RUN保持；无额外应用、Release、实例、owner记录、授权更改。逐次材料创建的新Goal/资源和原现有per-use保存授权应按现有合同保留，不能错误断言全表资源/Goal/Grant不变。

共3条生成mock请求+2条runtime mock请求；真实模型0。不重复旧PA/PB恢复矩阵，不需要JSDOM或PB源fixture。

## 因果原件最少内容

按monotonic ns与wall clock同时记录：`tx_enter`（caller/thread）、`BEGIN IMMEDIATE` 开始/获得/失败（connection、sqlite_errorcode/name）、`tx_acquired`、body完成、commit完成/异常、退出；heartbeat开始/成功返回的committed lease/异常及_run_id；Worker.once开始结束；每Run原clock、before/after完整行、CLAIMED原事件、binding原件、原始HTTP status/body和MockTransport线报。

不要给每条SQL同步落盘以免改写时序；内存记录元数据并finally落盘。最先落trace，之后再尝试诊断读取。记录真实同时持锁者的acquired→commit/rollback区间，与失败BEGIN等待区间重叠，才足以指认tx持锁因果。只有tx_enter不能证明取得锁；只有commit事件回调也不能证明提交完成，应在Store.tx返回后记录。

## 必要的轻并发回归

现成小测试可复用；无需再造自然base fixture。优先这几组，实际选择随修复触点确定：

- `test_real_sqlite_busy_recovers_without_new_claim[known/late]`：真实SQLite锁；短暂竞争恢复仍是原fence，既有late场景覆盖界限随后发布。
- `test_exhausted_batch_defers_only_with_committed_owned_progress[during-batch/before-batch]`：不能把本地观察或新claim冒充已提交续租。
- `test_heartbeat_final_write_requires_live_original_ownership[elapsed/wrong-worker]` 及 `test_background_renewal_rejects_cancel_intent`：过期、换owner、撤销不能续租。
- `test_deadline_after_guard_rolls_back_all_heartbeat_writes`、`test_capped_transaction_wait_never_increases_configured_timeout`：最终界限与原超时不放宽。
- `test_terminal_return_is_not_overwritten_by_late_background_error`：终态提交不被迟到竞争覆盖。
- 若改动natural_runtime续租发布，再跑 `test_model_sync_renewal_publishes_committed_lease`；若改动settlement，再跑原 `test_exhausted_background_contention_keeps_worker_and_owned_boundaries` 的 owned/unknown/new-owner 定向节点与 `test_unexpected_settlement_failure_still_propagates`，不新铺外围矩阵。

候选只通过py_compile/ruff，不冒称已实际运行正例。SQLite/TestClient/mock范围之外，Windows、PG、远端CI、真模型、真实语义均未执行。
