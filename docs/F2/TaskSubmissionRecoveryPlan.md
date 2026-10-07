# 普通任务提交回执恢复：本地产品切片（2026-10-07）

基线d3d4fa58fda9e339d6842b7d13aee5f9a5022d37，独立dev/task-submit-recovery-local；不含未发布activation68443。原V5产品§5持久接受、§6.4关闭/断线恢复要求接受Run继续且不盲目重复。本页面普通run-form每次提交创建新key，回执丢失后再点会重复创建，且迟到成功会抢当前项目/任务选择。

实现：页面内冻结project/identity/goal/resource_refs/request_key；单一进行中/未决提交禁用新提交，明确“未确认”而非成功/失败；用户手动恢复同一POST/key/body，服务端既有幂等与当前权限校验负责拒绝重复/撤权。跨项目和任务重选隔离；迟到回执不抢画布。HTTP明确拒绝可重新提交修正输入，网络/5xx/响应异常保留原键。已收到run_id后的只读刷新失败单列“已接受，读取失败”，恢复仅GET，不重新POST。不开自动发送/模型重试，不增加表/DDL/Grant/认证或保存到浏览器磁盘。

验收：真实HTTP接受后丢回执→原键恢复只有1Run；双击；冻结输入；切换项目及选择历史时迟到成功/失败；403/409等显式拒绝与5xx未知区分；accepted后读失败只能GET；刷新后无原内存快照明确提示查历史，不虚称跨页恢复。测试与实际受保护浏览器尝试单列；若现有Linux浏览器权限拒绝保留失败，不能no-sandbox/改系统。Mock演示与PARTIAL/语义NOT_RUN诚实标注，不签收完整PB/F1/Win11。该产品切片0模型/0凭据/不push/CI；另一个工作副本随后单独获批的新真实窗口及实测不并入此口径。

最终：实际HTTP/DOM24项、6持久Run/2MOCK Attempt，专项1PASS与相关47PASS；受保护Chromium实际启动BLOCKED（SUID所有者），无PNG/像素验收，PG/Windows未测。详见[证据](../evidence/task-submission-recovery-20261007/README.md)。本地提交，不push/CI。
