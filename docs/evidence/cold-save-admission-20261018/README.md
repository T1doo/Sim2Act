# Cold SAVE最小修复：FRESH_MOCK_QUALIFIED

源码 `fd96df814e8c0fb6db6651ce77eb484951240ecc`，分支 `dev/production-trial-stages-20261018`。一次fresh串行B→A→C→D **4 PASS**，B原9窗口全部执行，实际gen3/Source2/Cold2成果及同Run PENDING owner入口通过。真实模型0；不签整体F2、LIVE、真实语义或性能保证。

[交付说明](../../F2/ColdSaveAdmission20261018.md) · [作者结论](author/conclusion.md) · [最终独审](review/final-independent-review.md) · [独审核验](review/final-verification.json)

## 精确封存及复制

| 来源 | 清单内原件 | 原件bytes | 清单SHA256 | 含清单的实际复制 |
| --- | ---: | ---: | --- | --- |
| [author](author/sealed-manifest.json) | 68 | 2,394,591 | `c6aa7ede21e01a16de2b9852cbc71a23542fba322fa5f9c7fab54916fc4e614e` | 69文件/2,405,655bytes |
| [review](review/sealed-manifest.json) | 10 | 56,995 | `fb8cfd178168bd118a5d6033516a0f3edb7086e040eaa717bb08814b2db855cf` | 11文件/58,749bytes |

总计复制 **80文件/2,464,404bytes**，逐文件SHA及长度精确匹配，DB复制 **0**。本README与三个selection文件为复制索引，不在两份封存清单内。见 [合计索引](selection.json)、[作者索引](author-selection.json)、[独审索引](review-selection.json)。5个合成DB仅外部保留，其作者size/SHA见 [闭合汇总](author/closed-summary.json)；独审仅stat，未打开DB或重算其hash。两份原封存目录在seal后均停止写入。

## 原始证据入口

- [唯一fresh命令/时间/exit0](author/fresh-once/execution.json)、[JUnit四PASS](author/fresh-once/junit.xml)、[pytest stdout](author/fresh-once/pytest.stdout)、[被动IO/guard/事务原件](author/fresh-once/offline-guard.json)。pytest540.32秒，outer542.936816秒，900秒timeout未触发，闭合于17:39:53.983473UTC。
- [本轮实际前缀B九窗](author/fresh-once/actual-tmp/actual-prefix0/fresh-proof-rejections.json)、[实际七调用及成果/owner](author/fresh-once/actual-tmp/actual-prefix0/actual-pa-stages.json)。实际9次合成adapter=完整链7+两负向2，真实模型0。
- [闭合汇总](author/closed-summary.json)重算七份raw/canonical响应SHA与两组SAVE guard，Cold epoch195→201，写后guard2.779830秒/3713SQL/余23.162011秒lease。事务11.315883秒是driver前commit事件，不能当作driver完整提交耗时；实际成果/owner断言另证业务完成。
- [源码及静态闭合](author/final-source-and-closure.json)、[最小patch](author/minimal-fix.patch)、[设计和限制](author/minimal-design.md)、[Ruff原stdout](author/ruff.stdout)、[源码diffcheck](author/source-diffcheck.stdout)。652输入/138生产与helper无漂移；1生产改变/137blob未变。
- [只读准入组件诊断](author/expired-admission-diagnosis.json)、[scope/audit/current组合诊断](author/proof-prefix/expired-admission-diagnosis.json)。未复现历史完整31.750秒，不把组件成本当完整SAVE或普遍性能保证；原lease仍拒绝，原DB字节SHA未变。
- [旧失败合成副本九窗](author/targeted-regression/fresh-proof-rejections.json)明示clones=true、不是fresh资格。其后旧Journal Worker因软件改变正确拒绝：[首命令exit1](author/targeted-execution.json)、[原stderr](author/targeted.stderr)；没有改旧合同。补充 [旧lease回归](author/expired-lease-regression/expired-lease-regression.json)用合法generic Worker/无旧pa_trial安装，两个窗口Stale worker lease、55表不变，未重跑九窗或旧请求。
- [断连恢复核验](author/reconnection-checkpoint.json)：先核原命令exit0及无在途进程才继续，未重复启动fresh、未删未知锁/进程。最终Git普通推送另以delivery记录核验，独审不预先背书未来操作。

f89原未合格检查点及旧封存原件保持历史：14=5PASS/8ERROR/1fixtureFAIL，33mock；本次新增4PASS/9mock后累计18=9PASS/8ERROR/1FAIL、42mock。组件脚本不算额外pytest PASS。旧19/12/8/9矩阵未重跑，旧满盘独审报告NOT_RECOVERED。

原始pytest/XML/profile输出按封存字节保留空白，完整性以SHA核验；新写说明、索引和源码分别检查空白，不清洗原件。

真实API已有用户授权/key存在事实，剩余条件是当前余额、强制无新增费用事实及真实source/controller受审安装；本修复未触发真实请求或新网络探测。Windows/native、PG、远端CI、真实语义/人工验收、新PB/AT10及本片浏览器重验NOTRUN。没有放宽lease、版本、权限或新增executor/Grant。
