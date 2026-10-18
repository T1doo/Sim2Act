# 未安装持久 journal：原始执行与有限独审

基线 `080ea7b184a7476019431c1803b4bfe4864afbd9`；源码/测试冻结 `12958af924fad425fa619adccd1841fb8f8228a8`；普通分支 `dev/production-trial-journal-20261018`。[实现及执行边界](../../F2/ProductionTrialJournal20261018.md)。

控制器只加载可信服务端 ledger/cursor，新写入以精确revision及旧fingerprint对四镜像作同事务CAS；不接受caller状态替换。它仍未安装到API/Worker，没有来源producer、sender、凭据或有效LIVE许可，所有回执均live/dispatch/real-source=false。只有合成内部来源结果、wire、usage和reservation身份，没有实际生产Attempt或模型响应。

## 一次实际执行

12唯一节点、12次执行、12PASS/0FAIL/0ERROR/0SKIP；JUnit47.523s、外层50.645257132s。703输入/136生产及runner/guard前后零漂移；原701输入/135生产逐字同基线。旧内核19唯一/20执行历史资格原样保留，未重跑、未累加，也不借其顺序取消用例声称并发。

- [精确命令、退出码与时间](author/run-1/execution.json)、[JUnit](author/run-1/junit.xml)、[stdout](author/run-1/pytest.stdout)、[stderr](author/run-1/pytest.stderr)、[runner](author/run-1/runner.py)、[冻结控制器](author/run-1/frozen-source/src/sim2act/production_trial_journal.py)、[冻结测试](author/run-1/frozen-source/tests/test_production_trial_journal.py)。stdout保留一个既有Starlette deprecation警告。
- [执行输入 before](author/run-1/inputs-before.json)/[after](author/run-1/inputs-after.json)、[helpers before](author/run-1/helpers-before.json)/[after](author/run-1/helpers-after.json)、[运行级离线哨兵](author/run-1/offline-guard.json)及[实现](author/run-1/offline_policy_guard.py)。HTTPTransport、Settings.from_env、InternModel入口attempts=[]；子进程另有相同五个真实模型入口及IO guard，实际记录均为空。
- [同Attempt两Store竞争及完整历史](author/run-1/actual-tmp/test_two_stores_same_attempt_o0/concurrent-same-attempt.json)：一新一重复、一次槽扣减；后续原key/marker/完全同Outcome重复不写任何行，旧revision不会变成新send许可。
- [同账户两project/两trial首预留争抢](author/run-1/actual-tmp/test_one_account_across_two_pr0/cross-project-account-contention.json)：一胜一RATE_LIMITED、一个共享cursor。先用winner读正向校准SQL观测，再确认空/伪造trial拒绝且cursor SELECT为0。
- [ledger写后quota CAS旧指纹冲突](author/run-1/actual-tmp/test_stale_revision_and_mid_pa0/atomic-cas-rollback.json)：四行同事务回滚，全55表严格相同；另拒绝旧revision的新Attempt。ledger/quota两种缺seal节点均拒绝且不修复；[ledger缺镜像](author/run-1/actual-tmp/test_missing_mirror_is_rejecte0/journal-state.json)、[quota缺镜像](author/run-1/actual-tmp/test_missing_mirror_is_rejecte1/journal-state.json)。
- 真实新Python进程：[pending stdout](author/run-1/actual-tmp/test_new_process_pending_unkno0/pending-child.stdout)/[stderr](author/run-1/actual-tmp/test_new_process_pending_unkno0/pending-child.stderr)，[UNKNOWN stdout](author/run-1/actual-tmp/test_new_process_pending_unkno0/unknown-child.stdout)/[stderr](author/run-1/actual-tmp/test_new_process_pending_unkno0/unknown-child.stderr)。只read及原Attempt重复，parent前后全表相同；revision1/3，UNKNOWN保prompt=5、completion/total=null、halt及原quota时间，不自动mark/send或退款。完全同结算重复只读，改Outcome被拒绝。
- 六种独立连接竞争trace：[marker先/cancel](author/run-1/actual-tmp/test_two_connection_marker_con0/linearization.json)、[marker先/lease](author/run-1/actual-tmp/test_two_connection_marker_con1/linearization.json)、[marker先/fence](author/run-1/actual-tmp/test_two_connection_marker_con2/linearization.json)、[control先/cancel](author/run-1/actual-tmp/test_two_connection_marker_con3/linearization.json)、[control先/lease](author/run-1/actual-tmp/test_two_connection_marker_con4/linearization.json)、[control先/fence](author/run-1/actual-tmp/test_two_connection_marker_con5/linearization.json)。测试记录winner已写并持锁、另一连接已尝试BEGIN、释放前两者均活动及实际返回顺序；实际Store.command取消与明确fixture lease/fence SQL分开。settle均保usage=8、拒收/halt、不退槽；marker先才有attempted=true。这只是marker/数据库控制线性化，不是provider发送原子性。
- [闭合核对](author/closure.json)、[闭合脚本](author/close-evidence.py)、[Ruff](author/ruff-freeze.txt)。普通场景严格比较其他表；fixture收尾排除被实际control/SQL改动的runs/events，CAS负例全55表相同。原件是逐镜像revision/指纹及执行断言，不是全行导出、逐操作55表窗口或独立数据库重建。

