# 固定 CSV DAG 的受限接线草案

这是原有三节点 DAG 页面/接口的工程扩展，候选未验收。保持 LIVE=0、MOCK、semantic UNKNOWN、owner PENDING、publishable=false；不覆盖旧版本，不开放正式发布、任意节点/代码/工具、动态依赖或业务写权限。合同仍沿用原 V5、局部修改、人工锁和影响分析约束，接线方案在提交/接受/执行/读回时继续重验来源和授权。

## 页面复现

1. 在本独立接线候选分支，沿用 [原 DAG 指南](FixedCsvDagQuickstart.md) 准备自有合成 CSV 的 amount 求和应用和当前交付图锚。安装和启动用原配置，不配置新凭据。
2. 在原应用的 DAG 区域点击“读取允许接线”。服务端只提供以下三个端口，各两种来源；界面不能添加节点、循环或执行器。

| 端口 | 默认来源 | 另一允许来源 | 语义类型 |
| --- | --- | --- | --- |
| aggregate.resource_id | preview.resource_id | source.resource_id | resource_id |
| report.resource_id | aggregate.resource_id | preview.resource_id | resource_id |
| report.source_hash | aggregate.source_hash | preview.hash | source_hash |

3. 选择 quantity，并将三个端口改为另一允许来源，提交新草案。读取精确 plan_fingerprint、新输入来源和依赖。aggregate 始终等待 preview 验证；report 如果使用 preview 的任何输出，自动等待 preview 和 aggregate 两个前驱。其余列/count/sum、schema、资源与授权绑定、节点、执行器和布局保持。
4. 明确确认该新计划的精确指纹，再接受离线运行。原 worker 执行 preview → aggregate → report，报告为运行结果，不保存业务 artifact。独立读取原 CSV 可复核 amount=30、quantity=15。
5. 查看实际回执：`input_sources` 指明每个输入来源，`predecessor_receipts` 封存实际前驱回执指纹；最终文本为“列 quantity；行数 2；合计 15”。来源值相同但来源字段不同也会改变方案指纹，不能用旧确认运行新接线。
6. 响应丢失显示 UNKNOWN，原 request_key、选择和指纹保持并锁定，点击原恢复按钮读回；不可重新选接线代替原接受结果。冷页面通过原历史入口重验计划和回执，不执行重复操作。撤权或来源变化后证明失效、仅保留停止状态。

## 接口与兼容

`GET /api/projects/{pid}/apps/{aid}/csv-dag/options/wiring` 读取服务端允许列表、图与候选指纹、options_fingerprint，无写入。原计划 POST 可选 `wiring_patch`，每项仅 `{step_id, port, source:{source, ref, field}}`，最多三个，不许重复。未传该字段保持旧请求/计划/回执字节结构；空列表明确建立默认接线的新草案，不覆盖旧方案。

严格 JSON schema 和服务端语义允许列表同时验证。hash与resource_id即使都是string也不能互换；未知端口/来源、额外schema/executor/dependency/nodes、循环、非法Unicode在写入前拒绝。新定义、计划指纹、精确确认、实际intent/receipt、来源hash、恢复均绑定接线。

本分支显式依赖两项 DAG P2 修复：原候选源码 `4c7d81b80d2d81ce9471b185b09ac34fd7c74740`，在接线分支取入提交 `bd4c549`（保留wire_proof冲突解法）与 `e8c3678`。该依赖的原独立审查状态另由审查者判定；作者测试不能作为独立验收。最终提交重新核lease/deadline/有效预算；持久化输出严格类型与整份证明校验在新接线上同样生效。

运行 `tests/test_csv_wiring.py` 可复核所有八种合法组合、旧默认兼容、真实独立求和、拒绝项、精确确认、前驱来源、冷恢复、撤权和P2防护。双数据库/实际HTTP+jsdom证据另存 `docs/evidence/csv-wiring-final-20261008/`。原断言与 Windows900 / Edge240 / Node150 标准保留，原生Windows/Edge NOT_RUN，LIVE=0，无新CI、dev/main合并或部署。真实gold、通用P-B、人工签收未完成。
