# 正式自然生成前端接线

基础提交6f2e6e78，后续工作树改动，尚未进入新的Windows包。

桌面supervisor把原五字段选择同时传给API和Worker。API将其作为启动时快照保存，不接受HTTP更换。新增按项目/目标读取的natural-generation-readiness接口，先核对主体与项目，再调用原check_selection、original_contract和existing_worker_selection；仅返回匹配目标的原生成键、目标版本/快照、合同/批准指纹和原期限。不创建Run/批准/模型请求，不修改选择、合同、预算或期限。

前端保留原离线入口；LIVE时另读上述接口，只有精确匹配当前Goal、版本、快照与有效期才按原生成键提交natural_spec。Worker仍执行原正式校验。API可读状态不代表生成成功或语义验收通过。

验证：

- 35项原页面脚本/JSDOM合成API检查通过，包括无启动选择、版本不符、正确选择原键提交和未知结果不重发。
- 2项接口/投影测试通过：无选择BLOCKED、跨主体拒绝、原checker必须调用、目标不符与checker拒绝传递。正例使用合成contract/checker，不能视为正式批准通过。
- 10项原双进程SQLite桌面生命周期测试通过；不覆盖新五字段正式PG正例。
- 首轮两个测试因fixture误把Goal头记录当完整快照而失败；改为使用其版本历史中的真实快照后通过，失败XML保留。

剩余：冻结新包，原正式试验准备/批准后重启选择，真实P-A/P-B整链、阶段确认与错误恢复。普通用户仍需要明确选择试验，当前没有热切换Worker；原生操作仍暂停。本轮没有调用模型或修改数据库。
