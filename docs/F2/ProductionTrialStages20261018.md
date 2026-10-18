# P-A 原控制器 3+2+2：未合格的有界开发检查点

本片 **NOT_QUALIFIED**。源码冻结为 `cdcae63e6ca6294b98ee6764b832d2d001e4de05`，分支 `dev/production-trial-stages-20261018`，基线 `4bb3c26f5f67511795771c9187537aee4e852590`。最终只封存、独审和推送；不再优化或重跑。此前统一目录、逐次材料及结果入口的已有交付不等于本片重新通过浏览器验收。

## 实际达到的位置与唯一最小阻断

最后一次有界 mock 整链实际经过原 InternModel/MockTransport 的 **generate3 → Source2 → Cold2**，共7次请求。Source 两次操作均 VERIFIED，原 Source Run 已 SUCCEEDED，夹具内 inspect 成功；第二份材料及完整 Goal 由原 per-use 入口显式提交。Cold 两次请求和本地 merge_pick/check_pick 均 VERIFIED，但最终 SAVE/结果事务没有提交。Cold Run `run_569084ed382a40ae80a0560eed94655a` 留在 RUNNING/version1/result=null。

Cold 最终当前准入 `check_run` 从 `1792342466.8449943` 到 `1792342498.5953877`，耗 **31.750393177秒**，报 `VERSION_CONFLICT`。被动记录栈为 `production_trial_policy.py:161 → natural_live_admission.py:919 _run_context → require`。最后一次实际提交的 heartbeat lease 截止 `1792342490.7291622`，检查结束已晚 **7.866225481秒**；原 Cold Run 总 deadline `1792342576.544284` 尚未到。

可以确定的是：Cold 最终 SAVE 的当前验证未能在原30秒 lease 内完成，原保护拒绝了结果提交；该操作已拒绝，未处于待处理状态。记录未保留外层 caller 和 rollback 中所有临时字段，因此不声称已排除所有并存条件或证明唯一布尔分支。下一最小工作是定位该当前验证耗时，使既有结果事务在原 lease 内完成；本片没有启动这个后续。

七份已知响应及 usage 已保存，journal 计账 accepted 不等于业务验收。没有放宽 lease、Run deadline、权限、版本、fence、CAS 后 fresh 检查；没有补旧 Run、重放七次请求或恢复重发。

## 本片实现范围

与基线相比，8个生产文件改变，130个生产文件字节未变，新增1个测试文件。`JournalTrialBinding` 限定 P-A TrialContract/V2，名称为 `UNINSTALLED-pa-journal-trial.v1`，只接受同一 test SQLite Store、固定 Settings、空 token、live=false 及 exact MockTransport；新绑定拒绝 P-B。它把新 journal/capture 的实际调用接回原 Worker/GA/NS、archives 和结果控制器，不新增 executor、Grant、第二预算或真实安装。

原 Worker claim、完整 Goal/材料/批准、owner/project/runtime、Run version/fence、30秒 lease 与当前权限边界继续生效。响应完整 body 和 usage 先按不可变事实保存，再由原业务合同解释；Store 替换会 poison 新绑定，外来 engine 不执行 SQL。完整 generation 及 Source stage proof 复用仅限同一 Store、连接、事务、线程及写入 epoch 的同步读取段；权限仍须重新验证。缓存不能跨写入或事务。原 `_source_scope_gate` 实体正文保持一致；这些静态事实不代表新增缓存撤权/到期窗口已通过运行验收。已有 P-B 读取段可能共享新增 marker，不能据此声称所有旧 P-B 路径字节未变。

详见 [冻结范围](../evidence/production-trial-stages-20261018/author/final-freeze-scope.json)、[最小设计](../evidence/production-trial-stages-20261018/author/minimal-design-v7-source-scope-read-segment.md)及 [独审](../evidence/production-trial-stages-20261018/review/final-independent-review.md)。

## 实际测试

| 最后一次组 | 实际结果 | 运行范围 |
| --- | --- | --- |
| run-8-chain | 1 fixture ERROR；B未执行 | 原3+2+2达到Cold最终保存前；同Run最终结果/owner回读未执行 |
| run-8-negatives | 2 PASS | C：已知计账不能接受错误业务schema；D：同SQLite URL独立第二Store隔离，foreign SQL=0；各handler1且无重发 |

整链命令为 `timeout --kill-after=15s 900s /workspace/sim2act-venv/bin/python -m pytest -vv -s --maxfail=1 -p offline_stages_guard --basetemp=… --junitxml=… tests/test_production_trial_stages.py::test_actual_pa_three_two_two_reaches_existing_results_and_pending_owner tests/test_production_trial_stages.py::test_fresh_actual_prefix_rejects_incomplete_mixed_or_changed_proof_without_writes`。精确 argv 见 [execution.json](../evidence/production-trial-stages-20261018/author/run-8-chain/execution.json)。开始 `2026-10-18T16:45:05.960691+00:00`，结束 `16:55:07.079374+00:00`，pytest 594.87秒，outer 601.118352056秒，exit1；900秒 timeout 未触发。负向组 pytest16.01秒、outer21.605561308秒、exit0。现在无活动测试命令。

