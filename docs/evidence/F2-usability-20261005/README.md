# E12 / 可用性、来源边界与小范围样式收敛

基线6b008b2，路线/验收事前提交1953564，见[下一阶段路线](../../F2/NextSteps.md)。固定MOCK目标候选与可信PREVIEW提取是不同工程子集，均不代表真实模型生成或完整P-B/AT10。零LIVE/模型请求；F1/Win11/正式发布未签收。

[独立只读复核](independent-review.md)复现4项具体缺陷；只复核基线，不独立验证主开发修复。修复：goal_candidate_requests锚定来源不可移除/添加；所有CSV预览候选核查完整固定模板/schema/接线，P-B复用同一校验而不重复模板逻辑；direct app创建与preview选择世代保护/重复提交/加载与错误反馈；DecimalException转换为DomainError，guidance同时核查可累计性，溢出禁选、API直接提交保留FAILED历史。

11新增持久专项（来源删除/JSON null/改接线/直接模板接线、两溢出例、5类源/目标权限自然过期）PASS；全[SQLite](sqlite.xml)214PASS/5平台专项SKIP/2警告26.11秒。ruff/mypy17模块/JS语法/diff通过，原V5/冻结AT不改。既有Starlette警告与并发首次Pydantic metadata警告保留，不为了消除警告改身份或验证要求。

[20项DOM结果](dom-results.json)，真实本地HTTP及产品JS、Node/jsdom：原提取正常/新材料/失败/冷页/导航、direct创建加载/成功/失败/迟到不抢选择、preview迟到不覆盖同app重选均PASS；stylesheet解析无jsdom错误。复跑：先运行E11/browser-fixture.py，再执行本目录dom-regression.cjs（测试工具jsdom安装于/workspace/browser-tools，产品未加依赖）。**DOM不是实际浏览器截图或视觉PASS**。

CSS仅增量改善现有配色/字号/行距/间距/表单尺寸/焦点/禁用态/状态/手机单栏规则；保持三个工作区及静态架构，没有新框架。无实际渲染审阅，重大视觉重构未做。工具目录没有可调用平台浏览器，官方runtime show退出1且未返回结构化连接；原Chromium无可用sandbox仍BLOCKED，不使用--no-sandbox、不访问私有认证或管道、不改系统安全策略。真实桌面/手机视觉验收见NextSteps，仍为依赖。

精确源码d3de155ba23cd5ba824f10f398f34b25c76e1817普通push，ServerCI37343525441/job111876274963 completed/success（2m36s），PG219PASS/0FAIL/0SKIP/1旧警告70.78秒。Setup/现显式迁移/最小应用角色业务CRUD/原生API-worker smoke/ruff/mypy17模块/Report/Cleanup均PASS，server stopped；[终态](windows-run.json)、[精确结果](windows-results.json)、[89源文件hash](source-hashes.json)。Server2025Datacenter/build26100/镜像20260925.250.1/PS7.6.6/Python3.12.10/admin=true/EnableLUA1/原生临时localhost PostgreSQL。GitHub保留固定动作Node20被平台强制Node24的注释，工作流未改。权限/来源证据不签收完整P-A/P-B、原资料解耦、目标语义/Release或F1。

主开发修复回归通过不替代独立修复复验。合成8071服务已停止；文档收尾只普通push，不重复CI。
