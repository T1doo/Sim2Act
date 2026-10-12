# F2-T02 / P-A：书生受控适配与模型图新材料复用

2026-10-12；基线 `a4fd476127a477006dbdb29a9a1f6c2f09e6a001`，独立分支 `dev/pa-intern-provider-20261012`。唯一产品写入者为根代理。原 owner 草案留在原工作树，未纳入本片、未延展。V5 原方案保持原字节。

本片落实书生发送适配所需合同，沿用现有 `InternModel` 的固定 HTTPS sender、实际 Worker、字面引用检查与内部实例；默认不发送。真实模型、付费 API、账号凭据配置、部署均不执行。合成 LIVE 形状测试仅在 SQLite 的测试 façade 下复用 sender，由本地 MockTransport 接收，不能称 PostgreSQL 或真实书生验证。

## 精确批准与发送

普通 `ApplicationGenerationPolicy.live_request_allowance` 仍为0。新 `ApplicationGenerationActivation` 只引用独立 `pa-intern-generation-approval.v1` 批准命名空间，不能借用原自然目标 CSV 会话授权。环境配置默认 `application_generation_activation_enabled=False`，`application_generation_live_id=""`；单凭 token 或 LIVE 标志不能发送。

准备冻结：完整原生 GoalCard 版本/hash、项目/用户/运行身份、一份授权 TXT/MD 精确资源与hash、全部当前授权指纹、软件指纹、唯一未来 generation request key、固定模型 `intern-s2`、既有固定 endpoint、账号 quota subject 和预算。批准另需精确 scope 指纹、明确 consent、费用说明与原 key。批准期限从首次批准时开始，至多300秒；重读、重提、等待与恢复不延长。应用和批准都是内部预览，无正式发布许可。

预算只可收紧：≤3次请求、≤1次 `resource.read`、≤1次候选修订，≤64000保守字节加输出预留量、每次输出≤1024 tokens，发送≤32768 UTF-8 bytes，共享账号配额有效RPM≤1。64k是保守预留包络，非 tokenizer 精确实耗，也非货币封顶。RPM等待在尚未预留的后续阶段持续核时限/当前授权/心跳；任何未知或失败的已预留发送均不重发，不退还批准请求槽。

预留与真实 Attempt 同事务；独立 charge/seal 与事件锚集合双向一致。实际发出前，重核当前 provider/mode/flags/live ID/凭据请求头/Goal/资源/授权/取消/lease/fence/预算，并先持久化不可退还的 sending 标记。收到响应先保留完整 bounded raw JSON、usage和返回模型别名证据；每阶段经过实际读取或候选核查后单独封存结算。错误候选最多一次修订；失败/未知 usage/错误模型/额外工具/截断/超限/撤权/过期/竞争不产生错误通过。已封存响应不被后续提交错误改签；独立失败事件保留最终拒绝。

最终候选只为 `PARTIAL`、`goal_acceptance=NOT_RUN`、`semantic_status=UNKNOWN`。最终事务写前/写后重核当前条件及原 lease 时限；过期、停止、撤权或迟到结果回滚。来源入口先按元数据/资源ID/原批准ID授权，再读取完整私有 Run/Goal/合同/资源内容，原ACCEPTED命名空间防止删除新标记降级。

## 用户入口与复用边界

页面只读列出已有批准，默认未选择、预算0；不准备批准、不自动确认、不配置凭据。显式选择后冻结精确批准与其原请求key，POST受理仅作提示，原key GET验证完整冻结合同后才持有Run ID。未知POST只原key读取，不自动重发。目标、身份、项目、页面、应用及单调编辑代次防止迟到回应接管内容/导航/焦点，编辑A→B→A仍失效。

