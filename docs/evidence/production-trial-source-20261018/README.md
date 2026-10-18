# 未安装账户来源：原始离线资格与有限独审

基线 `9df8a2ecca3e2e9905200398aa7c7a4d53b891a0`；源码/测试冻结 `ab838215af13c04281bbad441fd75b9a97839890`；普通分支 `dev/production-trial-source-20261018`。[四角色合同、实现及剩余阶段链](../../F2/ProductionTrialSource20261018.md)。

本片只实现固定服务端synthetic fixture loader/verifier；当前未给定受信官方来源接口，没有伪造真实producer。身份确认、合法免费权益、强制零收费及禁付费fallback、撤销与有效期各有原始证据角色。issuer/hash/两镜像不是出处或费用事实，内部ALLOW只代表合成数据合同成立。生产resolver/preflight保持默认拒绝，无HTTP source信任对象、任意callback、凭据、权限、LIVE或安装变更。

## 首轮九节点

九唯一节点/九次执行/九PASS/零FAIL、ERROR、SKIP；JUnit38.319秒、外层43.323537305秒。707输入/138生产及runner/guard前后零漂移；旧705输入仅sender改变，其余704输入/136生产字节同基线。旧19/12/8矩阵未重跑、不累加；新边界节点只对抽取后旧数据入口做一次小兼容实际调用，不借此签旧完整矩阵。

- [精确命令/时间/退出码](author/run-1/execution.json)、[JUnit](author/run-1/junit.xml)、[stdout](author/run-1/pytest.stdout)、[stderr](author/run-1/pytest.stderr)、[runner](author/run-1/runner.py)、[冻结source](author/run-1/frozen-source/src/sim2act/production_trial_source.py)、[sender](author/run-1/frozen-source/src/sim2act/production_trial_sender.py)、[测试](author/run-1/frozen-source/tests/test_production_trial_source.py)。stdout保留一个既有Starlette deprecation警告。
- [707输入before](author/run-1/inputs-before.json)/[after](author/run-1/inputs-after.json)、[helpers before](author/run-1/helpers-before.json)/[after](author/run-1/helpers-after.json)、[离线guard](author/run-1/offline_source_guard.py)及[实际记录](author/run-1/offline-guard.json)。HTTPTransport/socket.connect/connect_ex/Settings.from_env禁止尝试=[]；只允许现InternModel及exact MockTransport/固定synthetic占位。九条嵌套方法记录对应三次adapter请求、三次Mock handler：新source路径两次、旧数据入口兼容一次；真实provider/model0。本片无新子进程，不继承旧crash窗口数量。
- [正常原始四角色bytes](author/run-1/actual-tmp/test_owned_raw_source_contract0/raw-synthetic-source.json)与[实际source→sender证明](author/run-1/actual-tmp/test_owned_raw_source_contract0/source-to-sender.json)：从raw重算SHA、绑定及结果，600秒前观察仍有效，公开Resolution无正文且real/live/dispatch=false。四次load分别位于reserve/mark/guard/settle四个事务，每处使用该调用方原c；三次journal操作观测同一c及相同已加载source。正常usage8接受仅为accounting，business=false。必要未知/foreign issuer/伪造ALLOW与PRODUCTION标签均拒绝升级；删除source后原key直接历史，loader调用0、全55表不变、handler不增加。
- 六类必要来源拒绝：[缺源](author/run-1/actual-tmp/test_unusable_server_source_ne0/source-rejection.json)、[错账户](author/run-1/actual-tmp/test_unusable_server_source_ne1/source-rejection.json)、[跨项目](author/run-1/actual-tmp/test_unusable_server_source_ne2/source-rejection.json)、[过期](author/run-1/actual-tmp/test_unusable_server_source_ne3/source-rejection.json)、[撤销](author/run-1/actual-tmp/test_unusable_server_source_ne4/source-rejection.json)、[角色不一致](author/run-1/actual-tmp/test_unusable_server_source_ne5/source-rejection.json)。六个窗口均实际走新入口至原journal/policy拒绝，全部55表严格相同、handler0。除缺源外同目录保存该窗口实际raw-synthetic-source.json，可复算原bytes/hash；并非caller摘要。跨项目实际有另一owned项目及source pair，SQL先正向校准命中，再核缺自有锚时外国payload读取0；复制外国raw到自有pair仍DENY。
- 角色不一致节点另恢复[valid raw](author/run-1/actual-tmp/test_unusable_server_source_ne5/raw-valid-before-mirror-corruption.json)，只将一侧fingerprint改d64、保两requestFP标量锚，实际命中pair VERSION_CONFLICT→SOURCE_INTEGRITY/UNKNOWN；新入口拒发，以损坏后baseline全55表相同、不自动修复。这与两份seal都正确但角色不一致的第一窗口分开。
- [guard后服务端status撤销](author/run-1/actual-tmp/test_source_revoked_after_guar0/source-late-revocation.json)：一实际Mock handler可能已发，handler内提交source撤销；接收事务重读后保body/usage8、accepted=false/halt，duplicate历史全55表不变、handler总1。数据库guard与外部IO没有原子性承诺，来源失效不丢已接收事实，不退款、不重发。
- [入口与默认生产边界](author/run-1/actual-tmp/test_new_entry_stays_offline_a0/source-boundary.json)：非fixture Store、LIVE/非空token/外部transport均拒绝，原production_preflight仍因缺真实来源LIVE_BLOCKED。source pair读取点显式合成注入PERMISSION_DENIED，验证其向外传播、未变UNKNOWN；这些拒绝全55表不变、handler0。随后一次原数据入口实际adapter兼容通过，另计一次Mock，仍非LIVE。
- [作者闭合](author/closure.json)、[闭合脚本](author/close-evidence.py)、[最终Ruff](author/ruff-mirror-refinement.stdout)。严格全行相等来自实际测试断言、receipt和镜像FP，不是全行导出或独审DB重建。fixture收尾对其他54表（包括runs/events）及非本片元数据严格比较；正常尾态刻意删source，角色不一致尾态故意保留损坏指纹，不声称全部最终source有效。

