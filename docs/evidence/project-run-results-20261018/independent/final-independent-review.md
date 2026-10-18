# 项目任务历史→同Run成果与验收：有限最终独审

结论：本轮限定范围通过，未发现阻止普通开发分支交付的P1/P2。项目历史中的自然结果现在有正确摘要和明确只读导航，复用原应用/实例/Run成果及owner入口；不再把所有内部结果拼成CSV或硬填模型请求0。本报告为非作者源码审查及闭合原件纯文件/Git复算，**没有亲跑产品、pytest/collect、HTTP、Worker、模型、SQL、数据库或网络。**

资格源 `c3aa1e4fa569e6ea08174e30811f216392b7ccd2`；原产品冻结源 `49e0e7b026126ba031141944b15f20e28b4358a7`；基线 `2c21d278dbe0d46e05c4ba4cccd473a8edfa4716`。生产对基线仅app.js变化；133生产文件c3与49e0逐字一致。c3只修测试async模型记录器，不改生产/CJS及原assert AST。

## 产品源码结论

新入口先读受鉴权instance，核原项目/source app及该instance的machine Run/AppRun/Release，再用fresh app核runtime，经showApp/showInternalInstance/showInternalRun重读同Run，最终再次核machine Run/AppRun/Release。既有backend origin/授权/版本/STALE门、成果查看和owner状态控制器保持；没有新增executor、API、Principal、Grant或自动POST/PREPARE/DECIDE。

修前两个静态P2均已收敛：CSV sum原为精确字符串，现按原字符串合同保留，不转Number；导航scopeCurrent不含子instance/Run代次，current另检查子选择，用户同view明确新选择不会让原controller自失效或被旧finally清空。后台普通showRun(false)改read generation不误杀已启动导航，导航用明确user selection锚；同上下文pending跨按钮重画防重。agent分支补selectionCurrent传递；泛internal没有steps时只称成果/状态，不泛称人工验收。修前P2是静态推导，未冒称动态复现，原prequalification报告保留。

## 当前实际资格与独立回读

原件在 `/workspace/project-run-results-20261018/attempt-2/`，唯一真实case目录是 `actual-tmp/test_project_history_opens_ori0/`，未使用current符号链接。`execution.json` exit0、107.198395284秒；`junit.xml` 一例 `test_project_history_opens_original_natural_result_and_review` PASS、104.383秒。29是页面checks，不是pytest数量。原case保存9actions、33 API GET、27assets，共60页面HTTP；0POST、0下载、0页面Worker。

本目录 `final-artifact-audit.py` 一次纯文件执行PASS，原stdout/空stderr/JSON保留，独立核对：

- 695项输入before/after完全一致并逐项核当前文件；133生产hash与冻结Git blob一致且等于49e0；直接production map本次也含JSON，共133，不沿用前阶段131过滤口径。
- 33实际API的完整response文本/JSON/SHA与增量`http-responses.jsonl`一致，所有请求GET/无body；27静态资产长度/SHA对当前冻结字节吻合。唯一held行增量日志先写、交付后才补`delivery_released=true`，仅此观察器字段在比较时明确规范化，其余全字节字段不弱化。
- 项目历史实际读取原成功Run并明确双击导航；同app/instance/machine Run/AppRun/Release及typed结果v1保持。原Run为 `run_24f842420c9f409e98867cf51ab89ad0`，AppRun `iapprun_60e23a0164ef42adad378d5b22c1f249`，实例 `iinstance_368ad5a2dc2d5649d7f5c1e53f89595b`，Release `irelease_0a5ad7479d994bc2abdb3c9b2a46379f`。实际owner GET current.output与原typed/Run输出吻合，PENDING、sequence0、历史空，未制造人工声明。
- 实际成果GET `/api/internal/app-run-jobs/run_24f842420c9f409e98867cf51ab89ad0/spec-artifact` 的完整响应SHA为 `590768537274df861f4fde11ea5245806b0afce6320707caefdeb9138e35da72`；canonical清单原文SHA为 `338d85379a68d0f840e6dc37862fde04cd59fbfc0521c0c32e19e370ebcad19d`。源材料完整原文、resource id/hash、输出fingerprint、Run/AppRun/iid/Release/version1、UNKNOWN/PENDING及读取无新模型/写入均由原回执重算。
- 一条真实迟到控制：完整instance HTTP200原字节已接收后，仅延迟交付给页面，用户通过可见控件换到另一已授权项目；释放后scope逐字段不变，旧app/instance/Run/owner/内容均保持清空，且没有新的HTTP、工作区跳转或POST。未用假response代替这条实际200。
- CSV兼容只做明确隔离的synthetic renderer检查：金额sum `9007199254740993.01`原字符串保持、没有undefined或硬填模型0、无ID不生成导航按钮、0HTTP。它不是本轮真实CSV后端回归。

