# Fresh first-admission/G0：只读可达性设计独审

基线 `ada263ce4102a55c6ee9b54d3c85224561f6c51f`。结论：在“从新空上下文构建、整个建上下文过程零 sender、五真实函数及原完整证明不替换、不伪造批准/执行来源”的联合边界下，**当前没有可签 ACK 的原执行路径构造方案**。这是源码可达性/来源判定，不是声称数据库行在数学上不可手工合成。本审产品导入、测试、producer、Worker、模型与 DB 打开全部 0；只写本 `/tmp` 报告。

## 五函数确实依赖什么

`natural_spec_runtime.py:2617` `_ColdTrialGraph._prepare` 读取原主批准与 cold 阶段批准，重建 current first binding、source 真实结果/typed/完整 receipts、generation 原始 history、extraction、use、原不可变 Release 与当前实例；不是仅接受一个 RunCheck/StageAuthority DTO。`:2670-2717` 找到原 Generate Run、核三条 production markers，加载完整 journal，再对 Source 和 Generate 做完整 accounted 审核。

`pa_trial_dispatch.py:1706` `_pb_markers_from_facts` 强制三条 Generate production markers；`:1711` `_pb_prefix_source_from_facts` 强制非 halted、Generate+Source 恰五个 accepted 槽且 Source Run 唯一。`:1569` `_graph_stage_accounted` 要实际 Attempts 恰 3/2；`:1507` `_graph_journal_chain` 保留完整 owner/body/seal/Capture/raw/usage/identity；`:1415` `_stage_usage_from_facts` 要 Generate RECEIVED、Source VERIFIED。Source 另有 VERIFIED Operation 和原 NS/controller 两套正文的逐字节关联。

`natural_source_archives.py:435` `_graph_resolve_trial_source` 从完整 Source proof、原 ExtractInput 成对请求与重建的 StageAuthority 出发，独立重验批准/权限/原提取链；`pa_trial_dispatch.py:1664` `_graph_pb_archive_chain` 要 Source 两条 capture 和两套完整正文一致。不能用预制摘要或仅配对 P 替代。

原 sender 路径 `production_trial_sender.py:536-620` 为 reserve→record_attempt→provider.request_serialized_captured→receive。若从初始阶段就使 sender/provider 永远拒绝，正常路径不能生成上述五个完整 received/accepted 记录及 Source 成功证明。手写 attempted=true、accepted=true、SPEC_PRODUCTION_CONTROLLER capture 或原批准配对行，虽然可能构造可通过的纯数据夹具，却不再证明这些记录由原执行路径产生；本次不能把它冒充原真实 admission 上下文。

## Cold 第六响应：须避免过度断言

正常 `advance_model` 在 `natural_spec_runtime.py:3538-3572` 已持久检查 Cold RECEIVED、record_response 归档，然后 renew、lock_live 和原 meta 校验，才从实际 wire/raw/response/step/node 构造 graph_call 并进入 `_cold_model_before`。因此以**原正常运行位置**到达本次 G0，常规新建前置是 Generate3 + Source2 + Cold1，合计六次 Mock 请求；第七次 Cold 与 W5 不必执行，但不能把准备阶段六次请求藏到“零 sender 测量”之外不计账。

然而五个定时函数本身显式强制的是前五槽。`pa_spec_apps.py:2037-2065` 的内部 first prefix/commit 和 `_ColdTrialGraph.commit` first 路径，并不在每一步都要求当前 Cold Attempt RECEIVED；后续原 settling/receipts 路径才继续核当前响应。因此**不能仅从五函数推导任意私有入口都必须有 Cold1**。直接传人工 graph_call/raw/aid 调私有 first commit，可能是更窄的内部语义夹具，但必须标明脱离原接收位置，不得称同一真实 G0。它依然没有解决真实 Generate3/Source2 前缀来源。

可比较的候选入口是原 `_cold_model_before`：它拥有完整只读 scope，完成第二 original guard、scope 最后全图检查和原有限期限检查后才返回 W5。未来若另行获准准备新有效上下文，应在其原拒绝即停止；若原 G0 正常完成，则在 scope 真正关闭后、原 W5 组前截止，保留所有原校验。包装器不得 stand-in 五函数、跳过第二 guard 或用仅 first commit 的成功冒充 G0 已结束。

现有 `test_cold_admission_diagnostics.py` synthetic_commit 明确替换五函数和语义/SQL producers，仅是局部诊断等价测试；不符合本任务真实函数目标。复制旧闭库并改 created_at/lease/approval/expiry 也不符合新鲜来源合同；旧 Cold lease 在原失败时已经逾期。本报告未打开旧库、未恢复 Worker、未构造新批准或运行窗口。

最小缺失条件：先有**通过原路径生成且仍有效的前缀事实**，包括正确新合同/软件/账号绑定、原用户批准与 Source/Cold 阶段批准、真实三/二原始 Attempt/Capture/usage/body/seal、成功 Source 结果/提取、当前 Release/instance/原键及原完整 scope；原 G0 还需当前 Cold 正文。若准备也必须 sender0，则需另行承认这只是人工合成的内部数据夹具，不能代签原执行来源。此边界说明不是请求或授予新执行权限。

## 独立产品缺口：双求和换另一份既有授权 CSV

只列一个有源码证据的原复用闭环缺口。原计划 F2-T03（从成功任务提取变量/逻辑并冷复用）、T04/T07（有限 DAG 与局部变更）、AT-10/11（独立应用、新有效材料/参数产生新结果），及 V5 §4 P-B，支持这一已有能力的有限接续。它不是“两 CSV 比较”，也不表示当前冻结 Release 已经授权读取新材料。

现有双求和实例已经支持同一授权 CSV 上两个节点各自换列并保存完整两结果：`csv_dag_instances.py:91-99,189-211`。但 `csv_material_reuse.py:74-75` 明确拒绝 TWO_SUM_VERSION；MaterialInput 只接收单 column，definition 只改 nodes[1]。此外 dual data_schema 是按两个节点嵌套的结果（instances.py:133），当前 target_for_schema 比较普通目标草案 schema；source_snapshot 的 material_reuse 分支 `:159-162` 还显式 `not dual` 且只有标量 default_column。因此不能只删一条拒绝就认为完整支持。

最小范围应是：明确选源成功 dual Release、新的既有授权单 CSV 草案及两个固定 sum step 各自列；原结构/step ID/边/动作/预算保持；完整目标 resource/hash/graph/candidate/权限 CAS；只生成新 ordinary plan，原 no-model DAG 执行并核两个完整终端输出，成功后另行精确 Release/实例确认。旧请求/Release/数据/历史不重解释，不新增 Grant、工具、模型或双 CSV 读取能力。源内容仍按现有 material reuse 合同要求可核查，不顺便扩为 data-free logic 授权。

必要验证：用新 CSV 的独立数值 oracle 同时核两输出，选择与旧材料明显不同的数据；旧 typed/历史 bytes 保持；错误列映射/指纹/源目标身份/撤权拒绝；同键冲突与未知回执恢复；冷 Store/页面恢复和编辑 ABA；原取消/回滚路径及旧单求和/report 合同保持。当前仅确认缺口，不实施、不测试。
