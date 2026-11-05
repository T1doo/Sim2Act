# v7真实生成与应用保存

冻结Windows代码：942613ba02baa357e92ee6abb707f1b80f49845b。专用PostgreSQL、实际书生平台，无MockTransport或模型答案回填。项目“提交规则 · 复用工作台”，生成Run `run_0352109945a445788c7daa87eca4cbf7` 的实际标识以managed-natural-named-v7-942613ba-check.json为准。

实测阶段：真实read调用 → 真实check_candidate调用 → 原始最终候选完整校验通过，Run保留PARTIAL/语义NOT_RUN；随后按原指纹和版本确认，保存“提交规则审阅助手” `app_373d921dc36b87cc3c41ea9e16ba8309`，状态PREVIEW_ONLY。对应记录natural-v7-application-save.json。没有把候选生成的状态改成完整目标成功。

模型自行选择read_text/resource.read、spec_all/model.spec.all、verify_cites/spec.verify_citations、save_list/artifact.save_text四步图。端口和引用检查通过，尚未据此宣布完整语义正确。项目内产物目录deliverables/Sim2Act_规则审阅应用_20261106包含两份原材料、原候选、已保存应用及步骤图，未添加界面说明层。

后续执行尚未签通过。静态检查发现pa_trial_dispatch.journal_stage_accounted和_graph_stage_accounted把Source/Cold实际Attempt数量固定为2；本次合法图只有1个模型节点。需按冻结并已批准的真实图核对该资格，保留双节点漏调用拒绝，不能通过补发无意义调用凑数。此处是待验证的实现差异，不伪装为已执行Source失败。

原试验的stage_handoff_seconds=900，按前序Run创建时刻计。进入下一阶段前实时检查截止；过期后不改时间或复用旧批准。修正后应在新同版本范围内自动连续完成Generate→确认→Source→新材料Cold，减少调查间隔消耗阶段期限。调用/paid_cap/总预算和原记录保持。

v5结构失败与v6文字调用失败均保留。v7的25项调用/结构检查及54项精确软件资格检查PASS，但它们不替代Source/Cold和完整R0验收。所有本轮专用后台、Worker和PG已干净关闭。
