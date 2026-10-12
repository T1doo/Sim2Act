# 候选4独立复验：旧任务目录读取仍阻断合同

日期2026-10-12，独审`/root/text_logic_review`。基线`e2b856bb453fc74452583fa10843148758e2d9b9`、分支`dev/pb-text-logic-reuse-20261012`上的未提交候选4。冻结清单`candidate4-freeze.json`所列378个src/tests文件在两轮执行前后全部匹配，零缺失/零变化。指纹检查、完整命令、退出码、原始log/XML及逐项summary均保留在本目录。

主要新目标37项：**34 PASS、3 FAIL、exit1**。含两个作者新文件的28项和原独立API补充9项；三个FAIL全部是普通可见冷页面，不能签新合同通过。原始三个单边JSON类型污染红例及其余六项独立负例在本候选均PASS。

相关目录/条件App回归原执行22项：21 PASS、1 FAIL；其中两个socket UI文件超出进一步明确的本轮范围，不计有效验收，详见范围记录。扣除这两个文件，合规的普通API/无socket DOM相关回归20 PASS。

## 当前真实缺陷

1. **冷页面普通任务目录SELECT旧私有字段。** `refresh()`仍GET`/api/projects/{pid}/runs`；候选4`api.py:277`的list_runs SELECT `runs.goal`及`run_contracts.snapshot`。真实全段SQLite PrivateReadBarrier保护原成功AppRun和原生成Run的这些字段，三个UI场景`valid`、`authorization-lost`、`binding-lost`均在普通冷boot触发真实旧私有单元读取后报OperationalError。

   原错误完整保留在`new-and-independent.log`和XML，包括实际SQL：`SELECT private_read_runs.id,status,created_at,goal,request_key,private_read_run_contracts.snapshot ... WHERE project_id=? AND principal_id=?`。这是应用读取被测试屏障检出的失败，不是工具/平台授权拒绝。

   最小修复：新增普通Run目录metadata模式供冷页面使用，仅id/status/created_at与安全请求身份元数据；goal_summary采用标准无旧内容占位，不能读取旧goal、contract.snapshot再脱敏，mode无法仅凭当前安全元数据判断时用UNKNOWN。默认既有目录API兼容保留，显式打开仍完整权限/来源核验。

2. **只撤权、保留原resource时的hash目录缺口（静态）。** list_resources先整项目SELECT id/name/format/hash，再逐行authorize。原resource未删除时，即使最终隐藏该行，hash已被读。本合同规定授权后不再SELECT原resource内容/hash；当前新主例先删除resource，所以无法检测这条保留row路径。

   建议在同项目锁内先筛当前user+项目runtime的有效read授权resource IDs，然后仅对这些IDs投影hash并复核授权；或提供不取hash的metadata目录、显式授权再读。下一候选只需增加一个保留原row但撤权的普通目录/SQL屏障用例，覆盖既有数据权限目标；本审查没有为它启动额外候选4probe。

## 已修复并实际通过

- `text_logic_reuse.load`的canonical/public及独立sealed原payload比较已经使用fingerprint；pair、body与candidate相关JSON比较也改为规范指纹。原三个单边污染用例（0→false、false→0、64→64.0；仅重签primary row、两seal不改）均实际返回409，原始独立测试9/9通过。
- `/api/apps?metadata_only=true`只读app id/name/project/runtime及Grant metadata，生成仅供发现的CSV hint；没有旧candidate SELECT。条件报告新metadata目录依据独立kind先选ID，仅返回summary；默认目录保留旧兼容行为，打开仍load来源。这两处原候选3缺陷已静态修复，但三个完整冷页面仍在下一普通Run目录失败，因此不能声称完整页面通过。
- 新普通API/Worker用例、预算精确拒绝、真实64th写成功/65th拒绝且原key可读、typed最终写中expiry回滚及新身份/双seal闭集均在本轮通过。它们不替代完整冷boot失败。
- 合规相关回归20项覆盖默认catalog API兼容、use.js发现/显式打开（24个合成DOM检查）的原边界、条件App普通真实API行为。只确认这些实际节点，不代签完整平台与语义。

## 额外相关测试的范围记录

我此前把“必要CSV实例/条件App UI回归”解释为可执行其既有本地HTTP线程服务器测试，选入`test_application_use.py`和`test_conditional_apps_ui.py`。它们均含`sock.bind`。收到root进一步明确“仅进程内TestClient/IPC、不得bind socket”的消息时，两轮测试已经全部结束。

这属于本审查的范围判断错误：原实际结果必须保留，不能改写成NOT_RUN。`test_application_use_actual_http`实际PASS；`test_named_report_draft_real_http_dom`实际FAIL，错误为关闭JSDOM后的旧异步回调`document`undefined（完整driver.log/XML保留）。两项分类`OUT_OF_SCOPE_EXECUTED_NO_ACCEPTANCE`，从本轮有效验收计数排除。没有重试、换方法、改URL或调整工具绕过。

条件报告UI的hold-list hook静态仍使用`path.endsWith('/conditional-apps')`，新metadata query使其不匹配；如后续另行获准运行该历史测试，需按URL pathname更新拦截器并保留原等待/ABA断言。本轮不再执行它，不以它的socket运行证明新目标页面。

## 执行完整性与边界

`new-and-independent-result.json`：37项、exit1，134.36秒。`catalog-related-result.json`：原22项、exit1，49.03秒。均显式去掉SIM2ACT_TEST_DATABASE_URL，使用本次/tmp隔离SQLite；真实/付费模型0，Node为既有JSDOM。每轮1个既有Starlette/httpx deprecation warning，未安装或改变依赖。

全部独审测试/Node/runner已结束，已明确向root解除src/tests编辑等待；没有继续启动候选4测试。独审只写自己的/tmp，没有修改产品/作者tests、push、部署、凭据或网络权限配置。所有已运行失败和scope错误记录保留。

候选4结论：需要修复并重新冻结。原已取消精确候选安装竞态对照永久NOT_VERIFIED；本轮没有执行、实现或变通该目标，也不以API/Worker通过关闭它。native browser、真实模型/付费、PG/应用角色、Windows、真实设备崩溃、全旧源码升级、完整P-A/P-B/AT-10、人工语义/owner、正式发布/部署与远端CI保持NOT_RUN。owner PENDING、semantic UNKNOWN、LIVE0、formal publication false不变。
