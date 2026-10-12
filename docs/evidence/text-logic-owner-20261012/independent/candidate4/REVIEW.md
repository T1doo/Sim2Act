# Candidate4 独立有限审查：执行FAIL，待下一冻结

2026-10-12，`/root/text_logic_review`。分支`dev/text-logic-owner-20261012`，base `233ba9618ba462aad19e1ca16f085cd0d7242632`。root唯一产品/src/tests写入者；本独审只写`/tmp/pb-text-owner-review-20261012`，运行作者新主线及独立普通API探针。没有改产品、作者tests或旧证据，没有push。

**本轮实际42项：31 PASS / 11 FAIL / 0 SKIP，执行FAIL，不签最终软件接受。** root本轮自身33项27P6F与本独审33项24P9F不同，分别保留，不能借作者页面PASS替代独立失败。父作者已通知待全静止后修新增mypy两处None收窄并再次冻结；不能把candidate4测试结果签给未来软件指纹。

## 实际执行与原始产物

| 执行组 | 实际结果 | 原始产物 |
| --- | --- | --- |
| 作者新API/普通Worker/4正常可见页面 | 33项24P9F0S，exit1，190.02秒pytest | `new-mainline.log`、`new-mainline.xml`、`new-mainline-command.json`、`new-mainline-result.json` |
| 独立附加普通API/容量/权限/事务 | 9项7P2F0S，exit1，65.62秒pytest | `independent-api.log`、`independent-api.xml`、`independent-api-command.json`、`independent-api-result.json`、`test_independent_owner.py` |

所有路径均位于本报告目录`/tmp/pb-text-owner-review-20261012/candidate4`。两组独立basetemp下保留SQLite fixture/原page info和result/stderr；页面完整可复制证据在`ui-artifacts/`。汇总为`results-summary.json`。没有启动额外原家族回归、socket/native或任何旧取消case。所有测试/Node进程已结束并已通知父作者，之后不再启动测试。

## 五个作者API失败：末尾断言错误，原FAIL保留

`test_malformed_owned_run_ref_is_controlled_and_worker_fails_closed`的missing_fp/missing_ref/null/extra/bool_version均真实执行到了：历史ref校验抛DomainError、实际NoModel Worker将新Run置FAILED/VERSION_CONFLICT、HTTP读该新Run返回409/VERSION_CONFLICT。随后作者断言整库`internal_instance_data == []`失败，因为fixture本来含已经成功的旧source Beta结果。

这五项仍计FAIL，不能改成PASS。必要修复为保留typed基线、运行后核整库基线未变或严格核该新instance结果0，而不是要求清除旧来源成功历史。当前没有这些五例执行后越权提交新typed的证据。

## 四个正常可见页面：均FAIL，不签完整链

| 场景 | 实际proof | 冷Worker/新实例技术结果 | 已完成检查/动作 | 资产 | SQL语句/受保护求值 |
| --- | --- | --- | --- | --- | --- |
| accept | FAIL，Node exit1 | 1次，1个SUCCEEDED、typed v1 | 5/19 | 1boot，20 HTML/CSS/JS | 4172/0 |
| reject | FAIL，Node exit1 | 2次，2个SUCCEEDED、typed v1/v2 | 24/60 | 1boot，20 HTML/CSS/JS | 13594/0 |
| goal-lost | FAIL，Node exit1 | 2次，2个SUCCEEDED、typed v1/v2 | 26/62 | 1boot，20 HTML/CSS/JS | 13543/0 |
| decision-lost | FAIL，Node exit1 | 1次，1个SUCCEEDED、typed v1 | 5/19 | 1boot，20 HTML/CSS/JS | 4172/0 |

四例均`TypeError: Cannot read properties of null (reading 'status')`，位于driver `runAndPrepare`读取`engineering.run.status`。accept/decision-lost首个新Worker之后失败，reject/goal-lost第二个新Worker之后失败；后二例在失败前已经通过第一次逐项声明、Goal修订STALE及原key不复活检查。只读inspection各fixture新实例AppRun状态为SUCCEEDED，不能把Worker命令once返回true误当任务成功；精确IDs和版本保存在汇总。

