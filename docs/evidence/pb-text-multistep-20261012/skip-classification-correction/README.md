# r10 SKIP 分类纠正（仅文档）

总数535=523PASS/12SKIP真实；分类应为 **10 PG前提缺失 + 2旧源码archive缺失**。旧文本291=285PASS/6PG_SKIP；CSV199=193PASS/4PG_SKIP/2archive_SKIP。两项是 `test_actual_previous_dev_source_upgrade_preserves_old_proofs_and_requires_fresh_source`（67c6ccc8）及 `test_actual_f13_upgrade_preserves_old_rows_and_requires_fresh_source`（f13），实际升级仍 NOT_RUN。

[逐项原XML原因与SHA](summary.json)记录完整12项。原XML、日志、作者/独审测试汇总均未改动；[原README](original/README.md)、[原清单](original/DeliveryRemainingChecklist.md)、[原manifest](original/artifact-manifest.json)保留纠正前原字节，原错误表述不擦除。当前README与清单更正分类，artifact manifest更新当前文档路径的hash并纳入保留历史。

本目录记录UI P2修改前的文档纠正阶段：当时只改文档及分类汇总，源码/tests不变、新测试0；未开启新功能、CI或取消测试，未把r10回归升格为最终r11全仓签收。源码不变精确证明见source-unchanged.json。

随后同轮按父复审明确要求修改两处页面P2并做定向验证；见 [页面纠正](../parent-review-corrections/README.md)。上述414文件不变证明属于此前文档阶段，不能据此声称后续页面源码不变。
