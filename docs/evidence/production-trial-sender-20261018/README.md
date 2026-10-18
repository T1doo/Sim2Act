# 未安装 sender：原始离线资格与有限独审

基线 `94fa765de11e1e3cc42dac9070a28ec9c2b47647`；源码/测试冻结 `c6f946d4d5c90652dbc6ad9945499dc529cc8e4d`；普通分支 `dev/production-trial-sender-20261018`。[实现与准确边界](../../F2/ProductionTrialSender20261018.md)。

本片接通原 journal marker→现 InternModel/MockTransport→实际收到的 bytes→capture/journal 原子结算。只运行 test_only SQLite、原 Worker mock/live=false/token空及 exact MockTransport。旧配置解析、生产前置默认拒绝保持，没有 source producer、有效LIVE安装、真实凭据、模型或网络。所有 receipt 恒 business/live/dispatch/real-source=false；caller ALLOW和journal receipt不升级为来源事实或发送许可。

## 首轮8节点

8唯一节点/8次执行/8PASS/0FAIL/0ERROR/0SKIP，JUnit41.715秒、外层46.022090623秒。705输入/137生产及runner/guard前后零漂移；旧703输入只有journal私有提取改变，另外702输入/135生产字节保持。旧19/12矩阵未重跑、不累加，其资格不冒称为变更后journal的新全量回归。

- [精确命令/时间/退出码](author/run-1/execution.json)、[JUnit](author/run-1/junit.xml)、[stdout](author/run-1/pytest.stdout)、[stderr](author/run-1/pytest.stderr)、[runner](author/run-1/runner.py)、[冻结sender](author/run-1/frozen-source/src/sim2act/production_trial_sender.py)、[journal](author/run-1/frozen-source/src/sim2act/production_trial_journal.py)、[测试](author/run-1/frozen-source/tests/test_production_trial_sender.py)。stdout/子进程stderr保留既有Starlette deprecation警告。
- [输入before](author/run-1/inputs-before.json)/[after](author/run-1/inputs-after.json)、[helpers before](author/run-1/helpers-before.json)/[after](author/run-1/helpers-after.json)、[离线guard实现](author/run-1/offline_sender_guard.py)及[实际记录](author/run-1/offline-guard.json)。父guard阻止真实HTTPTransport/socket.connect/connect_ex/Settings.from_env；只允许确切合成adapter/MockTransport。父adapter5次、子adapter1次，共6次；Mock handler共5次，真实provider/model0。父guard有14条嵌套方法记录，不是14次请求。子guard覆盖HTTP/env/五个Intern方法，没有socket补丁，不能移植父socket覆盖声称。
- [正常原wire与raw/canonical几何及usage](author/run-1/actual-tmp/test_exact_adapter_capture_ato0/known-body-accounting.json)：含Unicode及空白，raw与canonical不同、usage=8，capture2+journal/cursor4同commit。原key重复不发、不改；迟到替换为同URL但非test_only Store时，事实仍只归原Store，替代engine SQL为0。公开receipt无正文。另有独立跨链篡改拒绝，拒绝时不写；[状态](author/run-1/actual-tmp/test_exact_adapter_capture_ato0/sender-state.json)。
- [新入口门状态](author/run-1/actual-tmp/test_fixture_and_actual_wire_g0/sender-state.json)：非fixture Store、LIVE/非空token、外部transport、自造来源对象、实际wire错误均在预留前拒绝，零新行/handler；错model仅额外纯派生检查，保usage8并UNKNOWN，没有扩成完整错误响应I/O矩阵。
- [marker提交后guard前cancel](author/run-1/actual-tmp/test_cancel_between_committed_0/marker-before-guard-cancel.json)：实际 Store.command(cancel)，handler0、marker保留、EMPTY UNKNOWN/halt。同节点EMPTY负例同时更改capture/journal同一错误SHA并重算seal，使跨链一致后仅空体派生拒绝；不是被跨链检查掩盖的负例。
- [guard后到transport的cancel窗口](author/run-1/actual-tmp/test_cancel_after_guard_may_se0/guard-to-transport-window.json)：原adapter guard实际结束，Mock handler入口用Event等另一线程的实际cancel，随后一次合成handler返回。已知body/usage8保留、accepted=false/halt，原key不重发。DB不能使guard与外部IO原子，本片不声称取消能撤回已可能开始的发送。
- [收到前缀后ReadTimeout](author/run-1/actual-tmp/test_adapter_received_prefix_d0/received-prefix-unknown.json)：现异步adapter实际保存含prompt=5的前缀，complete=false、UNKNOWN，completion/total=null；不把缺失补零、不重试。429/非200并未新增实测，原adapter可能只给空体/前缀，不能声称完整错误body。
- [capture后quota CAS失败](author/run-1/actual-tmp/test_capture_then_journal_cas_0/capture-cas-rollback.json)：先有一次fake send，再在结算事务注入原quota旧指纹；capture2+ledger2尝试写后quotaCAS0，六行全部回滚到已提交marker，全55表严格相同，无孤立capture。原key仍pending且只读，不推定未发送/退款。
- 两个真正crash窗口：[marker后adapter前证明](author/run-1/actual-tmp/test_crashed_sender_new_proces0/process-window-proof.json)、[收到body后归档前证明](author/run-1/actual-tmp/test_crashed_sender_new_proces1/process-window-proof.json)。各有独立[发送命令/退出17](author/run-1/actual-tmp/test_crashed_sender_new_proces0/crashed-sender-execution.json)/[退出23](author/run-1/actual-tmp/test_crashed_sender_new_proces1/crashed-sender-execution.json)、[恢复命令1](author/run-1/actual-tmp/test_crashed_sender_new_proces0/fresh-recovery-execution.json)/[恢复命令2](author/run-1/actual-tmp/test_crashed_sender_new_proces1/fresh-recovery-execution.json)及同目录stdout/stderr。实际4个新Python进程，发送端故意os._exit(17/23)是注入条件、不是pytest失败；恢复各exit0/adapter0，前后全55表严格同，原槽marked/pending revision2/quota2，无capture/settlement，不能由缺失推断免费或未发送。没有记录child PID，未声称有该原件。
- [闭合核对](author/closure.json)、[闭合脚本](author/close-evidence.py)、[Ruff](author/ruff-freeze.txt)。原件为实际断言、指纹、计数及receipt，不是逐行DB导出。普通fixture保护排除被控制/claim改变的runs/events；两个正常/EMPTY节点最终故意损坏新pair来测fail-closed，不冒称最终所有fixture均valid。

