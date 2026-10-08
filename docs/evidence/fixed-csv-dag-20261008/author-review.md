# Author review and contract boundary

作者复核，不是第二独立 reviewer 签收。父线程传回的独审只覆盖 f40d975 的 slash/NUL 键处理，不能用于签收 DAG。

核对原 V5 固定注册动作、有限类型化 DAG、严格全图 preflight、权限交集、持久 Run/intent/fencing、来源变化失效与工程验收标签要求。本实现只固定 preview/aggregate/report 三步；纯报告必须精确输入/输出 schema、read/read_only、空权限/依赖/委托工具、receipt.readback.v1。原权限校验不绕过，纯投影不需要额外授权，也不能成为模型工具。没有循环、任意解释器、客户端执行定义、新表、Grant、Release、artifact 或业务对象覆盖。

Run 接受事件、原计划双行 seal、RunContract、身份、来源 hash、候选/图版本、全源码注册指纹在派发及读取时重新绑定；步骤只从已验证前缀恢复。PREPARED、intent、本地结果、回执和计数原子提交。每步入口与提交前检查租约/fence/时限，旧 worker 无法提交；暂停/取消按既有状态在提交边界结算。冷恢复重算来源、实际聚合和纯报告，比对完整回执及最终结果；协调修改合计及其签名仍不能替换实际 CSV。OUTCOME_UNKNOWN 不派发、不 resume，既有 generic reconcile 不得替换固定证明。

页面复用原交付图上下文/项目/身份/epoch，原键/列/指纹被冻结，接受响应未知时只恢复同键；精确版本显式确认，先读持久回执再展示。来源/授权/版本或客户端指纹核验失败清屏，停止控制只读 NOT_VALIDATED 元数据。冷历史读取不自动 POST；页面 re-open、项目 ABA 延迟响应、篡改最终结果、撤权均由实际 HTTP/DOM 覆盖。DOM 导航夹具关闭定时刷新，不能冒认后台 polling 或原生 Edge 验证。

域保持探针通过原 API 创建/执行，逐表比较完整行：计划40表、接受37表、执行36表保持；例外只为既有交付请求、Run/RunContract、operation/intent、event、Worker.once heartbeat。第一次探针误将必要 heartbeat 算为禁止变化，其失败日志保留；修正允许集合后双后端通过，不更改产品源码或业务写计数。

保留原断言/旧测试与脚本、Windows900 / Edge240 / Node150 约束及依赖锁。Ruff 全 src/scripts/tests 与 mypy50源码文件通过。当前冻结结果只证明指定工程范围；独审 DAG、原生 Windows/Edge、真实任务 gold、完整 P-B、人工验收与正式发布未完成。LIVE=0，未运行真实模型或新CI。
