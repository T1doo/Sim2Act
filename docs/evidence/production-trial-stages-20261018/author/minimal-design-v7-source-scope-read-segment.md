# 原完整生成scope证明的同段复用（资格未通过）

run7原gen3+Source2实际完成Source SUCCEEDED；Cold首NS actual Core Attempt/PA请求已存，尚未进adapter即失败。实际adapter5、journal最终仍5slots；后一点只能说明Cold预留未提交，也可能CAS后fresh失败回滚，不能唯一断言异常语句。精确case577.207s/pytest577.99s/外582.940079368s保全。checkpoint源码8fd已普通推送，不代表功能PASS。

Cold私有stage_current只读cProfile7.436963s/5324SQL，source_scope_gate79/77次约4.165s；严格过期原check_run6.902280s仍VERSION_CONFLICT，未伪造lease。两者闭合run7 DB SHA70eb1f…前后相同，无模型/恢复。新热点优化只在原SourceReads、same Store/c/driverTx/thread/epoch内，首完整source_scope_gate原body逐字保留并必须True；只actual3 JOURNAL markers+自然generation双锚+无LIVE approval_id，False/legacy/NS不缓存。marker只是选择优化，不提供权限/完整业务证明。

缓存前要求原完整proof收集了相应READ与SAVE authorities。命中先fresh精确Run owner/project/runtime/own_project及全部原authority reauthorize，之后两次重读原Run refs、contract fingerprint/全部generation标量hints、全部ACCEPTED行数/id/锚、实际3 marker。每处与首次完全相等，最终还核same exact source read token/driver/Tx/thread/epoch；inflight拒未完成递归、异常clear、第一写即原hook清除，不能跨CAS/事务/Run继承。

曾在命中前后各做一遍相同reauthorize；该WIPprofile源SHA46aaff…结果10.212086s/3867SQL，SQL减少但墙钟未加速，原件保留，不据此承诺性能。最终收敛为锚前一次完整reauthorize，随后锚之间只读且最终epoch复核；没有省权限，Grant时间仍实际authorize。原journal CAS后fresh、lease30/Run300/stop/版本/材料/完整Goal都不改。

B仍1node，增加2个精确必要权限窗口：实际观察fullscope1次/真实cache hit发生authority recheck；SQL revoke后epoch清除使原fullscope再入并GRANT_REVOKED；另将对应runtime READ所有grant设置未来2秒、prime后真实时钟到期，无写/同epoch命中也GRANT_REVOKED，fullscope仍1。拒绝窗口55表严格相等，seed和rollback在窗口外，恢复全部baseline；不新造产品Grant、不扩故障矩阵。

session guard仅被动调用并返回原check_run和journal._apply_in_transaction，记录实际时长及异常类型/栈文件名行号，不改clock/门/返回/错误，不记录headers或凭据。下一fresh8组仍原4nodes，真实模型0；旧所有失败保持，不重复旧19/12/8/9。