正常单节点自然PA生成3Mock、业务Worker1Mock是后台fixture，不称页面创建。第二轮完整`mock-wire.json`四份request/response与响应SHA已独立核验，fixture业务Worker1，页面Worker/真实模型0。

## 数据与首次失败的证据边界

成功冻结pytest实际执行55表before==after，并保存相同global fingerprint、55张表各rowcount/fingerprint、changed_tables=[]。源码严格断言与PASS已审，但没有持久完整before/after行。本独审只核这些指纹/表集合/计数结构，**没有独立重算55表全部原行或查询DB**；不把执行断言证明写成第二次独立全表SQL核验。

首轮49e0仍为1FAIL/exit1、外54.219032831秒、JUnit51.244秒。正常生成3次、业务1次及原Run SUCCEEDED/v1已到达；Python仅钩sync `MockTransport.handle_request`，实际用async，因此在 `(3==3 and1==1 and0==4)` 失败，页面未启动、没有results/proof。`mock-wire.json`为空，不能说首轮完整raw模型请求/响应已捕获。11条fixtureHTTP原文/SHA与失败JUnit计数可核。

c3新增包装原 `handle_async_request`，await原handler后原样记录/返回Response，transport类与Worker类型守卫未替换，保留sync包装；原计数与所有业务assert AST一致。安装的httpx async实现直接调handler，不经过sync，源码说明该仪器漏采原因，无产品门放宽。记录器修正详见`instrumentation-review.json`。

首9文件保全清单中8个非数据库原件逐完整字节/SHA核验；DB没有读取或查询，只核stat字节数并记录原清单提供的hash，不冒称独审重算DB指纹。首原件继续外部保全，不复制DB/整树/大bundle到仓库。

本阶段合计一条唯一pytest、两次attempt：1PASS+1记录器FAIL，模型调用计数8；其中只有第二轮4次有完整raw模型捕获，首轮4次是计数/fixture终态证据。前失败不被当前PASS覆盖。

## 有限结论

实际只PA普通导航、双击、一条完整200交付延迟跨项目控制；其它账号重连/另app/workspace/同view实例Run supersession及后台刷新防重是源码审查，不说本轮逐个动态覆盖。没有新PB动态、真实模型/真人语义、原生浏览器/Windows/PG、远端CI或部署资格；没有重跑图/锁、局部修改长链、关闭、下载或旧故障矩阵。旧取消窗口、exit139未知根因、旧满盘缺件不补签。

普通push尚由root后续执行，本报告不预先背书远端或之后docs/evidence提交；本独审未访问网络。`freeze-static-review.json`保留过一次猜复数文件名的只读sed错误，明确是原tool-output文本转录、非原stderr文件或测试失败；本次最终纯文件audit没有失败执行。全部方法与规范化细节见`reviewer-method-and-provenance.json`。

本新目录写入`sealed-manifest.json`后停止所有写入；manifest记录自身之外全部文件的path/完整bytes/SHA256。所有此前sealed目录保持未写。
