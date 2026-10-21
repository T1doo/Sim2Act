# Native accounted 扫描 frontier：6570 后候选的来源设计独审

结论：**CONDITIONALLY_FEASIBLE_FRONTIER_DESIGN_ONLY**。可以继续实现默认关闭的候选；当前尚无实现字节可签。允许减少的仅是已完整转交不可变 owned 值、且其所有后续消费者已改用该值的纯重复扫描。不能按 run_id、内容相等或某个旧对象 id，一概跳过其他仍为 mutable 的原根。本报告不批准运行 G0/Mock/完整 prepare/commit。

只读基线：6570b7072e3cd415fbbcb3a130e8a80d9ad8be79，阅读时仓库干净。独审没有导入产品、没有测试/DB/Worker/Mock/PB/G0，未修改源码；只生成本 /tmp 报告。

## 原位置与整族路由

natural_spec_runtime.py:2718 Source 原 producer → :2724 expected_recipe/model_dump → :2726 原 recipe 验证 → :2728 versions SQL → :2730 exact backend `[VERSION]*3` → :2731 Generate 原 producer，次序和失败前缀必须保留。先前 `_bounded_cohort`/`_select_cohort` 连续调用两个 producer，不能直接替换此段，否则 recipe/version 失败时会额外执行 Generate。应在原两个位置各暂存一次 `_owned=None` 完整返回，在第二个完成及后置 fullguard 后才做整族 route；原 interstitial `_base`/pin 继续观察已有 Source 原值。

发行前：两 role 的原 producer 和原完整 guard、Source→recipe→backend 原失败顺序、完整 raw/typed 资格与预期 pin 比较均完成。预算/表示 unsupported 才允许 joint LEGACY，保留原 facts、无 producer 重读。发行后任何资格/容量/生命周期失败仅 close。不能先发 Source 后等 Generate，也不能在成功选择后回退。

## 可以替换的纯重复扫描候选

| 原位置 | 有条件可替换部分 | 必须保留的合同 |
| --- | --- | --- |
| CGR input_bytes/key 对 `cold-trial:accounted-source/generate` 的专属子树 | 完整采纳后用同 graph/epoch/role/registry 的不可变根见证取代重复 raw codec | 每次 fresh 动态边界及剩余 mutable frontier 扫描；根边不能换绑，handle/packet 必须仍属同 scope |
| `_ColdTrialGraph._typed_parameters` :2493/:2499 | `_graph_trial_accounted_models_from_raw` 重建、typed snapshots 全链重扫 | exact family、role、scope、registry、packet/ref 锚；无 raw 事实再被消费者使用 |
| `_accounted_fields` :2586 与 `_fields` :2605 | accounted 值重复 model_dump/Run/Attempt 字典重建；complete.generated/source/generation.run 的重复展开 | complete 其他字段、generation raw/metadata/frozen/material/history/marker 等仍完整保留 |
| `natural_live_admission._graph_trial_stage_models_from_raw` :1474 / stage raw :1493 | stage 中真正被替换的 owned Generate/Source Run/actual/chains/NS 重建扫描 | stage 9 元组、Cold vs Source 分支、原 binding/raw/metadata/frozen/extraction 身份/值 joins；Cold job 不属于此次 owned accounted 结果 |
| `_LegacyOracle` :383 及 mode.assert_current :515、pin_legacy_complete :654 | 新 native 分支对已无消费者的 accounted 旧原 facts、原 typed models、raw complete 的重复 oracle 扫描 | 旧实验/默认路径不动；新分支须由完整原采纳和逐消费者等价比较承担证明；不能连带删 archive/usage/domain checks |

现 6570 的 `_OwnedPrewriteMode.assert_current` 仍两次 fullcheck 并 `_LegacyOracle.assert_current`，`pin_legacy_complete` 又把 raw roots 放回完整图；因此只替换两个顶层 key 不会完成所需闭包，也不能声称已消除旧扫描。

## 不得顺带跳过的别名与独立根

下表均有原 mutable 对象或独立副本的消费者。除非未来补丁逐项迁移并证明后续无原读取，否则必须留在 mutable frontier，不能因“同 Run”合并。

