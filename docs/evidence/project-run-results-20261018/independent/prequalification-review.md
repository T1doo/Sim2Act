# 项目历史→同Run成果：WIP 非作者源码预审

范围：基线 `2c21d278dbe0d46e05c4ba4cccd473a8edfa4716` 后唯一生产diff `src/sim2act/web/app.js`。仅只读源码/Git，不运行产品、HTTP、Worker、模型、SQL/DB、pytest/collect或网络。root仍唯一仓库写入者；所有旧sealed目录保持未写。

结论：最新已读修正中，两个先前静态P2已收敛；未发现剩余确定P1/P2阻止继续冻结与必要定向资格。当前仍是WIP源码预审，不声称功能或迟到场景实际PASS。

## 发现原件与修正

P2-1：最初WIP `renderInternalTaskResult` 用 `Number.isFinite(result.sum)` 识别CSV。现有 `tools.py:351` 与 `csv_reports.py:15` 的sum是精确十进制字符串，原 use.js 同样要求string；因此正常旧CSV会失去求和摘要。该发现来自实际源码静态读取，未动态复现、未保存成冻结修前源码原件。最新改为 `typeof result.sum==="string"`，保留精度并按原CSV字段显示，不转Number。

P2-2：最初WIP把含instanceSelection/runSelection代次的完整current挂为engineering.selectionCurrent。导航等待原实例/Run时，用户同app另选实例或Run会让原controller自身++代次后立即失效，旧导航finally还clearApp，擦掉用户新选择。该发现也是静态控制流推导，未冒称动态复现。最新拆为scopeCurrent（身份/connection/project/原Run用户选择/workspace/app/view）与current（另加子实例/Run代次）；showApp只挂scopeCurrent。同view新选择不会使engineeringCurrent自失效，旧链current=false只停接续；finally在scope仍当前时释放临时fence，不因子选择变化clearApp。两个P2的最初消息和当前收敛状态保留，不将修前WIP写成通过。

## 最新控制流核对

- 入口要求所选项目Run仍有效、同上下文无正在导航；新的导航捕获token、identityConnectionGeneration、project、activeRun与runUserSelectionGeneration、workspace和app代次。后台showRun(false)更改runSelectionGeneration不会误杀已启动导航；明确新项目Run选择仍会使其失效。
- 原instance GET后核iid/project/source_app_id，且instance.runs必须有原machine Run并匹配app_run_id/release_id；showApp原控制器核app.id/project，本次validateSelected再核runtime与原instance相等。最后原Run重读仍核machine id/appRun/release，复用既有showInternalInstance/showInternalRun及同Run owner入口，不复制自然成果控制器。
- 全部新增网络调用均GET；目录/实例/Run读取会经过原backend当前授权/来源/版本证明，没有新executor/API/Grant/Principal或任何自动POST。历史STALE、撤权和当前内容门不被绕过。
- 自主切换到apps工作区只在原instance读取完成且当前上下文仍有效后发生，立即更新预期workspace；showApp新代次由onSelectionStart回填。另app/账号重连/项目/workspace变化会使scope失效。旧链finally只处理挂着自己scopeCurrent的工程视图，不清别的app或新导航对象；子实例/Run变化由current停止旧链，其原controller能继续。
- 双击与后台重新渲染的按钮共用internalTaskNavigation.current，且旧finally只有对象仍为自己时才清pending。按钮的selectedCurrent只用于开始，避免后台普通回读生成新按钮导致旧导航失效；账号/connection/workspace锚仍保留。
- 结果摘要不再把所有internal当CSV或推定模型0。只有string column/string sum/非负整数count才显示旧CSV摘要；规范清单和其它结构化结果显示对应提示，并让用户明确进入原应用查看。同Run owner只复用原入口，未自动PREPARE/DECIDE或下载。

需要实际资格的最小内容：项目历史选择真实自然结果并显式导航到正确app/实例/Run/owner；旧CSV精确string摘要；导航中必要的用户另选与背景回读控制。无需重跑图/锁、PB长链、关闭/下载或其它旧矩阵。源码逻辑未发现阻塞不等于这些行为已经实测通过。

最新读取app.js为 129539 bytes，SHA256 `cc0924048f2e8ef0438bd82f711203e5fe15924a4ecdcb479b2da80fee37aa85`。本报告只背书该读取版本的有限静态结论，不预先背书后续未读生产变更。新目录保持未封存。
