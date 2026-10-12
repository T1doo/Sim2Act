# P-A 技术规范引用清单有限闭环（2026-10-12）

接续已验 `4b227895d9df7347cd11f2b8e4be725bcbe930dd`，依据
[NonCSVTaskProposal](NonCSVTaskProposal.md) 与 [NonCSVExecutionPlan](NonCSVExecutionPlan.md)。
本次在独立开发分支 `dev/pa-spec-checklist-20261012` 实作模型步骤图生成、真实检查反馈、精确确认、应用保存和冷新材料运行。原 owner 工作树不纳入，main/coredev 不改。

## 有限合同与实际链路

仅既有 `spec.labeled_citations.v1` 支持的合成 MD：`# Spec synthetic_<id> v<version>`；显式 `- [rule_id] MUST|MUST_NOT <statement>`；≤4096 UTF-8 字节、≤40 行、≤16 唯一规则。拒绝未标记段落、重复标签、不安全文字、其他格式。不是一般技术规范理解，也没有真实 V5 材料验收。

生成 policy 为 `goal-spec-checklist-application.v1`，与旧单节点 literal 和其 LIVE scopes 分开。使用已有实际 Intern sender 的 `httpx.MockTransport`、真实文件资源/HTTP/SQLite/Worker；默认关闭、真实请求/费用预算均 0，未配置凭据。

模型响应选择完整 compact recipe 的节点 ID、operator、依赖和输入边，允许两条有限图：

- `resource.read → text.spec_checklist → artifact.save_text`。
- `resource.read → text.spec_rules → text.spec_json → artifact.save_text`。

服务端展开注册工具合同、ActionSpec/AppManifest schema、确定性 action ID 和冻结预算；不为模型选择步骤图。拒绝常量答案、改边、额外节点/工具/来源。三次合成响应依次请求实际 `resource.read`、提交完整候选给实际 `spec.check_candidate`、消费 PASS/FAIL 后最终返回；FAIL 仅一次修订，PASS 不可静默换图。完整原始响应、实际 wire、usage、模型身份、读取和检查回执进入已有受保护 Attempt/Operation/Event 历史；未解析或未知结果不再发送。

用户不填写候选 JSON。页面从已保存 GoalCard 选择规范家族，展示完整候选与精确指纹；普通候选同意之外，另需明确仅此应用在本项目保存核验 JSON 的同意。新应用身份只取得绑定源 read 和该项目 save，派生制品只对用户与此 app runtime 取得 read；不扩大项目 reader 的权限。制品从验证过的 `/api/internal/app-run-jobs/{id}/spec-artifact` 读取。

预览重新读取实际来源、执行纯步骤，显示 `UNSAVED_PREVIEW`，业务制品写入 0。实际内部实例 Worker 每步留独立 intent、完整 VERIFIED receipt 和 fence event；最后一个事务包括 JSON 资源与局部 read grants、local_effects、保存回读、typed record、instance data_version CAS、Run/AppRun 终态与完整事件。取消、撤权、Goal/对象版本、预算/lease/fence、迟到结果或末写失败全部不能提交部分制品。未知 operation 仅读取恢复。

冷绑定只替换明确的 app/card/resource/hash/完整人工 Goal 和身份 slots，保留实际收到的 recipe/节点/边及工具合同。原模型源保持当前授权审计依赖，旧样例答案不进入冷应用定义；冷运行 Attempt ledger 为空、0 模型请求，重新计算新材料。绑定 POST 结果未知时页面仅以原 key GET 恢复，编辑 ABA/身份/项目/选择变化不安装迟到结果。

## 验收界限

citation correctness、显式标签覆盖与结构检查可 PASS；自然语言语义完整性、人工 business gold、真实模型自主完成、完整 P-A/P-B 均 **NOT_RUN**。合成 adapter 从实际 read 反馈按公开 grammar 构造样例；私有手工 gold 仅用于外部断言，不进入 prompt。合成 wire usage 只能证明本次合成协议/预算门，不能证明真实模型质量或计费。

PG、Windows、native browser、真实模型/付费 API、真实 V5 材料、旧源码冷升级、wheel 安装与精确 SHA 远端 CI 均未跑。先前 wheel 缺 setuptools 的实际失败保持；本次不安装/重试工具链、不部署、不走已拒浏览器路径。

验证记录和完整 SHA 在实现/独审完成后补入本页；未将中间通过或中断结果称为最终验收。
