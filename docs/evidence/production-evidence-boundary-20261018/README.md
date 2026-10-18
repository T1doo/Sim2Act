# 生产账户证据边界：原件索引

基线 `494cf2e1490967f8cf8621bb48b52fa00713436d`；实际源码/测试冻结 `8cd9d0040150dbd28a68bb622f5e6822577dad42`；普通分支 `dev/production-evidence-boundary-20261018`。仅root写仓库，独审只读。此切片交付strict证据要求、非权威候选诊断和原准入路由的缺来源拒绝接点，**不具备真实账户来源、免费权益权威、生产许可或发送能力**。

| 原件 | 用途与限制 |
| --- | --- |
| [执行记录](raw/execution.json)、[pytest stdout](raw/pytest.stdout)、[stderr](raw/pytest.stderr)、[JUnit](raw/junit.xml) | 同一冻结9个唯一定向节点、一次运行9P/0F，JUnit25.526s/outer28.619s；ASGI而非真实provider HTTP |
| [输入 before](raw/inputs-before.json)、[after](raw/inputs-after.json) | 699个repo输入/134个生产文件零漂移；不把外部runner/guard冒称纳入这699个输入 |
| [实际路由与表窗口证明](raw/actual-tmp/test_actual_production_routes_0/actual-production-boundary-proof.json) | 21份结构化ASGI request/response：4缺源400、14额外字段422、3权限403；4次resolver；两55表strict-equal已执行断言与每表行数/FP。没有完整行副本或独立DB重算 |
| [三版本投影](raw/actual-tmp/test_original_contract_project0/original-contract-projections.json)、[候选拒绝](raw/actual-tmp/test_candidate_binding_unknown0/candidate-refusals.json)、[非权威诊断](raw/actual-tmp/test_complete_candidate_is_onl0/diagnostic.json) | 明确合成数据结构资格；即使吻合仍SOURCE_UNVERIFIED/NOT_VERIFIED/livefalse/dispatchfalse，不提升真实来源或零费验收 |
| [运行级哨兵](raw/production_boundary_guard.py)、[哨兵结果](raw/offline-guard.json)、[runner](raw/runner.py) | 封存的外部运行helper；阻止HTTPTransport、凭据环境发现和InternModel请求，未触发。没有Worker.once或模型调用；fixture consent与SYNTHETIC_ONLY permit不是有效LIVE令牌 |
| [闭合结论](raw/closure.json)、[源码patch](raw/source.patch)、[source commit](raw/source-commit.txt)、[Ruff](raw/ruff-final.txt) | 11个保护文件与基线逐字节相同；仅新module及preflight四行接点；_qualified/admit保留且缺源时NOT_REACHED |
| [最终执行清单](raw/manifest-final.json) | SHA256 `69a5feae66810641bb31c38ce435b6b3163705471d065dc13e99e46291deb4df`；34个原件路径项+清单共35个copy路径/658328B；pytest `current`别名按原路径保留，不计额外用例、证据事实或fixture |
| [归档修正说明](raw/closure-correction.json)、[首次helper工具结果](raw/close-attempt-1-tool-result.json)、[首次helper](raw/close-evidence-attempt-1.py)、[旧清单](raw/manifest.json)、[完成stdout](raw/close-attempt-2.stdout) | 辅助器先用错已有文件名、后过早hash stdout。旧件完整保留，首次工具结果是metadata而非独立raw stderr；最终清单闭合实际完成字节。无产品/测试失败或重跑 |
| [独立终审](review/final-review.md)、[机器核验](review/verification.json)、[独审清单](review/sealed-manifest.json) | 有限通过，无剩余已知P1/P2；不另跑产品、DB/SQL或网络，不提前背书push。原serializer遮蔽P2已修；清单SHA256 `106e71ddcd65f993e3cf075eb24b73e4cae9e2c3fe6c68c55aab6a7d328107af`，含自身10普通文件40984B |

35个raw路径项全部直接复制封存执行件并核SHA，数据库/工作树/bundle未复制。最终manifest的数据库部分只记录本机保留的合成fixture路径与hash，包含pytest current别名；独审仅stat，不开DB/SQL或冒称重算行。完整运行日志的一条Starlette deprecation warning保留，不改变通过分母。

[选择清单](selection.json)将35个raw路径和10个独审文件与外部封存路径逐字节桥接，45个copy路径共699312B；README/选择清单自身及F2说明不计入该copy分母。独审目录已停止全部写入，旧sealed目录均未修改。

最终打包的全staged whitespace检查首先仅在`raw/source.patch:208`报告一条空格；它是原unified diff的空白context行，不是产品代码。保留该hash绑定原件，随后仅将此精确归档patch排除于staged whitespace检查；源码、测试及其它文档仍完整检查，`.gitattributes`不变，699个运行输入不因打包改变。首次检查exit2发生在commit前，交付核验metadata保留此事实。

9个节点范围：5个新增数据/回调/三版本投影/实际ASGI边界用例，既有P-A及P-B准入拒绝各一、仅合成permit拒LIVE一、旧offline callback与非test_only拒绝一。两个请求无写窗口之间的READ撤销是明确的合成fixture变更；不能写成fixture创建至撤销全程无写入。缺源阻止任何生产send/reserve；既有usage/unknown ledger不变，本轮未运行成功生产发送或恢复资格。

真实provider/账户权益/不可收费、真实语义、native Windows、PG、远端CI均未执行，不把本轮提升为R0/完整LIVE链/正式发布，不恢复已永久撤销的旧安装窗口。旧满盘未落盘独审仍为未补回缺口。
