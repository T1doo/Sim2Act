# 已保存目标到普通任务：工程切片日志

2026-10-07。计划先提交 a1e2a12，基线 eb79cb5；产品初版364caa0，来源/恢复修正d85bc12，中间冻结cf0ac19，最终执行冻结 **02ddcebf937e4264ac60c8b7da60455a5e2c6eab**。工作副本 `/workspace/Sim2Act-bounded-product-candidate`，普通开发分支交付到既有 `dev/f1-foundation`。初始 main/work 与旧断开任务文件未改写。

本轮补的是实际生产接口与正常 worker 接线：目标卡保存的精确版本及完整条件直接形成普通持久任务，不再要求用户重新输入目标。POST仅接受 expected_version、expected_fingerprint、request_key；同一事务校验项目、历史、当前材料及原请求键。冻结契约保留全部已知/假设/未决/硬条件/验收项和材料快照；原始接受事件同时绑定来源ID、版本、指纹和完整输入指纹。正常只读 worker 把完整目标送入请求，恢复时核验原始完整条件，只开放读取和CSV汇总；原授权、预算、fencing、实际工具回执保持。结果仍是 PARTIAL、目标语义 NOT_RUN，不是成功应用来源。

页面新增“按已保存 vX 执行任务”，明确未保存编辑不参与执行。未知接受只能原键恢复；已接受详情读取失败只GET。项目/身份/目标卡切换及ABA迟到响应不能选中旧Run。冷页普通任务历史可定位原任务。未新增表、DDL、Principal或Grant，未激活任何模型或外部发布。

## 实际验证与保留失败

- 最初后端开发12 PASS2.84s，仅开发证据。
- 初版对应90项开发运行88 PASS1 SKIP1 FAIL14.70s：测试worker空JSON请求体被现有安全检查拒绝。冻结通知与UI修改时序重叠，因此该次是**混合源码**，不能归为364caa0冻结通过。
- 364caa0独审静态BLOCK保留。来源接受锚、恢复完整目标及锁序问题修复。原报告“页面缺项目守卫”判断不准确：初版已检查project_id，实际缺的是card.id；原报告不改写，后续独审加更正。
- d85bc12冻结实际96前的95项：92 PASS1 SKIP2 FAIL21.21s。来源字段删除后GET漏查原标记是产品缺陷；HTTP夹具错误期待“合计”，真实文字整理目标只返回resource.read。修正回读守卫和实际内容/VERIFIED回执oracle，保留原件。
- 中间cf0ac19：**实际唯一收集96，95 PASS1 PG角色SKIP0 FAIL15.72s**，逐用例JUnit与collection多重集合一致。当时新增18后端用例含完整输入、原键恢复、跨项目/主体、权限/来源/版本篡改、双标记删除、原接受锚、恢复条件及未开放写工具拒绝。相关旧目标卡/候选/普通任务/契约用例保留。
- cf0ac19独立16实际oracle中13通过、3缺陷确认：接受事件版本true与1相等、恢复版本true与1相等、重复constraints键被宽松JSON解析掩盖。完整authority前后相等不代表来源通过。原独审失败及probe保留；02ddceb改精确指纹比较与strict_json解析（重复键/非有限数/深度拒绝），不新增任意输入长度上限。
- **最终02ddceb实际唯一收集101，100 PASS1 PG角色SKIP0 FAIL15.09s**；逐用例多重集合匹配，23新增后端用例含事件/恢复bool、float及重复键；未再次运行full/PG/CI。
- 最终产品完整DOM受控27检查通过；另7检查用真实loopback HTTP/API与正常默认MOCK Worker，读到真实授权CSV文本、VERIFIED读取回执、PARTIAL/NOT_RUN及冷页原Run历史。HTTP原始测试确实断言1Run、完整排序Principal/Grant行与运行前相等；数据库行 **NOT_EXPORTED**。实际加载app.js哈希与冻结源码相等；加载哈希导出范围仅app.js，不声称完整资产逐项导出。
- Ruff、mypy43源文件、JS语法、源码diff检查通过。253个tracked src/tests/scripts/.github执行文件对照git冻结字节并在执行后核对；无单独执行前manifest回执。

[原始结果、源码哈希和失败记录](../evidence/saved-goal-run-20261007/README.md)。最终独立19实际SQLite/ASGI/defaultWorker场景全部PASS；正常/旧契约4路径共8次实际MOCK调用、0LIVE，篡改及撤权/材料变化场景0发送，完整authority前后指纹相等，GET逐次全表无写。独审执行的是自己从02ddceb导出的不可变源码，模块路径/7关键文件哈希另存。UI/原生/PG并发独审NOT_RUN；锁序只静态核查，不能提升为真实PG并发通过。原cf0ac19的16场景/3缺陷记录原样保留。

## 与真正P-A/P-B和R0的差距

手动CSV路径仍是固定csv.sum模板；planning.py尚无真实自然语言目标→模型选择ActionSpec/AppManifest。Report来源/核查/提取/冷运行已有工程接口，但production provider路径仍有test_only/MockTransport守卫，全球LIVE预算0；不能宣称“只差一次LIVE测试”，不能擅自移除守卫或加预算。本轮全目标快照进入普通worker是一个可运行前置，MOCK不证明任务语义正确或规划成立。

R0空环境安装、身份建立、正常API/独立worker启动、原生浏览器、Win11、AT02、F1/owner签收、真实NL P-A和完整P-B均未因此完成。当前没有提出LIVE请求：需先限定生产planner/provider接口及返回结构、持久预算与权限，再单独申请精确模型/次数/数据范围/通过门/清理计划。历史完整7854及独立R0Doctor6bbe证据仍各自绑定原源码，本次不是它们的新全量。

[Windows900阶段账本与覆盖保留优化方案](WindowsFinalBudgetAssessment.md)仍NO_GO。本轮不重跑full/PG/CI，不提高900/240/150，不减少断言，不修改凭据或系统安全。最终使用普通push、[skip ci]，不合main、不部署。

独审最终报告：[限定PASS原件](../evidence/saved-goal-run-20261007/independent-final/final-review.json)，SHA b89565b1b285f336472ce55db1155d50472288fdd29a2b058320b3ac3b203c1b。21独审文件哈希与7源码哈希实际匹配；37自有fixture DB已删除。GET全表无写断言实际通过，但原数值digest NOT_RECORDED。四原始失败log/XML中的28行traceback尾空格按原字节保留并核查，其余源码/作者文档无空白例外。
