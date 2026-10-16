# SQLite 自然任务心跳锁：只读因果审查

源码基线 `87c1f0d0726f95270255a311983181ae1241bd09`，2026-10-16。根线程唯一仓库写入者。本审查者只读仓库并在 /tmp 写自己的有界探针/报告，没有运行自然业务重 fixture、真实模型、旧矩阵，未访问/删除未知锁或进程。

## 已证实的两段因果与尚未证实的旧身份归因

旧 f9 原件只证明额外预置的第二旧 Run `run_f84938d5ad05425280d986f2284c2324` 终态 WAITING_RESOURCE、精确错误 RESOURCE_UNAVAILABLE/Heartbeat renewal could not acquire the database lock。原件没有该次事务分段、线程及调用时序，不能倒推其必定命中本次受控竞态，也不能把这份旧 FAIL 改写为 PASS。

本轮自然业务基线由根线程实测原预算 SOURCE 与 COLD 各一次 Worker.once：两 Run 各一 claim 成功，整例 PASS110.18秒。它没有自然复现旧 WAITING；没有修后源码，不能叫修复成功。不过原始 trace 明确有 7 次真实 SQLite code5 BEGIN 失败，与长前台写事务重叠。

本审查者另用真实基础 Run/Store/flow 有界探针，一次稳定证明“后台自身锁失败已结束，随后同 owner/fence 实际同步续租 commit，但 failed 仍粘着，下一次 advance 前写成 WAITING_RESOURCE”的因果链。该探针不是自然业务重跑，其初始 state.deadline=None 对应尚未发布完整验证界限的调度状态；并不证明旧 f9 的具体失败时刻或是否已发布 deadline。

## 实际源码路径

- 自然路径是 pa_spec_apps.process_job → text_workflows.process_job 专用 beat；不是 worker.py 普通模型循环。
- `db.Store.tx:603` 的每个 SQLite 事务均 BEGIN IMMEDIATE，纯授权/验证读取也先取得 writer。Store.heartbeat 在独立 checkout 连接自己的 tx 中完整 guard、权限/owner/fence/未过期 lease/CAS，成功 commit 后才返回精确新 lease。
- `natural_spec_runtime.advance_model:691` 初始绑定/回执/commit_guard/effective、`sender_guard:753`、模型回执 settle:900，以及 local/SAVE 的完整最终核查会在前台 tx 内执行。三处 renew 和 advance_and_renew 都在前一 tx 退出后另开真实 heartbeat。未静读发现这些 renew 直接嵌套在自己已持有的 tx 中的自锁。
- beat 在 text_workflows:918 调 heartbeat；只有真实 sqlite BUSY/LOCKED 可有原三次有界重试。没有已发布 deadline 时 retry_cutoff=None；已发布也需有效截止与已提交进展才可 defer。否则 failure.append + failed.set + return（950–954）。主循环 966–975 对该历史 failed 无条件转 RESOURCE_UNAVAILABLE，随后 app_jobs.fail_job/natural.fail_owned 按原 fence/owner/lease 决定 WAITING_RESOURCE；不会因为本次 advance 已在之后完成真实同步续租而清除此历史故障。
- 初读曾列历史 replay 为候选，但普通 PA 的 heartbeat guard 与 load_binding 没有直接调用 verify_instance_records，因此不得仅凭“第二 Run”断言递归历史是根因。实际热点和重复证明成本仍须以分段记录证明；本轮没有给某个 helper 未测量的 CPU 归因。

## 对根线程自然 trace 的独立重算

原始 `/workspace/heartbeat-lock-baseline/test_two_natural_uses_original0/trace.json`，SHA256 `11e5fbcf26dc51f0c3f38ebd73124f194aec722491e8fbc61d78d3ea7c7241c0`。本审查者按 thread_id+tx 从 attempt 配到 acquire/end，避免重复使用的 Python id 错配，共103次事务尝试、96次 acquire。

7次 code5 全在 BEGIN，均没有该尝试的 acquired 事件。其 BEGIN 到 error 观察窗分别约5.020、5.054、5.021、5.029、5.070、5.199、5.797秒；与 MainThread 已 acquire→committed-return 窗覆盖相同时间，总未覆盖仅0–8.1毫秒。特别是第二 Run：

- heartbeat error sequence498 的5.199秒完全落在 natural_spec_runtime settle:900 前台 tx140707923397296 的9.232秒窗内。
- error sequence527 的5.797秒完全落在 advance_model:691 前台 tx140707931011088 的13.170秒窗内。
- sender_guard:753 的前台事务也持有约5.138秒。

