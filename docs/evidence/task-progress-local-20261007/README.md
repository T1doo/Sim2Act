# 普通任务只读步骤与等待原因：独立本地切片

基于冻结CI源00a469693144c657192506b52c3de24bdc06d135，分支dev/task-progress-local，仅app.js和测试/docs变化，不混入CI37574285701。真实模型0、不push、不追加CI。

普通任务成果画布追加最近20条已记录步骤与持久时间：接受、领取、模型尝试登记、工具核验、技术状态、人工控制/核对。尝试登记明确不表示发送或成功；技术状态、已核验效果与尚未实现的目标验收NOT_RUN分开。未知尝试/工具效果不重复发送，待资源、撤权、额度、失联待核对分别给出有限原因；没有原因时保持未知，不虚构故障。VERIFIED与EFFECT_KNOWN_INVALID计数分开。

仅使用已有授权inspect/unresolved-attempts回读结果，没有API/表/权限/worker/模式变更，没有自动操作或新增fetch。新摘要按固定事件名/状态白名单展示，不复制任意event.data或模型文本；完整原授权回执详情保留。既有身份/项目/选择代次守卫不变；内部AppRun与协议入口继续走其原展示。

15项投影专项中真实API接受→normal Mock Worker→PARTIAL、2MOCK Attempt/1VERIFIED构成正例；等待/未知/格式攻击为明确合成展示负例，不伪称真实外部限流/故障。原真实HTTP/DOM恢复/历史组合扩为41项（2新增进度项），仍7个刻意意图/7Run、2MOCK Attempt；独立夹具不混算预算。专项2PASS/1browserDESELECT/1warning（4.87秒），相关53PASS/1PG-roleSKIP/2browserDESELECT/1warning（50.88秒）；独立2PASS/1browserDESELECT，Ruff/Node/mypy34/diff PASS。

失败历史保留：v2 driver strict eval 未把helper暴露为window函数，TypeError失败；改为实际script元素加载，与真实入口一致，产品代码没有为测试改全局契约。v1旧组合只验证39项，最终41项在real-http-results.json，不替代/重写原历史。PG/原生浏览器/像素本切片NOT_RUN，不借当前冻结CI的Edge验收提升。完整P-B/F1/AT02/Win11/正式Release仍开放。

下一有界工作：让普通任务回读/授权拒绝明确清空旧画布并区分“读取失败”与任务技术失败，随后把此只读进度切片接入既有原生验收；不自动续跑或发真实模型。
