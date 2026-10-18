# P2 修后及新测试静审

本次读取父级 root WIP，仍无产品/pytest/DB/SQL/HTTP/网络执行，未写仓库。不是冻结字节或测试通过记录。

原 `P2_LEDGER_RECOVERY_PREFIX_AND_RPM` 在产品源码静态闭合：`production_trial_policy.py:221–224` 要求非末槽 accepted 且相邻 reserved_at≥60；原 accepted 还需 attempted、完整有效已知用量及 total≤wire+1024。`record_attempt:286–290` 在 fresh 前拒绝已标记/已结算或 halted，保留一次标记及 UNKNOWN 停止语义。此次未发现剩余确定产品 P1/P2。

7 个新测试节点未执行，实际源码检查到两项冻结前 oracle 修正：

- `tests/test_production_trial_policy.py:158` 对真实 grants.revoked=True 硬期待 PERMISSION_DENIED；真实路径 `gate._authorize(:703–705) → Store.authorize(:878–879)` 是 GRANT_REVOKED。应改成该精确代码，不拓宽接受集合。
- `:213–216` 的 prefix 负例也使用同秒两槽；即使去掉 prefix 校验，RPM 校验也会拒绝，因此不能独立验证 prefix 修正。prefix 专用第二槽应设 reserved_at=first+60 并同步 quota.last_reserved_at；dense 负例单独保留同秒槽。该要求仅隔离失败原因，不削弱源 gate，也不新增测试节点/矩阵。

测试范围正确限定：合成 SQLite 真实原批准与 Store.claim，内核 Attempt ID 仅输入身份，未调用 Worker 或写 Attempt；每个 policy invoke 在 fixture 改动以外单独 snapshot 全表 strict equality，并仅导出 FP/rowcounts，后续独审不能冒称凭导出独立重算原 rows。SourceResult 为 synthetic internal data；十分钟前 observed_at 有效并不证明真实来源已核。新 Transition 不能被旧 budget._active 视作 SYNTHETIC_ONLY Permit，resolver 仍缺源拒绝。JSON 往返是可序列化测试，不是 durable 安装或跨进程一次性证明。

这两项测试修正后可以冻结并运行必要定向资格；无需扩大旧门/安装窗口/长链。P2 原 WIP 发现报告保留不改签为当时通过。
