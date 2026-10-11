# F2-T03 / AT-10：有限文本成功运行提取

基线 e17d7c44098492745b23a57adaa715adb490119d；root 单一产品写入者，既有独审只读。新分支 dev/pb-text-extraction-20261011，原 V5 §4 P-B 与分阶段 F2-T03/AT-10 为合同依据。

只从现有目标生成的 text.literal_evidence@1 应用的实际 SUCCEEDED 持久 AppRun 提取。拒绝失败、未终态、取消、错误、未知操作、额外操作/结果及模型 Attempt 污染；纯字面 AppRun 的真实 Attempt 数为0，其上游目标生成 Attempt/wire 沿用原独立来源校验。核对身份/项目/实例、冻结绑定和运行合同、Release、类型化结果版本、精确步骤 intent/receipt、原材料 hash 与当前授权，并用既有完整行号/引用检查器重验。不能由旧结果、PARTIAL 生成任务或人工 JSON 构造完成来源，也不允许递归提取或 Replay。

用户选择同项目、绑定不同内容 TXT/MD 的已有初始应用作为授权域。提取只插入独立 app_drafts/task_extractions，沿用其 runtime 和现有 resource.read 交集，不新增 Principal/Grant。原完整 GoalCard 保留为来源 provenance，其 resource_refs 属于原目标；新 Manifest 的材料绑定和权限/依赖锁指向新材料，运行变量仍为 term。逻辑、输入输出 Schema、限额、检查及只读效应复用原登记执行器，不追加算子或模型请求。

新应用以独立 task_run 来源标记验证，不能继承或伪装原 goal_application。新应用、内部版本及实例的 owner 为 PENDING，不复制任何旧声明；当前 owner 签收入口仍限定目标生成应用，新 task 应用不得通过它继承签收。所有技术语义 UNKNOWN、正式发布 false、LIVE0。当前来源审计仍保守要求原来源授权与证据有效；冷计算只使用新绑定和新 term，不声称来源内容已退休或完整 P-B 消除所有审计依赖。

API共用运行范围检查先在同事务内只取匹配身份的项目元数据、核验项目owner，之后才读完整Run；撤回材料授权仍保留owner取消/控制。确认 POST 冻结来源证明和目标指纹，事务内重验、严格幂等冲突与全部回滚。新文本入口以原 key GET 读取已接受回执，不用 POST 重发恢复；成功 POST 的 ID 仅作提示，必须匹配 keyed GET。文本候选自身封印完整 extraction_request（含原 request_key），安装前读取真实候选并独立计算 candidate SHA-256，精确匹配回执与完整来源/请求/身份/目标授权域及新 app ID；协调替换同来源/目标但另 key 的应用亦拒绝，并冻结工作区、身份连接、应用、目标、源实例/Run及材料/名称编辑代次，编辑撤销与迟到回包不得接管选择、草稿或焦点。未知结果保留原 key，显式只读恢复。

采用合成来源 provider 的 test-only transport 准备既有初始应用；实际生产 API、正常 Worker、冷 Store/API、HTTP 资源加载与离线 JSDOM 全链另验，绝不把合成 provider 当真实模型。验证新有效输入、未命中和错误输入、污染、撤权、跨 owner/project、竞争、取消、迟到结果与历史保留。原失败日志与独审另存于 [本轮证据](../evidence/pb-text-extraction-20261011/README.md)。PG、Windows、原生浏览器、真实模型/付费API、人工语义、旧源码升级、完整 P-B/AT-10及发布/部署未跑即 NOT RUN；精确新 SHA 远端 CI 未验证。
