# P-B 原提取意图：重载后的显式只读恢复

基线为父级有限独审通过的 `1f725e8318a9f3993e782335203d5b2e76085c0f`，新普通分支 `dev/pb-cold-key-recovery-20261018`。root是唯一仓库写入者；开工checkout干净、约25GB可用、默认Git网络正常。复读原V5的F2-T03/T05/T09、AT-10及结果不明恢复合同，接续现有成功来源、精确审阅与by-key回执，不新增执行器、后端协议、授权种类或模型配置。

## 用户路径与独立原意图

原提取面板只在页内Map保存完整pending。关闭页面后原key与独立确认依据消失，原按钮也没有冷页入口。现有服务端GET会当前重新授权并完整重证明来源、目标及已保存应用；但仅拿一个key返回的request/reviewed再自比，不能证明那就是重载前用户确认的意图。

本次在原精确审阅中显示只读原key。用户勾选并明确提取时，在同scope exclusive/ifAvailable Web Lock内，先保存并逐字读回白名单票据，然后才调用原POST一次。发生实际201回执丢失或页面退出，票据保留。重载后用户从统一目录回到同一个成功成果并点击原提取入口；重新核对当前成功来源后，自动发现的是本浏览器原票据，编辑/预览/提交保持锁定。不会自动调用by-key、创建新key或重发POST。用户明确点击原GET按钮才恢复，完全核对后才另行明确打开已保存应用。

票据namespace为 `pb-natural-extraction-recovery.v1`，存储及锁前缀为 `sim2act.pb-natural-extraction-recovery.v1:`，后接principal/project/source app/source instance/source Run五个稳定标识的JSON数组。页内Map也使用这个无token的scope，切换身份时清除相应RAM正文，原持久票据保留。

严格17字段仅含标识、hash及正整数：namespace、principal_id、project_id、source_app_id、source_instance_id、source_run_id、source_app_run_id、source_release_id、source_release_fingerprint、source_result_version、request_key、request_fingerprint、review_fingerprint、candidate_fingerprint、app_id、runtime_id、source_proof_fingerprint。request_fingerprint钉完整ExtractInput及两个原consent；review_fingerprint钉去自身fp的完整原review。票据不含token、请求正文、Goal/材料/成果正文或完整candidate。

## 恢复与未知锁

原 `GET /api/projects/{pid}/natural-spec-task-runs/{rid}/extractions/by-key/{key}` 保持不变：先source_gate的本人项目、Run标量及来源/成果授权，再load_draft、双记录、review/verify。页面先比较服务器完整request/review/candidate/source证明的实际SHA与独立本地票据，之后才在RAM重建原pending，继续原完整回执比较和fresh `/api/apps/{id}` 验证。原Run对应Release/结果锚不误用实例当前Release。每个API和WebCrypto await后核对身份连接、工作区、项目/应用/实例/Run选择、编辑及pending对象代际。

成功删除票据要求仍持同scope锁、原pending对象与原raw未被替换、完整原回执及fresh应用核对完成，且当前代际不变。若另一页已经成功删除持久票据，本页已知RAM元数据仍只允许显式原GET；成功后仅清该RAM，不删除任何新记录。新raw出现、损坏/存储失败、无锁、BUSY、撤权、版本冲突、污染或未知回执均不能放开新提交。权限/来源核对拒绝时清受保护DOM及已知pending正文RAM，保留原metadata与key。

服务端此家族没有NOT_ACCEPTED/CLOSED墓碑或安全关闭未知意图合同。即使票据已保存而POST尚未发送、GET返回OUTCOME_UNKNOWN，也不能据404、超时、403或本地时间清锁。本片不提供清除未知/换key按钮，不借普通spec-run的固定input={}重建或close DTO。旧JS绕过本地协议、用户清除浏览器存储/改用其它浏览器、升级前未留票据的未知请求，没有新增server fence或自动发现保证；不以票据作为授权凭据。

## 有界验收与独审

只新增必要五类实际HTTP/JSDOM场景：实际接受201丢回执→完整关闭旧DOM→冷页原票据→显式GET和fresh app→明确打开；跨账号/项目/实例/Run/应用/工作区/重连迟到隔离；原来源与目标真实合成READ撤销；原回执/新应用及本地票据污染；无锁/坏存储与两页BUSY/另一页成功后的只读恢复。控制的网络投递、WebCrypto或存储故障单列，实际服务器原响应字节保留，不称原生浏览器。

一次本轮fresh种子经原正常生成3次Mock和成功来源正常Worker1次Mock，关闭自有连接后以逐字相同SQLite副本隔离各case，不改行、重签、改时钟/lease/deadline或伪造成功。另一个正常API受理后取消的Run只用于实际Run导航，不调用Worker。每例只允许一次原提取，原有一个runtime、两条既有工具Grant及四条双封印账本；随后恢复只GET，不创建Release/实例/新Run。原行、正常claim/clock、模型wire、HTTP、资产SHA、复制和输入前后映射及finally错误全部留证。只读权限屏障范围与实际捕获单列，不声称零底层JSON标量读取。

源码与测试完整冻结后运行5个新case及一个受影响的原P-B导航控制回归。根仓库只由root采纳，隔离测试作者与非作者合同/源码/原件独审并行；未完成不得预写PASS。真实模型请求为0，所有模型通过MockTransport；Windows/native、PG、真实语义/场景、远端CI及部署未因此验收。

永久取消的旧精确安装digest并发对照窗口保持NOT_VERIFIED：本片不做第二actor prepare、旧/新实现同predicate或安装digest时序比较。新恢复hash等待的导航隔离只涉及本次只读回执验证。原额外性能探针exit139的因果及产品关联仍Unknown，本轮不重试，不删未知锁/进程；旧满盘独审未落盘缺证保留。
