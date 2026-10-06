# AppManifest/AppRun 有界 agent 离线切片（实施前冻结，2026-10-06）

基线 6cbf47f56a8b75e3527aac3922441f26dd9344c3，dev/f1-foundation。只本地实现/验证/提交，父线程检查后另决定 push/CI。0 网络模型请求、不外发 V5、无新增 API/表/迁移/Grant/身份、无项目成果写入或正式发布。

## 与原 V5 对应和明确限制

原 V5 §4 P-B 要求目标、输入输出、实际工具和检查证据→可参数化应用→新资料新结果；§5/§6要求同一 ActionSpec/AppManifest 编译和运行器；§12 明确引用定位不证明语义推断。本轮实现这条主线的 read-only bounded_agent 分支，不叠加 spec-checklist 转换器。

最小验收目标是 **literal evidence retrieval**：给定明确字面检索词，在自由 TXT/MD 中返回全部命中行的精确引用、行号、来源 revision/hash。没有 MUST 标签/固定标题要求，无义务类别推断。可信检查器只证明字面检索任务/引用定位；任何语义规范提取请求拒绝 UNSUPPORTED_CAPABILITY，输出 semantic_status 恒为 UNKNOWN。该明确的非语义目标可成功；不得用它提升自由规范语义正确、真实自主生成或完整 P-B/AT10 状态。

## 接口（内部 Python 服务，现有持久对象，无新 HTTP 接口）

* `compile_preview` 支持单 bounded_agent `intern.agent@1`、唯一 `resource.read`、固定 `source.literal_evidence.v1` 检查器，闭合类型/接线/依赖/预算和 R0 effect=read/idempotency=read_only。候选必须声明限定目标，拒其他 executor/check/write 工具。不是把一次旧结果作为 manifest 输出。
* `persist_agent_candidate(store,user,pid,runtime_id,candidate,name)` 使用**已存在**且不同于 project runtime 的 app runtime；先核 caller/project/app 身份及现有 read Grant，插入 app_drafts。不创建/复制任何 Grant/Principal。resource version 初始为1（现有资源无修订列），hash 冻结；要换版本使用新逻辑 resource +新 manifest/revision，不能改同 id 内容冒充原版本。
* 离线 Replay 接收与现有 Model.request 一样的 `(messages,tools)`，提供 OpenAI assistant/tool-call response，经现有 `parse_response` 严格解析。request 槽、tool 槽、UTF8 envelope、输出 envelope、wall deadline、零 repair/retry；拒 live adapter。读工具实际走 `authorized_read`，真实回执送到下一轮；检查器验证 final JSON 对**当前实际原文**，不读测试 gold，不预填运行时答案。
* 现有内部 release/instance/AppRun/Worker 同一 prepare→compute→commit 和 lease/fence/Operation 保证保存 typed internal result。sample 和正常 worker 采用同 Replay protocol；生产 provider 调度仍禁止。所有冷读/重复请求重核当前来源、授权和 proof；无项目 artifact.save_text。
* `extract_agent_candidate` 只接受本服务已 SUCCEEDED 的 AppRun 及已 VERIFIED Operation/internal record/受限目标来源证明，重核真实源材料与 check；冻结来源 Run/输入输出/工具回执指纹、原候选版本和可参数化字段。重新绑定已授权新资源，沿用协议/检查器/输出类型，不复制旧答案；用现有 app_drafts 与 candidate provenance 保存，无新提取表。

## 验收标准

1. 两份自由合成 MD，独立手工 gold 先冻结，至少一个不同检索词/不同命中行；source app→可信已完成 AppRun→提取候选→新 resource/new input→冷 Store +现有 Worker→不同结果及可回读 lineage。gold 只在 tests，Replay 是离线模型输入，结果不作为运行时 gold。
2. 所有阶段 Principal/Grant 数量保持不变；project runtime 有权但 app runtime 无权、另一主体/另一项目、读 Grant 撤销/过期、retired source 拒绝。结果 ledger 为现有内部 AppRun effect，不开放 arbitrary writer。
3. source bytes/hash/revision、candidate/spec/proof/operation/record 篡改；FAILED/UNKNOWN/PARTIAL 源；旧版本/无回执/错误工具/任意代码/语义断言拒绝。不得把引用覆盖 PASS 当语义 PASS。
4. Replay 恶意 JSON、错引用、漏行/额外引用、超限/重复 call_id/多工具/工具未读即 final、额外 round、client gold、source 读后改写、commit 前撤权、同键异参/并发、cold read 均有负例。失败历史保存，失败不追加 typed data。
5. 现有 CSV/F1 回归、ruff/mypy；SQLite 全回归及可用本地 PG 最小 CRUD，无 API DDL。没有新增 UI 时明确此切片无新浏览器验收，不把旧 Edge 38 项算作新功能浏览器证据。

先独立审查上述权限和诚实性边界，再实施。独立审查发现与未测场景追加 Log，最终只本地 commit。自由语义提取/模型自主规划生成/LIVE/完整 P-B/Win11/F1签收/正式发布仍 NOT_RUN。
