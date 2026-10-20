# 双求和独立无内容逻辑：最终有限运行独审 ACK

结论：冻结字节的本地合成验收证据可以接受；无未闭合 P1/P2。承接本目录 CODE-ACK 的静态结论。根报告产品提交 e579c47e；本 ACK 以 source-freeze 的十份完整 SHA256 为准，不替代提交/远端核验。

本次仅读取源码、JSON/XML/gzip/日志并用标准库计算归档数据；未导入产品，测试、Worker、数据库打开、模型、PB/G0 执行均为零。报告脚本是归档文件校验程序，并非产品/测试运行。首次校验脚本将 recipe 节点键误写为 id，发生 KeyError 后已按实际 step_id 修正；不涉及产品执行或新增验收测试。

- 最终后端 JUnit：28P、0F/0E/0skip，56.053 秒；最终页面 JUnit：9P、0F/0E/0skip，91.639 秒。九份 results 与 driver.log 均 PASS，其中双求和六项、原标量三项。十份源码/测试的当前文件及 frozen-source 副本全部吻合 source-freeze；七个质量检查记录 exit0。
- 九例各两次页面加载、每次 26 个资产，共 468 个 loaded_source_sha256 全部等于当前对应 web 文件。dual 的 mint-post、post、identity-late、invalid-budget、invalid-node-budget、invalid-second-schema 及三个 scalar 场景均有实际原件。归档请求中的 material-plans POST 次数分别符合恢复方式；所有同 intent 重发 body/key 保持完全相同。页面检查还覆盖独立确认、第二列变更取消确认、身份 ABA 迟到守卫、GET-only 冷恢复、撤销后拒绝。
- 两个定向恶意回执在弱 seal 版本实际红测 2F/5.497 秒，失败为恢复行为断言；冻结最终对应两例均 PASS，各重发相同 POST 两次。没有将红测或初始 backend 26P/1F（夹具大写节点名）记为通过。
- 从实际 target resource.read 原件提取新 CSV，SHA256 为 87783f1c00940fe497f2895ee9623fecb69e9bf7408aaaf9cdc771f025a1330f。独立 csv/Fraction 求和得到 net=35/4=8.75、units=13，均 count=3。实际新 target 为 total_a=net、total_b=units；冷实例交换为 total_a=units、total_b=net。完整资源 ID、内容哈希、列、count 与有理数结果逐项核对；六个 dual 页面冷实例也核对同一新内容哈希与各自 plan 的新 target resource ID。公共 logic 未含旧 resource/release/amount/quantity/private_audit，dual recipe 固定 read/total_a/total_b。
- 正例 proof 保留 original_history_preserved=true、model_requests=0。35,766 条归档 SELECT 逐条复核：含 oldrid 参数且查询 resources 的记录为零；含 oldrun 参数且投影 runs.result/runs.context/operations 的记录为零。oldrun 参数实际 82 条，唯一 SQL 为 runs.id/principal_id/project_id/runtime_id/status/version/fence/fingerprint 标量查询。旧 Release/approval 参数查询 410 条，是允许的不可变审计例外。

SQL 边界必须保留：同一 JSONL 内存在测试 snapshot(env) 的无 WHERE 全表读取，包含 runs.result/context/operations；这是测试零写入和历史 oracle，原记录未标 oracle/product scope。因此不能把整个 JSONL 描述为“每条 SQL 均无旧正文”或“零旧 JSON 访问”。当前结论是实际 hook 的 exact-ID 参数谓词零命中，加上已静态审核的产品投影；未发现产品广泛读取旧正文。inspection/source-identities.json 是根在结束后对已闭 SQLite 的标识投影，报告 mode=ro immutable、total_changes0、前后 DB 哈希一致；这里只将它用于识别原 SQL 参数，不冒充运行时记录，也未重新打开数据库。

旧批次 backend67P/2skip（155.590 秒）和 UI14P（166.315 秒）发生于 P2 修复前，不能说它们全部验证最终冻结代码。原标量三项已在最终 UI9 中重跑；两个 skip 仍为显式旧 archive 缺失。各批次存在重叠，未相加冒充独立用例数。

本 ACK 仅覆盖本地合成 SQLite/ASGI/JSDOM 和固定有限 canonical compiler；不宣称 PG、原生 Windows、CI、完整 PB/G0、真实模型、正式发布或旧软件 authority 迁移通过。此前完整 PB 和最新期限未知边界不改变。无需为本报告增跑测试。

逐文件 SHA256、JUnit 失败/skip 名称、九场景摘要及 SQL/算术计数见 RUNTIME-ACK.json；校验脚本和 stdout 同目录保存。