main acquired 窗记录的 DBAPI connection id 为140707958445040；failed BEGIN 只有不同 SQLAlchemy connection id，不能假补其 DBAPI id。acquire 到 committed-return 是 inclusive 观察窗，不是纯 CPU、精确物理解锁时刻或独占根因测量。5.797秒含调度/记录开销，不能据此说 SQLite timeout 被配置延长。

独立 derived JSON：`/tmp/f2-hb-baseline-overlap-independent-87c1.json`，SHA256 `957480d84cf1f0190a93151d9e1f119bdce9cd03a6f776babe19b17c90420353`。这是原始 trace 重算，不是另一次业务执行。

## 本审查者实际有界探针

1. 公开 Store 机制：自己的随机 /tmp SQLite 数据库，前台 Store.tx 仅 SELECT1 并持住，另一线程/DBAPI连接 Store.heartbeat(_wait_seconds=.05) 在 BEGIN 得真实 code5，52.8ms，heartbeat 行完全不变。只证明纯读 tx 持 writer，未跑 Run/Worker。原件 `/tmp/f2-hb-own-store-87c1-nlmsoa_d/proof.json`，SHA256 `749237fd22308fc581d5207ad2bf6ae965d1bc616b090c10ab9e745c35067b79`。
2. sticky 故障：真实基础 Run 经正常 API 入队、原 Store.claim，原 lease30/run300、SQLite默认 busy5000ms 不改。仅调度 Event.wait(10)→.001，前台真实 Store.tx 在启动 flow 前先 acquire，以确定性安排持锁。后台原 heartbeat BEGIN 在另一连接真实等待5.024秒后 code5，失败线程返回。前台 commit 后原 Store.heartbeat 同 Run/fence 真实成功 commit 并发布新 lease，然后 advance 返回 True。原 flow 却不再调用第二次 advance，实际终态 WAITING_RESOURCE、原精确错误；created_at/fence/worker不变，0 model attempts、0 tool operations。没有伪造异常/clock/lease、没有增 wait/retry预算。

sticky 原件 `/tmp/f2-sticky-owned-87c1-g4nku3x2/proof.json`，SHA256 `5fcb6d4303d8d75213f1b3eedaaa5214a4df3fbc8f0daf94312d41093469d57e`；脚本 `/tmp/f2-sqlite-sticky-probe-87c1.py`，SHA256 `d9762a647a2f17b5e3014597821f9ebdf9d9d1e3b656da6e6405174b38258352`；原日志 `/tmp/f2-sqlite-sticky-probe-87c1.log`。该受控证据一次成功，没有盲重跑。

## 最小修复候选及独审门

不建议全局 Store.tx mutex、WAL、增加 busy_timeout、增加重试/等待、延 lease/deadline 或把失败盲改 defer。最初协调建议中的“等到 lease 截止”已因父级严格不延等待预算要求撤回，不作为当前可行修法。

若修明确已证实的 sticky 竞态，最小候选仅自然 SQLite、仅 genuine BUSY/LOCKED、仅失败之后该同调用/同 Run/fence 的原 Store.heartbeat 已真实 commit 的同步续租，显式将此已知失败记录为被更晚真实续租恢复。调度 state 需独立 sync commit-generation/return 标记，failure 捕获 halt 时 generation；单纯 lease_until 数值更大不够，因为 bound 读取和早于失败的进展也能更新数值。新续租仍完整原权限/scope/lease/status/CAS及绝对预算门，不增加等待或原 batch 重试。

不能只 clear failed：原 beat 已 return，需安全恢复同调用原 cadence 的后台调度，尤其 model I/O 期间继续真实心跳。非 busy、没有更晚 sync、过期、撤权/竞争、未知错误仍原失败；新一轮失败也不能被旧 sync generation 认领。原错误与恢复事实应保留日志，不把失败 heartbeat 改记成功。若要求外部 writer 的失败也绝不被恢复，需进一步精确标明自身 acquired tx 的重叠归属，不能仅以“后来 sync 成功”推断原锁是自身。

待实现后至少核：后于故障的真实 sync 才恢复、早于故障/仅 bound 数值/伪 progress 不恢复、同 Run/fence/version/owner/截止、model I/O 后台持续、非SQLite/非busy/外部失败保守、terminal优先、stop/cancel、原三次/5秒wait及budget常数不变。无需扩旧故障矩阵；根线程双自然 Run 是正常回归，不作为旧随机失败必现或永久消除的统计证明。

当前阶段为基线因果与修法建议，尚无修后源码可签收。Windows、PG、CI、真实模型及真实语义均未执行。
