# 有限四步文本任务与 P-B 提取：实际证据（2026-10-12）

合同见 [TextFourStepExtraction](../../F2/TextFourStepExtraction20261012.md)。单一仓库写入者root，原main/coredev/3e890e CSV分支不改；分支dev/pb-text-multistep-20261012自已推送1ab405fa5a413e9812744d39b7c0d51c9265ee3d接续。

## 最终实测分母

- r11作者：55唯一PASS，0FAIL/ERROR/SKIP。新43backend+4实际HTTP/JSDOM/cold NoModel Worker=47；两个已接纳旧源的正常冷续用/真实FAILED历史/撤权内容与metadata stop8PASS，另50有意deselected。原新scope三个私有cell屏障断言0blocked，范围/JSON投影限制在测试注释中明确，不称整个数据库所有body均零读。
- r11独立：56唯一PASS，0FAIL/ERROR/SKIP；43backend+4UI+7额外后端+2受控原key页面。47与作者重叠，9额外；不与作者或旧535相加。实际typed后过期预算BUDGET_EXHAUSTED，全DB零写、4真实前缀保留；Attempt污染与input宽等均409拒绝，删双RunScope/ACCEPTED且坏binding+撤权403与5保护Run cells零求值；错key/正确body但另一真实app替换时receipt不设、Open禁用、无额外POST。
- r10作者完整回归：535唯一=523PASS/12SKIP/0FAIL/ERROR；新45、旧文本291=285P6PGskip、CSV199=193PASS/6SKIP（4PG前提缺失、2旧源码archive缺失）。真实执行属于r10。r11仅私有新家族bound增加唯一完整ACCEPTED header校验、独立oracle拒未trim词，两测试；412 src/tests（含全部web）原字节相同，AST唯2私有函数，另final47与旧8实际fresh，不把旧535改写为final全跑。
- r10独立54唯一最终PASS，原55执行含1expiry lease夹具FAIL及修后1PASS；准确r10报告不重签未来r11。

最终414 src/tests map `ba77f3195c17bc1015ced6c15224240f8a64f54020d06fa56a324f3f85e9351a`；68实现PY（排config）`82a9ded4897962cb81e8e0d05a2195a3686e60bbe0032ac25316dc2d793ae4ab`；pyproject `49f68cb7901e719cd014141c69e5fa9ea562f51e9b9c40acd122ace6f2085d81`。作者/独立前后source零差异。9纯内核文件相对1ab原字节不变。完整结果见author/actual-results-final.json、frozen-r11.json、r10-r11-byte-bridge.json及JUnit/log；SQL ledgers gzip为无损原库，原SHA/压缩SHA列明。

## 失败与中断保留

原未freeze静态5项和r8残留报告全部保存，不倒签修复版本。r8独立三实际core失败：AppRun.input True→1仍获inspect/proof200；Attempt行污染仍获model_requests0证明；删除双RunScope/ACCEPTED且坏binding/撤权，最终403但先求值5个Run私有cells。这不是已证明响应泄露/真实攻击。另r8精确字节HTTP/JSDOM错key反例：另一同项目真实app validFP被接受为原intent并启用Open。源码快照、SQL/页记录和原manifest不改。

作者初轮14schema FAIL、14普通GoalRun accepted格式 FAIL、13P1HTTP码期望FAIL、27P1OUTCOME_UNKNOWN码期望FAIL、28P4NameError夹具FAIL、32P、r7 37P3重复barrier清理夹具FAIL、r8 40P均原log保存。名为review-blockers-red的4个FAIL也是缺import NameError，不能称已实际复现其产品阻塞。r1 command127是pytest未在PATH的工具设置错误，随后用既有.venv，不计产品FAIL。r1页面3P1FAIL是checkbox夹具只会置true，修后false实际PASS。r8独立expiry+10000s/后+60.001同时过lease，原零写断言已通过但期望BUDGET实际VERSION_CONFLICT；最终仅续真实lease120保留run budget60，正确预算反例PASS。独审r7停止确认substring误判自身shell属bookkeeping错误，原日志及精确PID更正均保留。

r7/r8/r9仅明确自己启动的精确测试进程SIGINT后再改源，INTERRUPTED与实际partial/退出分别保存，不签终态PASS；未杀未知进程、未换环境/工具规避禁止动作。初期作者失败log没有完整每轮源码快照，精确freeze/桥从r7起；独审r8核心红例有准确source快照/完整map。

## 准确剩余条件

这是当前授权TXT/MD有限四步单次提取，源审计依赖仍须可读；不支持任意DAG、软件续用链、旧撤销内容独立逻辑或模型生成。新应用自有当前Goal、owner PENDING，人工提交UNSUPPORTED、技术语义UNKNOWN、发布false。late hash后可能只读GET，但后续current门忽略结果、不得设receipt/Open；未签所有异步窗无只读请求。

Windows、PostgreSQL、native browser、真实用户旧库升级、真实模型/付费API、真实owner/人工语义、部署、完整P-A/P-B NOT_RUN。12旧完整SKIP为10个PG前提缺失与2个旧源码archive缺失（67c6ccc8、f13升级；见原JUnit）。新模块/变更文件ruff PASS，全src/tests ruff10与mypy5既有基线不变，不称全绿。Forbidden CI保持停止，没有查询或声称精确SHA CI绿；历史精确取消候选安装窗口永久NOT_VERIFIED，未重新执行/导入/改名。

交付完整SHA、正常push/远端及clean校验由最终回复与delivery-verification.json提供。证据文件以artifact-manifest.json的原字节SHA为准；历史raw空白不清理以保留完整内容。


## SKIP 分类纠正

父级只读复核指出此前“12全部PG／CSV6PGskip”的分类错误。总数535=523PASS/12SKIP保持：旧文本291为285PASS/6PG_SKIP，CSV199为193PASS/4PG_SKIP/2缺旧源码archive_SKIP；合计10PG+2archive。两项实际旧源码升级仍未跑，不能隐藏为PG或借r10给r11全仓签收。原README、清单、manifest已按原字节保留于 [纠正历史](skip-classification-correction/README.md)，原XML、作者/独审报告与测试输出不改；精确逐项分类见 [汇总](skip-classification-correction/summary.json)。本提交仅文档与证据分类纠正，没有新功能或新测试。

## 父复审页面P2补正

[页面纠正](parent-review-corrections/README.md)记录原Open两失败、pending迟到R1一失败和修复定向3＋2PASS；69后端PY（含config；68实现PY）不变，只改两JS及定向测例。原r11验收证据属于原冻结，未重跑全仓，也不替代后续独立定向复核。
