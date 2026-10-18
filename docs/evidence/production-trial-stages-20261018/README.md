# NOT_QUALIFIED：P-A 原控制器3+2+2的有界检查点

源码冻结 `cdcae63e6ca6294b98ee6764b832d2d001e4de05`；普通分支 `dev/production-trial-stages-20261018`。最终负向2 PASS、正向fixture 1 ERROR，B全部9窗口及最终结果/owner回读NOTRUN。Cold final SAVE/current admission超原lease后VERSION_CONFLICT，未提交结果；不能称完整3+2+2/F2/LIVE通过。

[交付说明](../../F2/ProductionTrialStages20261018.md) · [作者结论](author/checkpoint-conclusion.md) · [独审结论](review/final-independent-review.md) · [独审核验](review/final-verification.json)

## 原件和复制

作者目录 `/workspace/production-trial-stages-20261018` 在独审前封存，之后无写入；独审目录 `/workspace/production-trial-stages-review-20261018` 在最终报告后封存。下列SHA仅指各自封存清单。两目录按清单逐文件SHA/长度校验后，精确复制非DB原件及清单到本目录。

| 来源 | 清单内原件 | 原件bytes | 清单SHA256 | 含清单的实际复制 |
| --- | ---: | ---: | --- | --- |
| [author](author/sealed-manifest.json) | 359 | 8,310,355 | `f10694b1c2b5390d6fcf11130a160314177952cd74d51e0e1287657e07c33150` | 360文件 / 8,367,794bytes |
| [review](review/sealed-manifest.json) | 75 | 269,346 | `7c82aefd1d3d42dde6bb53b280e927666ea3c4d35e910345d8a557b77c5156ae` | 76文件 / 281,036bytes |

总计精确复制 **436文件 / 8,648,830bytes**，数据库复制 **0**。本README和三个selection文件为复制时新增索引，不属于两份封存清单。见 [selection](selection.json)、[作者复制索引](author-selection.json)、[独审复制索引](review-selection.json)。DB在外部保留，原始size/SHA见作者 [汇总](author/qualification-summary.json)；独审仅stat，不打开DB或重算其hash。

## 最终原始证据

- [chain精确命令/开始结束/exit1](author/run-8-chain/execution.json)、[JUnit ERROR](author/run-8-chain/junit.xml)、[stdout](author/run-8-chain/pytest.stdout)、[完整被动guard](author/run-8-chain/offline-guard.json)。原timeout900秒未触发；结束16:55:07.079374UTC；无活动测试。
- [negative精确命令/exit0](author/run-8-negatives/execution.json)、[JUnit 2PASS](author/run-8-negatives/junit.xml)、[guard](author/run-8-negatives/offline-guard.json)。
- [历史汇总](author/qualification-summary.json)：14次记录=5PASS/8ERROR/1fixture FAIL，实际3个唯一节点/计划4个，33次mock adapter/真实模型0；旧19/12/8/9重跑0。每轮失败、输入清单、当轮runner/guard和冻结源码均保留。
- [作者关闭后只读导出](author/closed-checkpoint-facts.json)：60 archives/7 Attempts/3 Runs，fixture DB SHA前后相同。它是作者导出，不是独立DB重建或资格通过；[七body纯文件核验](author/closed-checkpoint-body-audit.json)。
- [完整源冻结范围](author/final-freeze-scope.json)、[最后Ruff](author/static-freeze8-committed.stdout)、[作者关闭信息](author/final-author-closure.json)。源8改/130生产blob未变，最终652输入/138生产前后无漂移。
- [独立纯文件audit](review/closed-file-audit.json)：核全部359非DB原件；当前NOT_QUALIFIED。独审没有跑产品、打开DB、联网或读取私有holdout。

独审文件观察器曾把含局部预算的最小heartbeat deadline误作总Run deadline，触发一次AssertionError。其.first原脚本/stdout/stderr与 [修正说明](review/final-file-observer-correction.json)全部保留；按created_at+原300秒及heartbeat复核后纯文件audit通过。这是观察器解释修正，没有产品重跑。

顶层早期draft/设计和诊断记录保留其时间语境；最终以NOT_QUALIFIED的作者结论和独审结论为准。`author/check_closed_outputs.py` 和 `author/write_final_docs.py` 为未执行PASS-only准备，不可当作通过；只读profile不是性能/权限资格；双reauth WIP文件为显式hash匹配重建。旧满盘独审报告NOT_RECOVERED。

真实模型POST0。真实API已有用户授权及配置token存在/非空布尔证明，未知的是当前余额/强制无新增费用事实/真实source-controller受审安装；两次无凭据公开根GET因DNS及proxy403失败后停止。Windows、PG、远端CI、真实语义/人工评分、新PB/AT10与本片浏览器重验NOTRUN。后续Git普通推送以独立delivery记录核验，不属于封存独审对未来动作的背书。

原始pytest/XML/远端Git输出保留其尾空白和结尾空行，通用 staged diffcheck 因这些封存原件返回2；原件未清洗以保持封存SHA。新写说明、索引及源码冻结范围单独diffcheck，无空白错误。完整原始诊断另存最终delivery记录。
