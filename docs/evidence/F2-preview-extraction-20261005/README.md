# E11 / P-B 可信PREVIEW任务提取工程子集

基线9bd4bac；事前范围提交24e5ba9。独立/workspace/Sim2Act-pb的dev/f1-foundation；原work/旧任务无改动。实现与边界见[F2提取契约](../../F2/PreviewExtraction.md)。源码精确提交和ServerCI终态在后续核实后追记。

可信单节点CSV合成预览成功回执→工具回读/独立整数sum oracle→来源/版本/原条件快照→新CSV明确授权/绑定→column参数化新预览。源旧4.00，新材料40/另一列5，失败输入保留FAILED历史。来源PREVIEW不是F1 Run；未把PARTIAL/UNKNOWN/FAILED标成功，原AT02/V5不改，目标语义NOT_RUN、PREVIEW_ONLY。模型0/无Release/无外部业务写入。

32新增专项本地PASS、1 PG应用角色专项SKIP；源状态、权限撤回（含未选来源条件材料）、跨主体/同主体跨项目、完整模板/回执/候选/新材料篡改、请求键及版本冲突、并发一份身份与两条最小Grant、失败事务回滚、非目标卡直接模板源和独立oracle舍入/资源界限已测。[sqlite.xml](sqlite.xml)为最终全回归记录：202PASS/5平台SKIP/2警告，19.86秒。ruff/mypy17模块/JS语法/diff通过。

[dom-results.json](dom-results.json)：12项Node/jsdom正常/失败/冷页/导航/重复交互检查PASS。使用本地真实HTTP API和产品JS，但**不是Chromium或真实浏览器验收**。复跑：独立mock测试环境安装包后运行browser-fixture.py（8071）及dom-regression.cjs（需测试工具jsdom）。测试工具在/workspace/browser-tools，产品依赖未增加。

[browser-block.json](browser-block.json)：真实Chromium0检查；默认与正式审批启动均因helper所有权失败，保留namespace沙箱尝试仍No usable sandbox；未使用--no-sandbox、未改系统安全策略。真实浏览器导航/可见布局/引擎兼容仍未测，不借用E10旧截图补证。Win11/F1整体/完整AT10/P-B/发布仍未签收。

首次全回归因测试环境未安装sim2act造成2项子进程ModuleNotFoundError（198PASS/5SKIP）；正确editable安装后消除，非产品修复。首次提取专项29PASS/1FAIL/1SKIP发现新材料actual content篡改进入失败历史；修复为加载候选前hash核查，随后专项全通过。保留Starlette弃用警告及并发首次Pydantic schema metadata警告，如出现按实际终态记录。