## 设计、修正与封存

[设计v1](author/minimal-design-v1.md)为receiver原子桥提案，[v2](author/minimal-design-v2.md)按父级要求加入marker→send，[v3](author/minimal-design-v3.md)追加事前wire/协议/binding收敛，均保留原字节；[设计输入](author/design-inputs.json)、[v2桥](author/design-v2-inputs.json)。v3 SHA256 `1293f629edc0d3fff177d9d95e03c94b60c9bcf02f5f4a6db2bed22138082663`。

四项静态P2（capture/journal跨链、EMPTY再派生、Run身份先于body、迟到动态Store替换）全部在冻结及第一次执行前修复。EMPTY测试oracle随后也在首跑前隔离。[事前观测](author/pre-freeze-observations.json)保留Ruff import与24个格式错误、AST辅助脚本选错docstring节点以及一次patch上下文拒绝；初始Ruff/辅助脚本/patch只有可见工具输出转录，未冒充单独原stderr。它们不是产品或pytest失败，修前产品未运行。

[作者AST提取桥](author/journal-extraction-bridge.json)核原校验表达式、原事务体、read owned标量锚及其他原函数一致。实际差别为校验进入事务，前置in_transaction断言；旧公有签名不变。不据AST一致声称重跑旧12节点。

[作者逐字复制](author-selection.json)包含62路径399218 bytes（61非DB原件388974 bytes及manifest），DB复制0，排除bytecode和pytest current别名。8物理fixtureDB只在外部保留，作者closure记hash/size，独审仅stat。[作者sealed清单](author/sealed-manifest.json) SHA256 `86837696b72c0b460154f7d6a467a45b371c88d9671ce87728cdf02edf741c06`，原目录此后停止写入。

[最终有限独审](review/final-independent-review.md)与[结构化结果](review/final-verification.json)均通过，未发现剩余确定P1/P2。[事前设计审](review/design-review.md)、[WIP四项P2](review/implementation-review-draft.md)、[Store binding补充](review/implementation-binding-addendum.md)、[修复审](review/implementation-review-fix.md)、[冻结静审](review/freeze-static-review.json)及[原审计脚本](review/final-artifact-audit.py)/[stdout](review/final-artifact-audit.stdout)/[stderr](review/final-artifact-audit.stderr)逐字保留。原journal校验/事务体AST桥及其它135生产blob一致已独立核实。705 before/after map一致；当前699非DB输入核SHA，6个旧db.gz只stat及基线/冻结Git blob元数据比对，未读或解压其内容；8个运行fixtureDB同样仅stat。独审没有另跑产品/pytest/网络、不打开DB，也不提前背书随后push。

独审纯文件脚本首版因6个旧db.gz触发过严后缀断言，停在读取前；[原脚本](review/final-artifact-audit-first.py)/[原stderr](review/final-artifact-audit-first.stderr)/[修正说明](review/audit-correction.json)均保存，不计产品或pytest失败。

[独审sealed清单](review/sealed-manifest.json) SHA256 `c7a4185399de34ccc31075d38ab1c36412c43dfa029aee2c86d117de7b91511d`，20原件86787B加manifest3230B，共21文件90017B。[独审复制](review-selection.json)与[全部复制清单](selection.json)列原绝对路径、size及SHA；合计83路径489235 bytes，不含本README及selection元数据，数据库复制0。作者与独审两原sealed目录均已停止写入，仓库保留逐字副本。

## 未执行范围

未执行真实provider/model/账户/费用/语义、可信source producer或LIVE sender安装、完整generation/source/cold/UI、PostgreSQL SQL/并发、Windows/native、远端CI。旧19/12矩阵、旧永久取消窗口及旧满盘未落盘独审没有重跑或补回。source ALLOW只作内部合成数据，双镜像不是签章，也不抵抗管理员整体改写可信行。未来真实来源及安装需独立实现审查，不作为本片离线代码未交付的借口；整体F2及生产LIVE不由本片签收。