父作者对同轮自己的一个null失败解释为后台poll的showInstance→restoreRun仍在途，driver提前读取暂态。下一候选需普通driver等待本次HTTP/IPC完成且选中本次SUCCEEDED详情；不能停止poll/改timers/换执行器或借此进入已取消精确竞态probe。此解释是作者静态诊断，独审没有另开复現动作；四例本轮完整链结论仍FAIL。

每页真实HTTP加载index+app.css+18JS，资产hash由作者test核；原始proof含全部loads。四份stderr分别427/426/426/427 bytes，不为空也没有丢失；Node退出及SQLtrace均保留。屏障本轮覆盖原source私有数据与source/初始target两张native GoalCard snapshot，实际protected_private_evaluations均[]；这只证明已走过部分的0求值，不能冒称四页完整操作链已通过。

## 独立9项：7实际PASS，2探针设置FAIL

实际PASS：

- 通过真实HTTP连续创建64个不可变自有Goal版本，第64次成功；第65次400/BUDGET_EXHAUSTED且全库无部分写；第1原keyGET保留version1回执、当前head仍64，无写入。
- PREPARE后target user撤权：DECIDE403/GRANT_REVOKED、owner账本未写；原source保留撤权下旧private屏障0，metadata CANCEL及原key恢复仍可用且无payload。
- 已DECIDE后fresh runtime target撤权：旧签收STALE，无prepare_current/payload；metadata REVOKE及旧回执恢复可用且无内容泄露，旧private屏障0。
- 两个普通自有Goal version writer对相同head/binding各自明确新意图并发：恰好一201、一409；最终native版本[1,2]、4个双seal行，无部分第三版；第1key读回仍历史version1。
- native更新及两个seal实际INSERT之后注入故障：全部事务回滚，完整库快照等于写前。
- 删除任一主记录或seal：两项GET均409/VERSION_CONFLICT，不追加任何行。

两个执行FAIL均属本独审探针设置错误，承认并保留原始代码/log/XML，不能写成产品FAIL或通过：

1. 预算探针直接将默认64000缩至63000，误标为仍高于cap。实际在Draft budget门返回400/BUDGET_EXHAUSTED，而断言期待409/VERSION_CONFLICT。它不能证明above-cap变化失效，后续必须从较低预算（例如51200）正常mint对象，再在仍覆盖cap的63000 current budget下检验STALE/拒旧DECIDE/新PREPARE。作者同名budget注释也需纠正范围。
2. 单边boolean污染探针误用`delivery_graph_requests.c.id`，该表实际以app_id/principal_id/kind/request_key复合键定位，抛AttributeError。污染UPDATE尚未实际执行，不能宣称该探针证明双seal类型污染拒绝。下一冻结在新的独立文件用复合键修正；本candidate4原文件不重写。

## 源完整性与接受边界

冻结文件`docs/evidence/text-logic-owner-20261012/candidate4-freeze.json` SHA256 `6495ea3acf801c0b298fd68084db1fc4759c01941a5194208b5b4b9584036986`；377个Git deliverable src/tests，5个ignored egg-info显式排除。规范map fp `e6e377fd7f32d552d42b0ab7eb54e7331b1ee85080abc232fc844469759afa28`。两组各自before/after逐文件hash全一致，Git deliverable路径无额外/缺失，所有4份完整校验JSON保留。

本轮SQLite每test隔离、synthetic provider MockTransport初始真实软件链、后续普通NoModel Worker、TestClient进程内HTTP和IPC可见JSDOM；人工选择均SIMULATED，不是实际用户语义签收。技术semantic UNKNOWN、正式发布false、LIVE0。真实人类/语义/正式发布、旧233库升级、PG/Windows/native/付费模型/凭据/部署/main/core/force均NOT_RUN。无工具或平台拒绝；此前取消精确竞态永久NOT_VERIFIED；既往范围误选与UNKNOWN历史不改写。本候选仍有真实红轮，等待修复与新freeze独立重验。
