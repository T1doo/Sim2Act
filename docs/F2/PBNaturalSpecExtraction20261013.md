# F2-T03 / AT-10：自然规范成功运行到可复用应用

依据封存 V5《平台产品设计》§4 P-B 与《分阶段开发计划》F2-T03、AT-10：基于成功任务的目标、输入输出、工具调用及验证记录识别变量、稳定逻辑和必要模型节点；独立来源入口，新资料、错误输入和冷会话分别验证。P-A 新材料 binding 不能代替 P-B。本轮基线 `68812ce9603cab94922b98c57ff1175b0a8f9207`，分支 `dev/pb-natural-spec-extraction-20261013`；root 为唯一产品写入者。

现有自然规范运行器已支持实际 4/6 步模型图、完整来源/账本与最终事务保存。缺口是成功 Run 没有独立提取入口，不能审阅、编辑稳定逻辑并保存 task_run 来源的新应用。本轮复用原 codec、ActionSpec/AppManifest、内部 Release、Worker 和成果读取，不加入固定答案、语义解析器、模型批准或发布框架。

## 有限合同

- 来源限同主体同项目的自然规范 SUCCEEDED 内部 Run；P-A 生成应用或其明确新材料 binding 的运行均可作为来源。原键/accepted/binding/Release/Goal、真实模型 Attempt、Operation/Intent/Receipt、本地 effect、typed JSON 与原 P-A 审计必须完整通过。独立 P-B 来源禁止再提取，避免隐藏提取链和无界审计。来源不是生成时 PARTIAL 候选，不能仅以成功字符串或缓存输出冒充。
- 默认 recipe 来自实际已验证成功 definition。原图与编辑图各有指纹；编辑只使用现有有限算子、端口与无环结构，一 READ、一 VERIFY、一 SAVE、1/2 模型及必要合并，完整关注范围。不能添加代码、任意提示词、工具、常量答案或删除关键检查。预算同时受来源 runtime_limits 与平台上限约束，来源单模型不能因平台额度更大而增加模型节点。
- 独立 P-B 可见入口在成功规范结果版本。用户可编辑稳定节点 ID、模型关注范围、第二节点是否读取前一节点实际 items/feedback，再选择自己已保存的不同 Goal 与 TXT/MD。完整新 Goal、全部人工未决项、原/编辑图、实际端口、目标材料、最小权限与预算在精确审阅中展示。编辑或选择变化立即失效旧审阅与确认，含 A→B→A。
- review 为仅读，无新应用/Grant/资源/模型请求。精确 fingerprint 冻结整个审阅和原请求；提交在项目事务中重新鉴权、复验完整成功来源及新目标材料、重新编译编辑图并核对指纹，原子创建独立 app/runtime、仅新材料 READ + 本项目 JSON SAVE 两项最小 Grant、task_extractions 独立 marker、metadata 双 seal 与完整回执。创建后再次核完整来源、目标、预算与保存物，失败全部回滚。
- candidate 的 manifest 为 task_run/source_run_ref，独立 spec_task + task_extractions KIND + metadata/完整原请求必须吻合；不能混入 goal_application/spec_binding、移除 marker 或降级为其他执行家族。P-B 专用读前 gate 和审计分支接入现有 app/Release/instance/Run 读取和最终 Worker guard。
- 提取发送后通过原 key GET 独立核对回执、精确审阅和新草案后才打开；未知结果只 GET 恢复，本页 pending 保留，禁止重发。关闭审阅不会取消已发送事务；重新打开同来源仍只能恢复未知原意图。页面/身份/项目/实例/工作区/编辑代际变化后，迟到响应不能绘制、交接或清除另一 pending。内部 Worker 的原暂停/取消/撤权/期限/lease/fence 与事务检查保持。

## 语义和复用边界

原结果、引用、完整原文、模型响应和凭据不进入新 candidate 或新模型输入；sample_fingerprint 仅指向已成功来源的实际输出证明，`sample_scope=SUCCESSFUL_SOURCE_ONLY`。编辑图和新材料预览均 `NOT_RUN / MODEL_EXECUTION_REQUIRED`，不得声称编辑图已执行或语义验证通过。冷 Worker 必须读取新绑定并产生新 AppRun/typed 成果；引用/结构 PASS、semantic UNKNOWN、owner PENDING、formal publication false 分开。

来源仍是当前授权的显式审计依赖；本切片不发放删除/撤权旧源后的独立无内容逻辑许可，不声称 source 退休或完整通用 P-B 完成。数据绑定为注册资源 ID/hash 与明确 Goal，无原聊天或一次性本机文件路径。默认真实模型关闭，请求/费用 0；实际工程测试只注入合成 transport，不能据此接受真实模型或业务语义。用户手动模型设置不修改。

原失败及最终实际测试另存本轮证据：首两项夹具误读 Goal API 快照，下一两项 Release 快照无 name 的真实集成拒绝均保留，修复后实际重跑。最终分母和源码资格以完整冻结终态及独审为准，不把运行中、历史或中断轮次合并计 PASS。PG、Windows、原生浏览器、真实模型/资料/人工语义、完整旧库升级、完整 P-A/P-B、正式发布、CI/部署未跑即 NOT_RUN；旧取消窗口永久 NOT_VERIFIED、不重做。