## 设计、修正与完整性

[原设计](author/minimal-design-reviewed-v1.md)、[修正读边界后的设计](author/minimal-design.md)及[精确桥](author/design-revision-bridge.json)分别保留。旧设计原字节以逆向单句替换恢复，SHA与独审事前记录一致，不冒作原封存复制。独审静态发现原read可让空trial读取共享cursor；冻结前改为自有双标量锚前置，没有动态运行修前代码或倒签测试。[其他事前观测](author/pre-freeze-observations.json)如实区分import排序提示、缺路径搜索和一次工具JS解析错误；初始Ruff的stderr未另捕获，只有工具输出转录元数据，修复输出保留。

[作者逐字复制清单](author-selection.json)含56路径372265 bytes（55非DB原件363044 bytes加manifest）；数据库复制为0，排除pytest current symlink aliases及bytecode。12个物理fixtureDB仅在外部保留，作者closure记录其hash/size，有限独审仅stat。

[作者sealed清单](author/sealed-manifest.json) SHA256 `c5057f6b9c371ff03e5f7bef1e8eeb660fc71a613854cee096cb82d3e8235d91`。原封存目录停止写入，仓库只是逐字副本。

[最终有限独审](review/final-review.md)与[结构化结果](review/final-verification.json)通过，无当前确定P1/P2；[设计审](review/design-review.md)、[WIP P2](review/implementation-review-draft.md)、[修复](review/implementation-review-fix.md)、[冻结审](review/freeze-static-review.json)均保留。[纯文件/Git audit](review/audit-qualification.py)实际exit0，保存[stdout](review/audit-qualification.stdout)、[stderr](review/audit-qualification.stderr)及[逐项核对](review/qualification-verification.json)。独审未另跑产品/pytest/网络或打开DB，没有独立重建原行。首次读错run-1日志路径的[工具错误来源](review/read-path-correction.json)明确为可见输出转录，非原始重定向stderr，不计产品或测试失败。

[独审sealed清单](review/sealed-manifest.json) SHA256 `8cfef6e97854ba6cd90caa709f5a3073e17f93739b8f14570bb82491a5b4cf68`，含清单16文件50954B。与作者56份合计72个逐字复制路径、423219 bytes；[完整selection](selection.json)列出原绝对路径、size和SHA，不含本README与两份selection元数据。两份原sealed目录均停止写入，数据库复制为0。独审限定冻结源码和现有原件，不提前背书其后的push或部署。

## 未覆盖与后续依赖

本片完成合成SQLite持久journal及有界并发/新进程只读资格。PG SQL及其行锁并发、Windows/native、远端CI、真实source/账户/费用/模型/语义、完整source/cold/UI链均未运行；没有重跑旧synthetic恢复矩阵或旧永久取消窗口，旧满盘未落盘独审仍未补回。

真实来源producer、受审sender及未来安装仍需各自实现和独审，但其缺失不阻止本轮离线代码。namespace双镜像不是签章，也不防数据库管理员同时回滚全部可信行；全局账户串行只覆盖本journal，不能冒称系统全部路径。现有试验endpoint/model、权限和caps没有放宽，整体F2与生产LIVE不据此签收。
