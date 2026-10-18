# Journal WIP 非作者静审

结论：**P2_READ_UNOWNED_SHARED_CURSOR 未修；其余所审路径暂未发现确定 P1/P2。** 这是静态控制流发现，没有运行产品或动态复现。此次读取的 uncommitted journal 文件 bytes/SHA 及 read 原片段分别保留在 implementation-review-draft.json、wip-read-fragment.txt；不能用后续修复字节覆盖本发现。

## P2：无自有 ledger 的 read 会返回共享账户游标

位置 `src/sim2act/production_trial_journal.py:152–158`。`_context:79–90` 仅检查严格 contract 投影、caller 自有 project/runtime 与 account→quota 一致；它不验证原 approval 或本 owner/scope 已有持久 journal。随后 read 先 `_quota(create=False)` 取得共享 account cursor，`_ledger:129–130` 对 absent ledger 合法返回空 Ledger/revision0，最后 receipt 仍包含实际 global quota_revision/last_reserved_at。

因此，在同数据库已存在某账户 cursor 的前提下，可以用自己项目的合法 typed contract 副本改成该账户 canonical quota，且无需该 trial 曾批准或有 ledger，调用 read 得到他方账户的共享时间/revision。它违反 docstring 的 owned metadata only；即使当前没有 API 安装，内部读合同也应在本片封住。

最小修正：read 在读取/锁共享 cursor 前，用 scalar/header 锚核本 owner/project/trial 的完整原 ledger pair 存在，且 request fingerprint 与当前 expected request 精确相等；缺失立即拒绝（NOT_FOUND/OUTCOME_UNKNOWN 均可按现规范选择），不读取或返回共享 cursor。先锚核时不锁 ledger，以保 account→ledger 固定锁序；随后正常 account lock→完整 ledger lock 并重验。等价的严格原 ledger 所有权前置门亦可。不要求新 Grant/source 权限或完整材料正文，不改变 fresh mutation 的初始化路径。

建议只在新 journal 定向 fixture 中增加一条断言：先创建账户 cursor，再以另一自有 project/无原 journal 的 contract 调 read，拒绝且四行/所有保护表不变。无需新增一般矩阵。

## 已核其余关键控制流

- `_quota:93–124` 先严格 pair load，单边立即拒绝；全新双 insert 只接受 [1,1]/[0,0]，mixed拒绝。revision0 仅允许本 TX 新 seed，不能将空 seed 当已提交状态接受。
- quota/ledger exact request 和严格字段/typed状态检查；ledger 的 last quota revision≤当前全局 revision，允许他 trial 推进后的旧历史。
- `_cas_pair:60–76` 以原 PK/fingerprint/requestFP（其中 snapshot 包含 revision）CAS，两镜每条 rowcount=1；`_persist:161–168` 同 TX 更新 ledger 两镜和 quota 两镜，Store.tx 任一异常回滚。
- `_apply:183–191` 完整 policy._bound、原 Attempt identity 和 wire 先于 history shortcut；精确 reserve/marked/same Outcome duplicate 仅返回当前可信状态，changed默认为false，不推进revision或重新fresh/send。新 mutation 才核 expected_revision。
- reserve/record_attempt 调原 policy 并在四行持久化后最后 fresh；settle 保留原事实，fresh失败仅 acceptedfalse/halt，不因失效丢 usage。末写/完整性/CAS故障仍整TX回滚。
- 新模块不注册生产 source/sender/Permit，不扩大旧 synthetic bucket；所有 receipt 恒 non-executable。SQLite/PG claim范围仍应等实际新定向结果，未运行测试不称实现已通过。

只读 Git/文件，无产品/pytest/HTTP/网络/DB/SQL/Worker/model 执行，无仓库或旧 sealed 目录写入。本新review目录未seal，等待root修复及最终冻结资格。
