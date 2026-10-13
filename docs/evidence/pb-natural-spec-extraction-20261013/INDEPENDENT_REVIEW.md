# 最终有限独立工程审查（r2封存）

结论：**有限独立工程 PASS**，没有剩余阻塞代码发现。冻结HEAD `507b322e73758f4ad2ae2794382f5dee69760630`，产品代码e3b4fd84、资格62aa9fd0，对照68812ce。本报告的通过只覆盖明确的静态合同和本轮独立实际5例；作者r2 negative/UI仍在运行，尚不计其结果，不声称完整P-A/P-B、真实模型或语义验收通过。

独立小集真实退出码0，XML独立5个testcase/5个唯一ID、5 PASS、0failure/error/skip，408.68秒；XML SHA256 `1be3f69f1b1c92439e6ae8fa05c6a67815c26172959629a1fc48274199298f88`。包含单模型/双模型自然成功源到编辑P-B的新材料冷Worker、P-A material-binding成功源到P-B冷Worker，以及status/effect-pointer两个读前门禁故障。cold正向均真实新Store/TestClient/Worker、新AppRun/typed结果，输出与模型wire来自新材料，不返回旧答案。source默认图和人工edited图保持分开，编辑介入不是自动通用化/语义证明。

八份真实worker-claims日志共八次claim，每Run一次、最终均SUCCEEDED，原created_at/accepted clock与fence断言成立。**失租重新claim分支 NOT_EXERCISED**；最多三次驱动的静态限制不能替代动态恢复证据。正常claim已经足够完成本轮双模型，与旧失败并列保留，不能说消除了所有负载下的失租。

全部440个src/tests/pyproject文件的before/after/snapshot/current SHA逐一一致，HEAD保持、工作树无产品写入；源产品字节与62aa9fd0完全相同。区别仅三份测试夹具：有限真实Worker驱动、UI真实resources页签、明确run_id/instance RPC。驱动只在RUNNING、未cancel、lease已过、原deadline内且无unknown时允许正常claim；新fence/CLAIMED唯一、主体/项目及原clock恒等，最终真实SUCCEEDED，未手改Settings/lease/Run/key。latefault仍单次once不重试。

精确qualification原73+新增pb_natural_specs=74文件；config.py原排除、sole-module-literal zero64 normalization、pin、完整字节map、ANCHOR_HASH/anchor原件、CHANGED、两来源集合与算法均核对不扩。review_candidate正确指向产品代码e3b4fd84，最终507仅test变化，不偷换资格绑定。详见qualification-static.json和source桥。

## 完整静态范围

已读V5 P-B/F2-T03/AT-10及本轮合同，复核独立pb模块、api/apps/自然compile/spec origin与audit、app_jobs同调用Release复用、UI及全部新测试。新入口只提取完整验证的原自然SUCCEEDED internalRun（含明确P-A binding来源），不提取PB链；默认recipe来自真实成功图。原源与目标当前授权分别在正文前核验，源成果四组独立scalar指针一致并授权后才读正文；原R1/R2/R3具体路径修复有静态与所选动态证据。

raw audit为每次新鲜事务内读取，封存完整source Run/contract/binding/AppRun/typed/Release/Attempt/Operation/Intent/effect/event/reservation、原P-A audit、源origin marker/META/BIND seals与实际source Goal头和版本；seals排序稳定。入口和final完整replay、原lease/deadline/fence/账本与rollback保留。同调用已验证Release返回仅消除重复read_release，无跨调用cache或授权/预算扩大。

natural闭合编译受控重建task_run/source_run_ref/spec_task，独立数据库kind+marker+seals一致、拒绝移除/降级/混合来源。编辑限已有finite Recipe，ports/依赖/prior反馈/focus/verify/save结构与source预算封闭；无旧答案/正文进入candidate，新sample仅SUCCESSFUL_SOURCE_ONLY、edited NOT_RUN。review仅读→明确精确confirm→原子独立app/runtime和两Grant→GET原key完整复验→另行内部Release/实例。UI编辑单调代际、身份/项目/app/instance/workspace fences，unknown保留同一内存pending仅GET，无迟到响应交接或重复新意图。

## 分母、历史与边界

旧独立5例4P1F、XML/日志/DB诊断保留在../final-independent。失败位于prepare原source仅READ、无Attempt、RUNNING，不进入P-B；Worker.once真实保证取得工作而非终态，expired guard的DomainError可由fenced fail_owned让出而不写错误。此路径静态与DB形状一致，具体异常未保存，不把猜测称捕获证据；旧失败不加入新轮PASS，也不删除。作者其它早期fixture/Release/no-name/lease失败同样保留。

旧作者120项回归正常退出、120唯一/120PASS、无fail/error/skip；before/after原440相同，新产品src全字节同，差异仅三份不在该组所选模块内的P-B test fixture。old-regression-source-bridge.json给出确切桥，不重复跑120，不把它说成全新HEAD完整closure重跑。

旧作者negative实际27唯一/27PASS，与独立5有两个重复case，不能相加成唯一32。四latefault旧DB码已核source_revoke→GRANT_REVOKED/WAITING_RESOURCE、source_changed→VERSION_CONFLICT/FAILED、cancel→VERSION_CONFLICT/CANCELLED、bad_output→VERIFICATION_FAILED/FAILED，无typed/SAVE且保留REJECTED_KNOWN raw。latefault源码段与产品src62→507同字节；作者r2实际码和27/UI5终态尚待后续独立closeout，本目录不据进行中点数充PASS。

读前barrier只证明其Run/contract/resource/receipt/intent观察集，未覆盖所有Attempt/AppRun/typed列；新入口metadata scalar准许读取。同事务/合成transport故障与SQLiteUDF观察不称真实外部并发攻击或API泄露。页面证据为JSDOM及真实进程内HTTP桥，不称原生浏览器。

真实模型请求/费用0、semanticUNKNOWN/NOT_RUN、ownerPENDING；完整真实P-A/P-B、真实资料语义、人工签收、正式发布、PG/Windows/原生浏览器/CI/部署等NOT_RUN。源退休或撤权后独立无来源审计能力不承诺；当前源仍需授权。旧取消安装窗口永久NOT_VERIFIED；实际model/reasoning/Fast/service-tier无可核验工具，不称已切换或关闭。

本目录在报告、summary和SHA manifest生成后停止写入；作者后续closeout另目录保存。
