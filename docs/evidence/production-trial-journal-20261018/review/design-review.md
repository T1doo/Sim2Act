# 未安装持久 journal 最小设计独审

结论：**可继续实现，以下四项为具体实现必须保留的约束；不是新增权限前置。** 基线 `080ea7b184a7476019431c1803b4bfe4864afbd9` 已只读核对，当前工作区 clean。只读 minimal-design.md、现 policy/budget/gate/Store 事务和控制路径；没有产品/pytest/HTTP/网络、DB/SQL/Worker/model 执行，也未写仓库或任何旧 sealed 目录。

这是真实新增的可信加载与持久 CAS 控制器，原 pure policy 已存在，复用而不重造其预算算法。新 namespace 明确 uninstalled，与旧 synthetic 账户桶分别计数；API/Worker/sender 不安装、返回恒 false。旧 19 unique/20 executions 仍仅历史资格，不重跑。

## 必须精确实现

1. **新账户 pair 不修复半副本。** 不能直接复用 `natural_trial_budget._quota:208–213` 的逐个 ON CONFLICT 后读：若原先只存在一半，该模式会补齐并冒充完整新账户。按固定 left→seal 顺序执行两次 insert-on-conflict，实际创建结果仅允许 `(1,1)` 全新或 `(0,0)` 已存在；混合 `(1,0)/(0,1)` 必须拒绝、整 TX 回滚，再严格双份读取。可用等价的可靠 RETURNING/rowcount 证明。全新并发两连接应串到同一个唯一键；第二方读完整已提交 pair，不是另造桶。失败的 loser 不得留下初始化 ledger/quota 哨兵。

2. **revision 是 CAS，不是复活或跨 trial 等值锁。** 主身份按原 user/project/trial key 定位，stored header exact scope/contract/account 不同即拒绝，不能借改 fp 另建空账。所有新 mutation 要求 expected_revision 为精确非 bool 整数且匹配当前 ledger；同 TX load 后，以旧 key/fingerprint/requestFP 和 revision 绑定作四行 CAS，任一 rowcount≠1 整 TX 回滚。ledger 记录的 quota revision 仅是该次写的引用，应 `<=` 当前全局 quota revision；别要求相等，否则别 trial 正常推进会阻断旧 trial read/settle。cursor 时间不可退，空状态仅在从未存在该可信 scope 时建立；不声明能识别 DB 管理员同时回滚全部可信行。

3. **原 key 重复只读当前可信历史。** 必须先完整比对 stored identity/wire/scope/account，settle 还需 exact Outcome；再允许无视旧 expected_revision 返回 `duplicate=true/changed=false` 的当前历史。不能返回过时的 pre-settlement 快照，不增 ledger/quota revision，不创建缺失 pair，不运行 fresh source/新 marker，不授 send。wrong identity/Outcome 仍拒绝。read 不初始化任何行；pending/marked/UNKNOWN 重开只读，缺 settlement 时保留未知/null，不伪造 response hash/usage。

4. **保存事实与接受权限分离。** reserve/record_attempt 在账户等待后完整 policy fresh，并在四行写后做最后 fresh deadline/source/context 检查；失败整 TX 回滚。settle 必须继续使用原 owner/scope/identity 的可信已预留槽，fresh cancel/expiry/revoke/source/lease/fence 失败仅使 accepted=false/halt，不能因这一失败丢弃已收到 usage/原占槽。真正 SQL/CAS/完整性失败则整 TX 回滚，不能部分写账。

## 锁与线性化

父级补充的固定顺序可用：owner/project锁 → account pair（固定双键顺序）→ ledger pair → policy fresh 内既有 project/Grant/phase/Run锁 → 四行 CAS → active 操作最后 fresh。当前新 journal 不存在 Run→account 反向，所有相关 binding/phase 在同 project；账户锁之后不再获取其它 project/account，避免扩出跨账户环。

依据：`Store.tx:702–727` SQLite BEGIN IMMEDIATE/全异常回滚；`gate._authorize:697–711` project/原 READ+SAVE；`_run_context:861–892` 原 phase+Run行锁、worker/version/fence/cancel/lease；`Store.command:1613–1678` 普通 cancel 在 Run 锁内写状态，app command 先 project 再 Run（`app_jobs.py:673–692`）。取消先提交则 marker fresh 拒绝；marker 先提交则仅表明会计 marker，后续取消的 settle 拒收保账。持锁 fresh 点是接受判定线性化，不声明外部 IO 与数据库原子性。

现源码仍有普通历史 Run/Grant 控制路径，不因此把此设计称全系统 PG 无死锁证明；本轮只能按实际 SQLite 有界并发结果计分，PG 实现语法不等于 PG 资格。不要改 Store/旧 gate/lease/Run 期限以让并发测试通过。

## 最小资格建议

沿原设计已有五类：同原 Attempt 双 Store once-only；跨 project/trial 同账户首次争抢且 loser 全回滚；marker 与 cancel/lease/fence 双序；新 Store 读 pending/marked/UNKNOWN 不变更/不重发；四行 CAS 或末写异常完整回滚、半副本损坏拒绝不修复。测试应观察真实两个连接的 BEGIN/受控阻塞与终态，不把仅设置 Event 当已取得数据库锁。所有线程有界 join；业务/Grant 保护表与 journal 实际写增量分别精确断言。无需旧 19 节点、UI/模型、旧取消窗口或一般故障矩阵。

当前只是设计允许继续，无已实现控制器或测试 PASS 结论；最终 source freeze/定向原件仍待独审。可信生产 source/有效 LIVE Permit/sender 和费用仍缺，本片不补这些真实权益证明，也不要求 provider 每30秒续签。
