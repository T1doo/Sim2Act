# F2-T07：已有非CSV Report 图的人工编辑保护

基线 afb2f1f3813fc3a4744923f31bbcb4666b88cccd，独立候选
dev/report-edit-locks-20261009。V5§9.3(6)与原F2-T07要求影响集遇人工锁返回
LOCK_CONFLICT并保留内容；原 ManualEditLockIntegrationLog 指出非CSV/PROJECT
仍开放。当前公开manual-locks及页面只支持data.aggregate_csv，但已实现的
bounded-report-manifest拥有稳定图和decision→explanation局部修改，缺少同一人工
保护入口。本轮补现有Report族入口，不新建模板、工具、表达式或展示功能。

只接受既有load_family完整验证的bounded_report/intern.conditional_report及原CSV，
仍自己的项目/当前候选/源Run和原始材料证明、交集Grant与源码/依赖版本。使用原
manual-edit-lock.v1、图/节点/锁修订CAS、明确确认、原键恢复与不可变seal；可选择
已有Report图节点，不能创建任意节点或内容，锁改变后需显式重派生。锁定VIEW使
原展示影响计划/草案返回LOCK_CONFLICT；解锁并新派生/新计划后原有限展示检查
可以读取实际已归档Report输出。只改保护入口，不改canonical/Run/旧检查成功。

没有新增API、表、身份、Grant、权限/预算、模型请求、业务写入或发布。PROJECT
扩验仍PENDING/BLOCKED_PARTIAL，归档合成输出不转真实材料或语义/owner验收。
保留PG resources-history/全量及探索超时OPEN、HTTP200损坏响应提示限制、
Windows900/Edge240/Node150未验收，原等待上限不变，LIVE=0。

严格正反例需覆盖实际锁→重派生→原Report修改拒绝/无写入→解锁→新精确计划与
归档输出有限检查，旧图/CAS/请求键/确认/类型/跨用户项目/源撤权篡改/锁或seal
篡改/同连接竞争，冷Store及原键恢复不复用过期锚；保留原CSV兼容。双后端独立隔离
实际HTTP/jsdom页面与必要原锁/Report回归及旧源码升级，独立审查另写用例精确
冻结，旧源码须对新增Report入口预期拒绝。本候选普通push供审，不合dev/main。

最终修复另覆盖真实已接受计划丢回复、同项目peer加锁/重派生、原键重试返回
LOCK_CONFLICT仍保留UNKNOWN，peer解锁后的版本变化也不能静默换键。仅首次
明确拒绝且没有任何先前未确认接受的规划才释放未发送的展示意图，允许解锁后新
精确规划；定义已发送、形状损坏、上下文离开或旧闭包都不能清除原恢复意图。
