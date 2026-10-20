# 双求和新材料：最终冻结运行原件复核

**最终有限 ACK。无未解决 P1/P2。** 产品提交 `a2b44ef1b4019dc4ff56a7431960bc002a48c23e` 的 10 个冻结文件与 source-freeze、frozen-source 副本和当前文件逐字节 SHA256 一致；产品静态 ACK 仍有效，两处独审 P2 已闭合。

本审只读原 XML/JSON/gzip、归档 CSV、Git blob 和文件哈希。产品导入、测试、Worker、DB 打开、模型、PB/G0 执行均 0，未修改仓库。独立算术只用标准库 csv/Fraction 处理已归档正文。

- 最终冻结后端：20 PASS / 0 failure / 0 error / 0 skipped，JUnit **55.827 秒**。
- 最终冻结页面：15 PASS / 0 failure / 0 error / 0 skipped，JUnit **269.370 秒**。此前消息 269.367 的不同口径不采用为 JUnit 值。
- 旧相关回归：73 PASS / 2 SKIP，147.702 秒。它发生在最终显式 dict 类型声明修正前；两 skip 是缺少实际 50b/fab 旧源码 archive，不能宣称旧软件真实迁移通过。
- 三批 testcase 精确 ID 无交集，合计 108 个不同 PASS、2 SKIP；最终冻结字节实际通过 35 个节点。早先失败、重复通过批次不加进这个分母。

15 个 results.json 均 PASS，各两次页面装载，driver.log 均记录 PASS；30 次加载的 **780 个资产 SHA256** 全部与当前实际 web 文件匹配，差异 0。3 个新 dual-material 病例分别覆盖 POST 丢回执、晚回执、篡改预算回执，均走真实 HTTP、实际新计划执行/Release/实例、第二冷页与新双结果。其余 8 个单材料页和 4 个原 dual-instance 页亦均通过。所有 material POST 的原完整 body（含 key）在重试间一致。

已从 frozen-backend 的实际 resource.read 回执取原 CSV 正文，核其完整 SHA256 `9fc1713f4979f2170a0bcceee7817e1c44863a80168d168a00fc17a364d89756`，并与目标 material binding 对应。独立 Fraction 核新计划 total_a/price=40、total_b/units=17；冷实例交换后 total_a/units=17、total_b/price=40（产品保持字符串 40.000）。逐项核 resource/hash/column/count=3，不用同一个 aggregate 实现作为 oracle。三个新材料页面的冷实例也均为上述交换结果、data_version=1、model_requests=0。新 Release default_columns 正确保留 price/units，未与旧来源 hash 混用。

最终20个后端原件还覆盖两节点同列而 sink 不合并、错误/混合列映射、同键异参、scope/hash/撤权拒绝、源/目标当前权限重验、origin成对重签拒绝，以及第一 sum 后撤权时 WAITING_RESOURCE/tools2/无 typed append。旧历史保持依据作者测试中的实际逐行断言与归档标记；本审没有再次打开 DB 或伪称独立重拍全部历史表。

quality/checks.json 六个命令 exit 均0：Ruff、三个产品 Python 文件 mypy、三个 JS 语法及 diff whitespace。46 个最终 UI/backend 原件的压缩/解压 bytes/SHA256 与详细 testcase/算术核验结果列于 RUNTIME-ACK.json。README 已修正 JUnit 毫秒值，并区分最近完整 PB（G0 32.041、first-binding4.368、复合拒绝实际期限/stop未知）与更早37.279/paired历史，不补造旧失败有限期限。

有限范围仅既有授权单 CSV 的原两求和闭环，源授权/一跳材料来源保持；不证明独立 data-free 逻辑、双 CSV 比较、真实模型、PG、Windows/native、CI、完整 P-A/P-B 或生产发布通过，不产生重跑授权。JSDOM native structuredClone 由驱动注入，不扩大为原生浏览器资格。