模型先选择授权 `resource.read`，实际工具回执进入下一次请求；随后模型返回完整 ActionSpec/AppManifest。服务端验证实际收到的候选，保留模型选择的步骤ID和端口，而非用固定四步图代替模型规划。此有限family只接纳一节点 `text.literal_evidence`，不是任意DAG或摘要生成。输入词大小写敏感、非空无首尾空白≤80字符；材料≤4096 UTF-8 bytes、64行，命中≤16行。结果为完整匹配行及精确来源/行号/hash，由独立确定性检查复核；自然语言目标的语义质量仍未知。

确认原模型候选后，可以显式打开绑定另一份 TXT/MD 的原生新目标，预览并确认 `pa-model-literal-material-binding.v1`。只替换明确 app/action/resource/Goal 身份与版本槽；实际模型 workflow、binding ID、映射、schema、check、budget与 `origin=goal` 保持。完整新目标由人明确绑定，不能称模型理解了新目标。新无令牌运行身份只获得新资源 `resource.read`。独立原始模型候选/确认、原资源当前审计权限、双seal和精确新材料/新目标共同复验。

新绑定使用独立 task_extractions kind 保存来源，不伪造 P-B 完成任务，不复制 GA_APP_CONFIRMED，不增加第二条原Run唯一确认记录。旧模型请求、原确认、原应用和旧结果保持；冷新Store、关闭provider的Worker读取新材料，提交新词得到新结果，旧材料词在新材料不命中。来源仍为有权读取的审计依赖，本片没有无源内容授权。

新增实现改变软件指纹。原显式文本软件接续白名单未放宽；不能证明兼容的旧版本仍保守拒绝。本片测试新生成应用的冷Store；真实旧源码/旧库升级 NOT_RUN。

## 后续真实调用提案（未授权、未执行）

拟模型为 `intern-s2`，仅既有 `https://chat.intern-ai.org.cn/api/v1/chat/completions`，不查询 models，不改 endpoint/TLS/网络权限。一个有限目标最多3次请求：首次只给冻结目标/来源ID与hash/严格schema和tool定义；书生选择读取后，第二次加入本份获批材料和实际读取回执；仅无效候选时第三次加入原候选和诊断。无答案gold、其他材料、凭据、历史结果或隐藏推理作为输入。

本轮实际真实请求数0、实际费用0。输出≤1024 tokens可能不足以完整表达清单，截断会失败；不能预许成功或自动扩大预算。真实费用与账号额度本轮未查询、单价未核实，`monetary_spending_cap=NOT_ESTABLISHED`。未来收费估算应按获核准当前输入/输出单价与实际token计费，并在已核实账号硬预算下另行获批；不能将64k字节预留量当成货币封顶，也不能把测试consent当成真实账号授权。

## 验证与交付

实际作者与独审计数、原失败、source冻结、SQLite/HTTP/JSDOM证据和推送核验在[本轮证据](../evidence/pa-intern-provider-20261012/README.md)列示；本段只记录已结束的实际测试。PG、Windows、原生浏览器、真实书生/费用、人工语义与真实业务价值、完整P-A/P-B、正式发布、部署、远端CI均未取得本轮验证。既知被拒浏览器与Forbidden CI路径、已取消旧窗口均未重试。

2026-10-12 最终候选r5作者56PASS/0FAIL/ERROR/SKIP；独审68唯一PASS/0FAIL/ERROR/SKIP，其中56与作者重叠，另12独立fault。先前完整相邻675节点回归实际587PASS/84FAIL/4PG前提SKIP：82项旧软件接续在未获准兼容门被拒，另普通None-keyword接口与无关CSV撤权前ledger查询各1真实失败，后两处已修并实际复验。82仍为实际FAIL，不改标SKIP、不以新P-A通过替代。新增两模块及contracts/db/worker/goal_applications/text_apps不在旧软件允许变化集合；两个旧锚实际CLOSED_REJECTION，白名单保持原集合。此候选只完成新的有限P-A适配与新材料链，旧软件接续仍为明确兼容阻塞，完整R0/P-A/P-B不签收。
