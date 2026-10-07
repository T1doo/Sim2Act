# 普通任务回读失败后的安全画布（本地切片）

基于 `9f30cd2e009211fd983d98ef8103ca5448e8dba5`，独立工作树和本地分支。正在运行的标准CI源是 `82ffe61`，不包含此切片。范围和剩余三类核心演示能力见 [事前计划](../../F2/TaskReadFailurePlan.md)。步骤切片的后续独立来源/权限/UNKNOWN复核已单独保存，不改历史签收。

用户明确选择任务时，旧结果、步骤、命令和核对入口立即清空，显示正在读取；inspect或核对回执读取失败时，不再显示旧成果，区分权限拒绝与读取失败，并明确无法判断任务当前技术状态。读取失败不等于技术FAILED。该失败详情停止自动轮询；手动“重新读取任务”只读原任务，不重新提交、续跑、核对或发送模型请求。切换项目或身份还清空隐藏的核对响应、证据和ack。旧选择/身份/项目的迟到响应、旧重读按钮和旧命令不能改新画布或发送写请求。

实际既有授权API正例为正常Mock worker持久PARTIAL、2MOCK Attempt/1VERIFIED Operation；真实跨身份inspect403、网络丢回读、明确合成WAITING_RESOURCE投影后的真实unresolved API403为负例。合成等待状态不是实际外部未知请求。新18项HTTP/DOM检查共74 GET、0写请求；回读前后Run/Attempt/Operation/Event/Grant/Principal完整行相等。已有组合41用户检查/7刻意意图/7Run/2MOCK Attempt；共享原生oracle模块39项通过本地真实HTTP/JSDOM，7Run/2MOCK RECEIVED/1VERIFIED、Grant/Principal计数不变。不同夹具不合并预算/任务数。

验证：初始专项1PASS；相关首次1FAIL/25PASS/1PG-SKIP/1browser-DESELECT；强化driver等待后26PASS/1PG-SKIP/1browser-DESELECT（38.00秒）。最终项目/身份清空变更后的专项组合7PASS/1PG-SKIP/1browser-DESELECT（6.86秒）；独立发现与专项2PASS，最终协议/历史兼容2PASS/2browser-DESELECT。Ruff src/scripts/tests、mypy34源文件、三个Node语法与diff均PASS。

失败与验证错误均保留：

- 正确指定pytest `-o pythonpath=/workspace/Sim2Act-task-progress/src`后，原9f源码实际FAIL“明确选择等待时清空旧详情”；不改原工作树。第一次仅设置PYTHONPATH被pytest项目配置覆盖而运行新源码PASS，不作为旧源码复现证据。
- 原恢复driver只等同步accepted状态就检查activeRun；原遗留旧Run掩盖提前断言。两共享oracle现在等accepted且raw-result含相同持久Run ID，再保留原sameRun/零POST断言，没有放松断言或更改提交语义。
- 独立实际HTTP负例发现有效QUEUED直接换项目残留旧命令（原守卫阻止POST但入口仍可见），原FAIL保留。复用clearRunDetail后同一独立负例PASS，并清空隐藏核对字段。

仅app.js产品改动，两共享oracle的等待加强和新测试/docs；无API/表/权限/迁移/worker/模型/协议网关/工作流改动，无实验身份、真实模型请求、push或新CI。新切片PG/原生浏览器/像素NOT_RUN；Linux已知受保护浏览器启动限制未绕过。完整P-B/F1/AT02/Win11及正式Release仍开放。原失败CI和底层原因UNKNOWN保持，不把当前候选看作根因已确认。