计划4个唯一节点，实际3个；B全部9个反证窗口 **NOTRUN**，包括新增 scope-cache 的真实撤权/到期窗口。不得把fixture错误写为A通过，或把静审视作这些运行窗口通过。最终两组652输入/138生产文件的前后哈希一致，runner/guard无漂移；冻结 Ruff9文件及 diffcheck 通过。完整历史为 **14次节点执行：5 PASS / 8 ERROR / 1 fixture FAIL**，累计 mock adapter **33次**，最后两组9次（链7+负向2），真实模型 **0次**，旧19/12/8/9矩阵重跑0。

保留了run1到run8的每次失败及修正：claim绑定、checker协议识别、Core/Public Run key、租约时序、Source验证过期、一次第二Store夹具构造错误、Cold reserve未提交和本次Cold最终准入错误。没有删除失败或以最后负向通过覆盖它们。原始证据入口：

- [整链stdout](../evidence/production-trial-stages-20261018/author/run-8-chain/pytest.stdout)、[JUnit](../evidence/production-trial-stages-20261018/author/run-8-chain/junit.xml)、[被动IO/heartbeat/admission记录](../evidence/production-trial-stages-20261018/author/run-8-chain/offline-guard.json)。
- [负向JUnit](../evidence/production-trial-stages-20261018/author/run-8-negatives/junit.xml)、[stdout](../evidence/production-trial-stages-20261018/author/run-8-negatives/pytest.stdout)、[guard](../evidence/production-trial-stages-20261018/author/run-8-negatives/offline-guard.json)。
- [全历史汇总](../evidence/production-trial-stages-20261018/author/qualification-summary.json)、[作者结论](../evidence/production-trial-stages-20261018/author/checkpoint-conclusion.md)、[最终独审核验](../evidence/production-trial-stages-20261018/review/final-verification.json)。

## 证据边界

`closed-checkpoint-facts.json` 是所有本轮任务关闭后，作者使用标准库 sqlite `mode=ro` 从本轮合成夹具导出的60条 archive、7个 Attempt及Run元数据。DB SHA 前后相同。它是作者事后导出，**不是独审重建或整链合格证明**。七份 raw body 与 canonical body 的哈希均另从字节复算，且各自不同。详见 [关闭后导出](../evidence/production-trial-stages-20261018/author/closed-checkpoint-facts.json)与 [纯文件body核验](../evidence/production-trial-stages-20261018/author/closed-checkpoint-body-audit.json)。所有DB保留在外部并记录size/SHA；本Git包复制DB数0。

各轮只读 profile 是诊断，不是产品资格或性能保证。不同入口的原/优化profile不构成等价基准；双重reauth WIP的wall时间反而更长。该WIP整文件按一行差异重建并与运行时已记录SHA相符，明确标为 reconstructed；首轮顶层runner按当轮保存副本恢复并核原记录hash，后续各轮启动保存精确副本。旧满盘环境未访问，其最后独审报告 **NOT_RECOVERED**，未声称补回。早期 `delivery-notes-draft.md` 及准备的PASS-only模板均不是最终结论；`check_closed_outputs.py`、`write_final_docs.py` 未执行。

作者与独审证据分别封存，再逐文件校验和复制；清单、SHA、实际数量见 [证据README](../evidence/production-trial-stages-20261018/README.md)。独审仅执行有限纯文件/源码核验，不打开DB、不跑产品或模型，不预先背书后续Git推送。

## 真实API及未执行范围

真实API是独立前置条件：用户已有本次授权，环境已配置非空 `INTERN_API_TOKEN`，只记录存在/非空布尔值，未显示、复制或hash其值；离线runner刻意移除真实凭据。本片真实模型POST **0**。仅做过两次无凭据公开Chat根GET，分别因DNS `errno -3` 和有限重试的proxy tunnel `403 Forbidden` 失败，之后停止；没有替代路由或绕过拒绝。Git默认网络与该API访问结果分开记录。

还需确认当前同账户身份和剩余输入/输出额度、实际强制无新增费用及禁止收费fallback的有效事实，并完成真实source/controller受审安装。当前新绑定明确test-only/Mock/UNINSTALLED。这些未知项不能用用户授权、历史额度、其它产品价格或配置token存在代替。候选约束仍为最多7请求、每次最多1024输出/总7168、间隔至少60秒、无自动重试，余额或费用未知时发前拒绝。见 [安全前提元数据](../evidence/production-trial-stages-20261018/author/real-prerequisites/selection.json)。

本片没有执行真实语义/人工验收、真实场景、Windows/native、PG、远端CI、新P-B资格/AT10或浏览器入口重验。没有改main、强推、部署、新增费用、凭据或安全权限，也未访问旧满盘实例。该普通开发检查点可供下一最小修复复核，不能称完整F2、完整3+2+2产品交付或LIVE。