## 事前设计、修复与封存

[设计v1](author/minimal-design-v1.md) SHA256 `fb704f953ae475dce830dd414108ed50b06658f6193bc542e0eb0192a1d2a98a`，先独立审查再改src。完整业务阶段source与本片账户费用source明确分开；未来真实角色提供方/可信读取及批准需另审，不由fixture、标签或hash替代。原始四角色是合成验证合同，不是已核官方schema。

[事前观测](author/pre-freeze-observations.json)保存静态P1及格式/工具问题。P1为原key历史对三项_ledger返回值解包成四项，第一次执行前修正；独审原行只有可见工具转录，保存片段实际为修后，未冒称保有未修整文件字节。首轮import/style失败、格式后剩F401/E731均在首跑前修复，[style命令退出](author/style-executions.json)/[修正](author/style-corrected-executions.json)及各stdout/stderr保留；外层AssertionError只工具输出转录。另一次patch上下文验证失败无修改，读实际格式后一次应用，不是产品测试失败。

[作者逐字复制清单](author-selection.json)为75路径386413 bytes（74非DB原件374306 bytes加manifest12107 bytes），DB复制0，排除bytecode及pytest current别名。九物理fixtureDB只在外部保留，作者closure有hash/size，独审仅stat。[作者sealed清单](author/sealed-manifest.json) SHA256 `7a0d61b98fcaf4405be5e40df9e8b6f9c5a5f0cb97ca06b43015deb939d0fa65`；原目录停止写入，仓库仅逐字副本。

[最终有限独审](review/final-independent-review.md)及[结构化复核](review/final-verification.json)通过，无剩余确定P1/P2；[事前设计审](review/design-review.md)、[WIP发现](review/implementation-review-draft.md)、[修复记录](review/implementation-review-fix.json)、[冻结Git/AST审](review/freeze-static-review.json)与原件脚本/实际stdout/stderr均逐字保存。原sender九函数AST保持；接收主体仅加固定source重读，原数据入口签名保持，其余136生产blob同基线。独审复算九JUnit及七份实际raw源JSON、source四处同原c及实际拒绝窗口，不另跑产品、pytest、网络或打开DB，不提前背书随后推送。

707 before/after map相同，当前701个非DB输入独立SHA匹配；六个旧db.gz仅stat和基线/冻结Git blob元数据核对，未读/解压其内容；九个运行fixtureDB同样仅stat。独审报告输入段的“实际served源”是沿用UI措辞，准确范围是当前仓库源码、frozen-copy与Git blob，本片没有页面served assets或页面HTTP验收；结构化结果及审计脚本范围正确。封存原件不回写，解释在此保留。

[独审sealed清单](review/sealed-manifest.json) SHA256 `573b0b234ec381a033ea92f3477514fbfcf5019b7f93961777b92c3a9c62843a`：13原件64738B加manifest2191B，总14文件66929B。[独审复制](review-selection.json)及[全量复制清单](selection.json)列原绝对路径/size/SHA；与作者75份合计89路径453342 bytes，不含本README及selection元数据，数据库复制0。两份原sealed目录均停止写入，仓库只保逐字副本。

## 未执行与后续

未执行真实账户身份/权益/强制零费/撤销/费用/模型/语义、真实producer或LIVE安装、完整generate3/source2/cold2及UI、PG、Windows/native、远端CI。旧19/12/8矩阵和旧永久取消窗口不重跑，旧满盘未落盘报告不补回。新loader没有真实来源信任根；数据双镜像不抵抗管理员整体修改。本片可交付离线代码，后续完整阶段证据桥仍可离线推进，整体F2及生产LIVE不据此签收。
