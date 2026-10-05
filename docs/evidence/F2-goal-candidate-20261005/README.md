# 目标卡到MOCK候选及受限CSV预览证据

2026-10-05；基线1a2be0d，保留并完成既定未提交切片。人工目标全部已知/假设/未决/硬条件/验收检查以及授权材料hash冻结于版本；用户明确选择一个已绑定CSV及可信csv.sum能力，生成固定1.0-draft ActionSpec/AppManifest，已有preflight验证结构/类型/依赖/工具/预算，再创建仅该材料read/aggregate的24小时preview身份。应用页呈现冻结条件/来源版本、编译结果和输入数值列，预览/历史与返回来源目标卡、页面刷新回读路径已接通。

P-A：仅人工目标分项+明确选择固定可信模板的工程子集，不做自然语言规划或任意应用生成。P-B：已完成任务来源/新资料冷运行未实现，不借用PARTIAL/LIVE记录。生成标MOCK_DETERMINISTIC_CSV_SUM.v1，真实模型0，目标语义/条件验收NOT_RUN，PREVIEW_ONLY/不可发布/非Release。F1未签收、Win11未测、F2正式门不变。

新增goal_candidate_requests由迁移角色既有显式migrate创建并授运行角色业务CRUD；API/worker不DDL。新请求expected_version过期409；同请求键绑定目标版本/资源/能力，重复或并发只建一个候选及一个preview主体/两条所选材料Grant，异参数409。旧候选来源版本不随目标修订改变；详情及预览重新校验完整来源指纹/全部材料授权与实际hash，并验证所选CSV与冻结来源对应。已撤回历史不能恢复权限。选项/候选列表仅授权目标元信息，不是执行授权；打开候选仍完整复核。

取消提交前无请求/候选写入；已接受同步事务不伪称撤销，返回编辑/导航只停止自动打开，候选保留在列表。当前页面同一意图复用request_key，可重试不重复建权限；刷新后依赖候选列表回读，不声称跨浏览器请求键自动恢复。失败保留编辑及明确状态；预览失败保留真实历史，无成果伪造。候选与应用异步读取均校验选择generation/当前项目，保持E9目标卡竞态修复。

24项新增工程回归（SQLite23PASS/1PG角色专项SKIP），完整SQLite170PASS/4平台专项SKIP/1旧Starlette警告11.31秒；ruff/mypy16模块/JS语法/diff通过。覆盖目录只读无授权、完整条件冻结/冷读、作用域/跨主体/未绑定/非CSV拒绝、闭合输入/恶意模型执行器、撤权（含未选但仍为来源的材料）、目标/材料/工具版本/条件篡改、幂等/两并发提交仅一次身份授权、预览失败后新输入恢复。PG角色专项使用显式迁移表和限业务CRUD的临时应用角色执行目标/目录/候选/幂等/预览/历史整条API路径，尚待ServerCI实测；其余PG测试仍为隔离test-owner schema。

真实LinuxChromium：正常fill/select/click创建目标绑定CSV、候选、quantity=15/amount=4.00两个新结果/历史/返回；14候选交错与失败检查PASS，3页面刷新回读检查PASS，E9原11目标卡竞态回归再PASS。browser-regression.js仅扣留实际HTTP响应制造确定交错，不替换返回数据；手工添加无效列Option验证后端失败历史，非正常可选项。一次新增validation字段复查发现fixture Python旧模块尚未重启，重启全新夹具后最终14完整PASS；截图路径改绝对路径后捕获。最终browser-results/refresh/normal-flow/race-regression及截图保留，截图人工复核；非Win11或多引擎/独立复跑。

复跑候选检查：运行browser-fixture.py创建临时SQLite/mock合成A/B项目；agent-browser打开127.0.0.1:8070，填写脚本公开合成身份synthetic-candidate-browser并连接；`agent-browser eval --stdin < docs/evidence/F2-goal-candidate-20261005/browser-regression.js`。每次全新fixture，完成关闭browser/server。角色不是真实用户凭据，模型不启动。E9原11回归脚本路径在上一证据目录，其再跑结果此目录归档。

源码普通push及精确ServerCI结果待定，不预写通过；fixture/browser已关闭，未做外部写入、任意代码、main merge、force或LIVE。
