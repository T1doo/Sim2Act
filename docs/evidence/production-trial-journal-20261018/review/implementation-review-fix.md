# read 隔离修复与 journal 测试预审

**P2_READ_UNOWNED_SHARED_CURSOR 静态闭合；当前未发现剩余确定产品 P1/P2，可冻结必要定向资格。** 仍只是文件/Git 静审，无产品、pytest、HTTP、DB/SQL、网络或 Worker/model 执行，不把待跑测试称 PASS。旧 WIP 报告及原 read 片段保留。

`production_trial_journal.read:155–165` 在 `_context` 自有 project/runtime gate 后，只投影 owner/project/trial 的 kind/request_fingerprint 标量，不先取 ledger FOR UPDATE；要求原两个 kind 锚齐备且 requestFP 精确匹配本次 expected request，否则 OUTCOME_UNKNOWN，尚未调用 `_quota`。之后 account→完整 ledger 锁读和 scope/account/state 重验保持不变。没有未知 trial 的空 revision0 receipt，也没有共享 cursor 泄漏；首次显式 reserve(expected0) 不受影响。

新测试在同账户跨项目 winner/loser 场景附加两个实际调用：合法已批准但没有 journal 的 loser，及未批准 forged trial，都要求 OUTCOME_UNKNOWN，SQL observer 记录 QUOTA SELECT0。只增加同一节点内的原缺口断言，不扩旧矩阵。

其余静审覆盖与设计一致：同 Attempt 两 Store reserve once-only/重复无写；旧 revision 新 Attempt拒绝；跨项目统一账户首次争抢；在两个 ledger CAS 已写后故意使用旧 quota fingerprint 并全55表回滚；缺镜拒绝不补；真实子进程 read/pending/UNKNOWN/重复保留；marker/control(cancel/lease/fence) 六个双序在独立连接上观察 BEGIN、写后持锁、释放后终态。原控制 SQL 发生在明确受控窗口，fixture不能冒称这些 Run/events 一直不变。

冻结前建议的有限观测修正（非新产品阻断）：

- CHILD 子进程目前只 guard `request/request_captured/_request`，后两个不是当前主要 InternModel API。建议与实际五入口 `request/request_serialized/request_serialized_captured/_request_serialized/_deadline_request` 同步；仍保 HTTPTransport 与 Settings.from_env sentinel。否则只能称已经 patch 的实际入口未触发，不能泛称全部模型入口 guard。
- QUOTA SQL observer 可先在 winner read 上正向校准确实命中，然后 clear 再验证两条 negative 的0，避免回归监测器盲计0。
- race `_persist` 包装在 first=marker 时也会给后续 settle 加 marker-written 标签；若最终 trace 作时序证据，建议仅第一次 pause标记或明确区分该后续标签。初始 contender/held/release 断言本身不因这一命名重复失效，不作为新增产品问题。

本目录仍未封存，等待最终冻结及已经闭合的原件；不应据本报告声称 PG/真正生产 source/发送/费用、旧19节点重跑或更大恢复矩阵资格。
