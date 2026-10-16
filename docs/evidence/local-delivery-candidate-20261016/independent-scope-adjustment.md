# 本地演示失败及拟收窄范围：只读判断

原冻结源码0f0819a6a481841a0221cc69f75959326f264529。原静态/10轻测/包同源报告仍仅证明那些有限范围；不能据此签收完整prepare演示。根实际wheel完整演示失败应作为单独FAIL保留，不能回写原报告为完整通过。

只读核验/workspace/local-candidate-clean-install/failed-pa-run-readonly.json：P-A per-use Run run_be5e46f6c8794042bc18f2f9ca7ea6a7保持RUNNING，error null，fence1，一次CLAIMED；仅一个resource.read VERIFIED、runtime Attempt0。没有事务时序或异常证据足以确定为P-A动态重绑定根因，亦不能将它认定为旧F9同因。未重放或恢复该Run，未启动新fixture。

拟将工程演示收窄为“P-A生成并保存→使用生成时原材料+原Goal，由原实例input={}直接提交真实AppRun→从成功成果提取P-B→第三份材料+Goal逐次P-B使用”是合理的最小演示范围调整，不涉及产品权限/预算/lease修复；生成3+direct P-A1+P-B1仍5固定mock响应。必须通过原API、原候选确认与Release/instance/Run合同、原Worker一次claim，结果及同Run人工验收仍真实持久保存，不预填成果或绕过版本/权限。

通过后的准确说法是“收窄演示链在新冻结源和新目录实际通过”；不得称0f原完整演示已通过，不得把新演示计为P-A新材料per-use再验证，亦不得宣称已解决本次RUNNING超lease或旧锁问题。原失败目录、日志和只读proof完整保留。新源码、包、测试与新完整链需另记录SHA/hash，不沿用0f的zip/wheelhash。

把无关CSV演示放到单独明确项目可以减少夹具耦合，P-A/P-B仍在同一专属自然项目顺序使用；这不是产品隔离修复或授权扩展。保持原300秒Run/30秒lease，不增加等待预算、不加Worker循环/重试、不重放原失败Run、不造新executor/Grant。不需要通过无关锁矩阵或真实模型来证明这个限定工程演示。
