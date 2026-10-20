# 双求和新材料：冻结产品静态独审

**ACK 当前冻结产品代码。无未解决 P1/P2。** source-freeze.json 的 10 个产品/测试文件逐一 SHA256 与当前字节一致；精确清单见 CODE-REVIEW.json。此为源码审查 ACK，最终冻结 20 后端与 15 页面批次仍待父侧完成/归档后另核。没有重跑任何测试、Worker、DB、产品、PB、G0 或模型。

原两 P2 已闭合：材料回执不再用旧 CSV 列白名单约束新 CSV，只复核旧结构/节点/预算，再逐 sid 核目标列白名单与 plan.input；通用实例 helper 仍保留 frozen columns 约束。新冷 Store 测试也继承原 PG schema_translate_map，未运行 PG。

后端完整来源链仍在：recipe 读取 owned Release 并真实 read_release/closed；只允许原 completed 同读两 sum，不允许 material/logic 来源继续串联；目标 dual schema 精确重建两个完整 aggregate tuple，再走原严格普通注册 CSV schema 门，不放宽共享 target_for_schema。双列新模型与旧 scalar 模型严格互斥、只有恰两稳定 key、列值必须是目标当前数值列；完整 fp/graph/resource/source hash、当前权限和冻结预算重验。同键不同映射冲突，成对请求/响应从原 input 重建，不能靠重签 response 单独改第二列。

新来源 Release 从实际 SUCCEEDED 原 DAG/每步 VERIFIED 回执与两终端结果重建，按原 sid 保存实际 default_columns 和嵌套结果 schema；实例 enqueue/read_release/validate_snapshot/validate_binding 继续核完整 material 来源与新目标当前授权，derived instance-plan 不能取代来源证明。原 Worker 执行器、三操作与 typed ledger 未新建旁路。默认列只作已绑定意图恢复，后续另行确认的实例新列仍受目标冻结列范围控制。

页面分开确认材料计划、实际运行、Release 与实例；两选择器标稳定节点，变列清确认，回执核新 namespace/精确 source Release/目标/原 key/双列 mapping/完整 plan。冷页从已验证 default_columns 恢复，晚回执/原 key 恢复复用原页面世代和完整 intent 守卫。旧 Release/实例/历史不修改或静默迁移。

旧单列字段与 canonical fingerprint 值保留；共享基类使 Pydantic 字段声明顺序变化，所以不承诺 raw JSON 字段顺序逐字节相等。db.fingerprint 使用 sorted JSON，原同键旧契约仍完整重建。新 dual namespace 单独表达扩展；csv_logic 的 target_for_schema 及其 dual 禁止仍保持。

已只读核早先作者原件：20P/56.361s 后端、1P/10.790s 冷链补验、旧相关 73P/2SKIP/147.702s；两个 skip 明确为未准备 actual 50b/fab source archive，不能认作旧软件真实迁移通过。这些并非最终新冻结批次结果。早先保存的 dual-new-material-proof 显示 price/units 新结果，冷实例换列后分别为 17 与 40.000、模型0、旧历史保留；Fraction oracle 检查每个完整 result 的 resource/hash/column/count/sum。最终运行附录待新原件完成，不把作者运行算为审者执行。

范围仅既有授权单 CSV 上原两 sum 流程的有限新材料复用；没有独立 data-free 逻辑、两 CSV 比较、新权限/工具/模型或正式发布。未关闭 PG、Windows/native、CI、真实语义或完整 P-A/P-B。
