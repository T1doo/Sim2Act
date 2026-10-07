# 已保存内部CSV实例的业务使用切片

基于冻结 `bd56f8080f7ffd96ce1c8e59d305e48a7ab84a74`，独立本地开发；未混入 Windows CI37577897873。此 CI不能验收新增use.js。范围与事前验收见 ../../F2/ApplicationUsePlan.md。

用户可在应用页直接打开已有可信CSV实例，选择固定材料的另一数值列，提交正常异步AppRun，刷新本次状态和结果，查看保留的历史版本。关闭会话重开只读取历史，不自动提交。版本、材料、来源可展开核对；页面明确未发布内部版本和目标语义验收未执行。没有新增Release/Instance/Grant/Principal业务创建，没有数据库结构、worker、模型、Replay或正式发布开关变更；API只新增use.js静态路由。

真实本地HTTP/JSDOM+正常Worker专项：两个有效数值输入分别得到合计12和3、独立Run和结果v1/v2；另一个文本列通过正常worker失败，旧成功仅为历史。双击只一次POST，接受回执丢失后相同instance/revision/release/input/key恢复同一Run；只读失败清空旧画布，手动GET恢复；项目/身份切换及迟到包隔离，冷会话零POST。3持久AppRun、2结果行、Grant/Principal整表完整行不变，模型适配器若调用即失败。专项最终1PASS，相关75PASS/2SKIP/1DESELECT；PG和受保护浏览器边界保持未测，不把JSDOM称为真实浏览器。Ruff、mypy34、Node语法、diff检查通过。

开发失败保留：初始夹具Release返回值解包错误分别导致TypeError和ValueError，修正实际3项返回值后通过。独立真实HTTP审查复现提交期间旧成功仍显示为当前、ABA重开后恢复入口及冻结列不同步、合法格式但不属于实例的接受Run回执误解锁；产品修正为立即清空当前结果、共享pending只同步同上下文冻结列和恢复入口、selected回执必须出现在所选实例的runs且instance_id匹配，否则清空并保持只读恢复锁。独立终态与日志另存，不覆盖初始FAIL。

新切片真实浏览器、PNG、PostgreSQL、Windows/Win11均NOT_RUN。正式发布、换材料授权、通用应用、目标语义验收、完整P-B、F1/AT02不提升。真实预算0，没有新实验身份、LIVE/model查询、外部业务请求、额外push/CI或恢复包。

独立终态：6个真实HTTP oracle PASS（3+1+2），覆发送中当前结果、ABA冻结参数/同键恢复、两个实例来回、未绑定回执拒绝解锁、已接受GET-only恢复、实际撤权403/版本负例；见 independent/review.json 与日志、原失败。撤权是独立负例夹具既有授权的测试操作，页面运行未改变任何Grant/Principal。可重复oracle保留原执行路径于脚本；fixture数据库和整树未复制。

合并建议：d069e03已包含9f步骤与c041ace等价文档，不重复cherry b874。与本切片合并新增app.js项目切换handler冲突，须保留d069 clearRunDetail并在开头clearApplicationUse(true)；另Plan/Log追加冲突按两分支原记录拼接。merge-application-preview-merge-review.json与merge-preview-resolved-app.js仅建议，组合运行/native未测，未实际合并或push。
