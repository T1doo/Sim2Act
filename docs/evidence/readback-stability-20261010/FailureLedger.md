# 失败与未覆盖记录

- 历史807 Report GET idle6与42b resources-history Future10：原证据在已有目录保留。本轮各一次基线通过；未稳定重现，也未取得原慢读时CPU/wait-state/请求时间线，不关闭OPEN，不认定重复scope是原根因。
- 作者初轮SQLite probe：4节点，3PASS/1FAIL。失败是新反例夹具误用`requests.c.id`不存在字段（delivery_graph_requests实际使用复合主键）；产品及原页面/API正确通过。只改为真实composite key定位，随后473最终集合覆盖2新反例。原probe日志/JUnit/压缩profile保全，不把失败当成最终绿结果。
- 作者最终首次SQLite/PG：节点命令拼写错误，collection-only exit4，各自无测试执行；修正为现有`test_joint_pair_marker_and_join_deletion_cannot_hide_actual_accepted_event`后另保存最终完整集合。原collection-error command/run/log/JUnit保留。没有产品修改或放宽时限。
- 独审初轮3个coherent forge反例：冷GET均正确409；自编写入脚本使用新的合法check key却错误要求拒绝。现有合同允许合法201。更正为受损existing key/原body精确重放，均409零写。初轮与修正脚本、原日志、实际HTTP request.content全保留在独审白名单；不新增全历史无损的写入前置门，不增加unique通过数。
- 5427原Windows CI：72项Ruff style/import violation，Setup/smoke成功，JUnit未产生、Edge SKIP。754仅样式/导入顺序改正；完整Ruff/mypy新run实际通过。
- 754新Windows CI run38024430136/job114132123197：工程step cancelled，run cancelled；原15min上限附近中断，JUnit属性863 tests/26 failures/38 skipped/0 errors/time823.158，未完成全量。26失败的节点/断言未在原日志中输出，JUnit没有上传artifact；NOT_RECORDED，不把它们说成已知产品回归，也不说CI绿。Edge SKIP、Report/Cleanup成功。原完整log私下保留，`ci-754-verification.json`记录原SHA256与公开原文摘录。没有代理取消或盲目rerun，没有改CI/900/240/150预算。新native工程失败与未完成为OPEN。后续job公开annotation已确认超15m0s上限；26个F全部早于取消，不能把它们当作取消伪造的失败。artifact API为空、754仅run1/attempt1；26节点/产品vs测试装置归因仍NOT_RECORDED。正常push自动后续run38025760656核验时in_progress，不称PASS，下一轮优先26项失败。
- 只读能力失败：gh API读取原run返回Forbidden；安装GitHub只读工具可取实际run/jobs/rawlog，但额外actions/jobs与check-suite/check-runs endpoint返回INVALID_ARGUMENT。不能因此捏造26失败详情或精确取消原因；已用可读原日志与实际API记录结论。
- SQLite 5 SKIP：1 PostgreSQL business-role test、4 PostgreSQL resources/graph锁顺序test；由最终PG集合实际覆盖。native/真实Edge/像素/真实模型/P-A/P-B/R0未在本轮Linux作者或独审执行。原生budget验收仍缺失。

独立通过只签473的局部history语义复用；作者双库/升级证据单列。PROJECT PENDING/BLOCKED_PARTIAL，LIVE=0，整体NOT_ACCEPTED。

- 开发普通push首次exit128：Git无法读取HTTPS用户名；原dev-push.log保全。默认配置重试1次成功754→6eb42aa，未读/写凭据、未更改Git配置或安全网络。原失败与成功日志在ci-followup分开保存。公开annotation API直连默认网络403，但GitHub公开job页面只读成功取得取消原因；不是工具修改或代理绕过。