| 根/对象 | 原来源与当前消费者证据 |
| --- | --- |
| Generation `reader.run`、`run_pin`、`source_pin.run`；`generation:<rid>:run`、`:0:complete-source`、`:raw-*` | goal_applications.py:789–847 初始化/完整 `dict(run)==run_pin`；:825–836 source_pin 身份、完整 Run/contract/material；:911 source() 仍 recheck project/authorities；:1146 source_pin deep copies。它们不是新 accounting producer 返回的同一 RowMapping。 |
| `original-native-audit:<app>` 内 run/attempts/operations/events/contract 等 | natural_spec_runtime.py:2030 native audit add；goal_applications.py:740–780 raw seed checks；pa_spec_apps 的原 audit/origin 仍消费完整内容。不是仅 accounted2/3条 chain 的副本。 |
| Source `_ColdRunFacts.job` 与 `run-facts:<rid>`、其 `:attempts`/receipt-operations/其余 lazy raw/manifest proofs | natural_spec_runtime.py:296–415 保存 exact job 和每条 raw pin；:341–378 身份、注册完整性及 Limits 检查。不得把同 rid 的 accounting packet 作为这些原对象“不变”的证明。 |
| Source/Cold `binding-prefix:*` job、bound job、commit:* run/binding、pb-use:* job | app_jobs.py:700/720；pa_spec_apps.py:1475、2043；pb_natural_uses.py:1138。原 role/limits/instance/release/input/audit 仍消费，且含未属于两族的 Cold job。 |
| PB Source prefix.job、typed binding/outputs/proved/proof、audit.rows/original_audit_rows，以及 complete.source_facts/source_audit/native_audit/source_outputs/source_proved | pb_natural_specs.py:655/:669 prefix/fields、:675/:684 typed fields、:690/:700 source fields、:423 audit.fields；natural_spec_runtime.py:2610 `_fields` 将它们再次嵌入。保留完整独立证据链与具体对象身份。 |
| complete 的其他根以及 stage 非 owned 字段 | binding/source_binding、cold_job、extraction draft/target/goal/body、use review/manifest/material、journal ledger/cursor/revision、roles、source_proof。尤其 natural_source_archives.py:465 对 source_proof 是 complete 内同一对象；_typed_parameters:2547 相同身份约束。 |

即使物理共用了某个嵌套 mutable dict/list，只要还有一个非 owned 根读它，该路径仍需全扫描。反过来，同值但不同对象也不能凭值相等合并 provenance。不可变 bytes/str 共享无需假造可变别名，但新扫描 namespace 的编码别名形状也不应冒称旧原 codec 字节一致。

## 必须保留的动态/业务/数据库边界

- `_ColdGraphRead.check` :1812–1841 的 exact inputs/roles/phase、scope nonce、store/engine/settings/binding/worker、stop、connection/transaction/driver、thread、total_changes、write epoch、source read token，以及所有未迁移 frontier 的 fresh 内容检查。不能只缓存身份/长度/mtime/digest 代替 mutable 全扫描。
- `add` :1847–1861 原先 fullcheck 后新边 `forbid_root`、cycle/unsupported/container 完整验证、不可重绑、fresh repin。不可因部分子树成为 owned，就跳过新根别名/隐藏 RowMapping data 的 root backedge 检查。 owned 根只能是已受信精确不可变值，不是 caller 提供 digest/boolean/字符串 marker。
- 原 `_graph_run_context` :1007 的 approval/phase、实时 stage 重建、Run 锁行/owner/version/fence、time 与全部 deadline；`_graph_pb_accounting` 原 approval、Generate marker SQL、journal/source gate；`_graph_resolve_trial_source` 原授权、source phase、extraction pair/IDs、scope gates、proof-authorities、期满检查；没有一个能以 packet 替代。
- Source consumer 的 evidence_mode、当前 SQL archive key 集、完整 ordered request/response bytes、canonical/usage/slot/identity/outcome joins、archive receipt/ledger 相交、typed schema 都保留。 `_LegacyOracle.assert_archive` 是重复证明，但新 owned `_archive_chain` 的业务条件不是可以一起删除的“扫描”。
- 所有 fullguards 调用位置、原 timer/lease、stop/unknown、SQL次数与有序原参数不应因 route 换动。扫描实现减少是候选变量，不是减少 live gates 或取旧结果当权限。

## frontier 实现的最小可审条件

新显式模式必须绑定 exact graph/epoch/phase、两角色完整 registry、不可变 packet；每次检查固定边的 identity/role/ref，并完整遍历仍可变的剩余根。不可仅按名称前缀、相同 run_id、`id` 集合或内容摘要全局 prune。必须给出具体被替换路径白名单；complete/stage 的被替换位置与 consumer 构造同步，所有未改字段继续原检查。旧默认 None 路径及旧 codec namespace 保持原样；新 native frontend 的 representation/continuity namespace 显式分开。

必要局部验证包括：Source/recipe/backend/Generate 原失败前缀及每 producer一次；joint Legacy/Owned；发行后无fallback；每个 owned边换绑/跨scope/角色/ref/ledger伪造；每个保留根的同身份嵌套 mutation；跨界共享 dict/list（owned复制后原alias仍被别根使用）必须拒绝；新add嵌套/hidden-row root回边/cycle；原 Source archive/usage/Slot全字段；非 owned Cold Run/version/lease与权限撤销原错误。此清单仅供根侧合法局部测试设计，不批准真实完整 prepare、trial commit、G0或Mock。
