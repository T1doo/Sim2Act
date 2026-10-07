# 精确8c106组合全集：SQLite通过 / PG真实失败

唯一冻结 `8c106e9ba7e12d298a5ac3ff5c7d7409e16aa4a7`，238追踪src/tests/scripts/.github文件SHA逐字一致；六实际隔离venv/current/clean-child导入包含DeliveryGraph及apps均本树（origins.json）。collection实际1283项/0.45秒，比准备1261增加22，比先前native1046增加237；绝不相加旧成绩。父明确GO后唯一SQLite→PG串行执行，两phase各完整-ra、durations30、JUnit、独立venv/tmp/controller；原90秒/guard/49检查/14POST均未改。

- SQLite自然exit0：1241 PASS / 42 SKIP / 2 warnings，698.42秒。
- 然后唯一PG自然exit1：1278 PASS / 4 SKIP / 1 FAIL / 3 warnings，1407.99秒。
- 两phase每套均1283全集，真实skip理由完整日志/JUnit/full-summary保存。没有自动重试或selected代替full。

PG失败是 `test_report_manifest_real_http_dom` 实际Node subprocess90秒 TimeoutExpired，stdout/stderr空。安全driver-progress完整817行；check40“real project onchange ABA cannot restore late protected history”发生86007ms，最后health GET373在88985ms状态200，resources GET374在88986ms启动未收到结束。22个request-start fault_target全保留，最后hold-history/idx355/84645ms。没有results.json/driver-failure.json/driver.log；JS加载hash exporter未达到，因此实际loaded hash NOT_RECORDED，源静态hash不能替代这个事实。补充5个local sidecar观察6 RECEIVED/0 STARTED（source2/extract1/cold3），最终预期7Mock/49check未达到；旁账不代替实际DB回执，fixture正常drop后没有重建Run/Attempt。详见report-ui-timeout-diagnosis.json。失败原因保持UNKNOWN，不能套用旧e4超时或3de fault竞争诊断，也不能把SQLite49check通过当PG通过。

PG新Graph最小业务CRUD角色case实际PASS0.942秒，新ReportManifest preview角色case实际PASS4.385秒；role匹配共21项均实际PASS，包括protocol/sharedbudgetCRUD。完整角色case状态见full-summary，SQLite条件skip不作为角色通过证明。

清理实际完成：15:52:43UTC自有schema/role/publictable/controllerchildren0；精确selflabel容器删除/剩余0，privateDSN/rawPGlog/JUnit及两自有fixturetmp已删除。只影响本次owner资源，其他owner小测试、共享venv/DB均不碰。镜像postgres17.11本环境首次拉取后建立唯一DB，未泄DSN。无源改变/新Grant/真实身份/LIVE/push/CI。原1104/e4失败与3de诊断保留在旧树，不重复作本版证明；此次总体FAILED，不构成发布验收。WindowsCI仍NO_GO，本Linux耗时不构成Windows总预算资格。
