# 完整复验交付证据（2026-10-15）

冻结源码/测试 `0b6a780c952fb6eeed5e545f0f6db5f8e64360e6`，基线 `52654f7610602b7afc8a2c44eee7abc23e5c2d5d`；[完整说明](../../F2/ProjectCompleteChecks20261015.md)。最终提交只追加文档/证据，src/tests/pyproject与冻结源码相同。

## 最终单次完整运行

[RESULT](final-RESULT.json)：199 PASS / 0 FAIL / 0 ERROR / 0 SKIP / 0 deselected，RC0，199 unique/0 duplicate。
[原命令](final-COMMAND.json)、[collection](final-COLLECTION.json)、[XML](final-results.xml)、[独立根核验](TERMINAL_AUDIT.json)；488 before/after/executed/root/Git哈希闭合。pytest4588.65秒；runner4591.070秒；两个原Pydantic warning保留。

[公开回执汇总](final-SUPPORTING_CHECKS.json)：原双CHECK各首次领取成功，原300/30/3不变；实际合成P-A/P-B Worker各3/2/2七槽、全accepted/KNOWN7000/envelope48354、不允许LIVE；另一个Store七槽原断言14/7868通过，不能叫模型Worker链。UI8实际119检查/143actions/888requests/189assets/9boots，进程内HTTP/JSDOM。
[P-B公开事件](final-PB_PUBLIC_EVENTS_SUMMARY.json)：35条=7dispatch+21permit+7accepted结算，0拒绝/错误。
[质量](quality-RESULT.json)：fullsrc Ruff、12changed Python Ruff、两个Node syntax PASS；fullmypy FAIL5条原有/0新增。
[82模块精确资格](QUALIFICATION.json)：pin bcf48da5c3141eeaa35ad32543d34a48b14519b7e4f5f0e1772c701b61f41041，候选cadd1864e9f4da8209936edcf8b8e299a537a2e4。
[最终独审](FINAL_REVIEW.md)及STATIC_CHECKS/TERMINAL_CHECKS/DOCUMENT_CHECKS随本目录提供。

## 完整归档

每组tar.gz与同名前缀MANIFEST.json逐普通成员精确闭合；[ARCHIVES.json](ARCHIVES.json)记录压缩包大小、SHA256、成员数和完整回读。保留原失败，不把跨SHA或probe结果合计到199。不包含symlink、pytest缓存或mypy缓存。

| 归档 | 内容与路径 |
| --- | --- |
| rootcause-evidence.tar.gz | 原双应用before/profile源码、日志、claims、故障phase原失败/修复；profile.jsonl包含35.468639秒写锁观察，原ce6确切三次失败原因UNKNOWN。 |
| heartbeat-evidence.tar.gz | 识别SQLite BUSY/LOCKED修复前7FAIL、修复源码/实际结果。 |
| admission-evidence.tar.gz | HTTP作者3P2F/修正、P-B来源guard初失败、scope损坏独审反例、修复与完整源码。 |
| regression-evidence.tar.gz | final2dda原198P1F、pbprobe9b1a原1P、finalbb287原198P1F、recoveryprobe0b6a原4P、final0b6a原199P；各原XML/stream/source/fixture/manifest；quality0b6a为当前质量。其他旧质量结果仅对应其原SHA。 |
| review-evidence.tar.gz | recovered目录历史独审；final_recovered最终源码/pin/质量/终态/文档只读独审。 |
| integration-evidence.tar.gz | 原集成草稿历史、旧/当前TERMINAL_AUDIT、资格、断连恢复/进程健康/连续性、归档和推送核验脚本；DELIVERY_FINAL.md为本轮最终说明，旧DRAFT不是当前状态。 |

原2ddaP-B accepted=false确切拒因UNKNOWN；9b未重现；bb恢复准备取消前租约读取有窗口，但历史实际续租NOT_RECORDED。最终PASS不回写这些历史未知。

PG、干净Win11、原生浏览器、真实模型/费用、人工语义、完整真实P-A/P-B、旧源码升级、远端CI和部署均NOT RUN。私有SQL/UDF barrier与已知浏览器拒绝路径未调用。LIVE保持阻断；整体owner/semantic/dependency/真实收费权威等验收未关闭。

普通push后的完整最终SHA、精确远端、保护9分支、源字节无差异、其他WIP不变与clean/ahead-behind0/0回执位于交付消息所链接的独立Git JSON（生成于最后提交之后）。
