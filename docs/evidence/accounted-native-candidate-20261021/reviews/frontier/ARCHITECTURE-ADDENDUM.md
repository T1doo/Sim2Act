# 合片架构补充：精确 frontier + 预编译 immutable arena

只读设计结论：**CONDITIONALLY_FEASIBLE_DESIGN_ONLY**。父侧明确只减两个 accounted 专属根和 complete.source/generated/generation.run，独立 Generation/Source/audit/job 根仍 fresh scan/typed，解决了初审主要范围歧义。当前无精确候选代码或运行结果，本补充不签实现/预算证明/安装或执行窗口。

1. Source→recipe→backend version→Generate 仍各在原位置一次；第二个完成前只能暂存，frontier 未激活；整族 LEGACY 时不装新键、不重读 producer。发行后只能 close。
2. `_ColdGraphRead` 新私有 continuity-frontier key 应显式使用独立表示/namespace，不改旧默认 input_bytes/persist/raw/origin 合同，也不冒称与旧 input_key 编码等同。每次校验精确被替换路径及同 graph/epoch/scope/role/packet/arena 句柄；禁止按对象 id/run_id/前缀全局 prune。candidate pre 的新表示不得流入 post/origin；出口 failclosed。原未 owned 根和新 add 的循环/隐藏回根校验继续 fresh。
3. native mode 可以不叠加 assertion-only legacy oracle，旧默认 mode 继续原 oracle。但原 `_graph_trial_stage_raw_from_raw` 不能直接消费 Family，因此“完整stage仍旧guard”须准确表述为：原未迁移字段/业务 joins 保留；native `assert_stage` 逐项覆盖 9 元组、Cold/Source 分支、binding、Cold job 完整 fresh 根、raw/metadata 身份、frozen 完整模型、extraction draft/target/goal 原身份及 body 原完整 typed 值、source_proof 原 complete 身份。不得用一次 PASS 取代仍 mutable 字段检查。
4. arena 只可预编译不可变 packet 的 views 和两条 Source canonical 纯值（owned wire/payload/slot/capture 等）。每次消费仍做 family/scope/ctx/生命周期绑定，当前 Ledger 全字段交叉对照、SQL archive keys/evidence_mode、authorization/time/lease 等原 live joins。Canonical PASS 是纯值结果，不能缓存授权或当前 Ledger/Run 成功。
5. 不再把 mutable Ledger/resolved 冻结为 packet 的方向可行，前提是完整原 typed/DB/auth guards 原位置保留，新的比较严格覆盖原完整字段，不能只比 digest/attempt_id/几个标量。固定 scratch 必须真正覆盖原迭代结构；通用未封闭队列/任意递归比较不能以“streaming”命名就视为有界。数字充分性由 monitor 独审。
6. **arena/scratch一次预付本身不推出无 postissued Capacity**。候选发行后若仍可走 spend/view/equal/source_json 的动态账本，重复合法消费者会耗累计 work/view。要么代码明确后续没有这些可能失败的路径并以预付覆盖有限 call graph；要么限定只证明 arena/scratch allocation 不再动态追加，不宣称累计 CPU/work 同时闭合。不要把容量异常悄悄转业务通过或 LEGACY。

本补充未新增平台需求。仍只要求本候选自身的路径/生命周期/预算声明与实际代码一致。独审产品导入、测试、DB、Worker、Mock、G0/PB、prepare/commit 执行全部 0；仓库写入 0。
