# 最新WIP修复复核

**两项已发现问题静态闭合；本次有限差异追踪未见新确定P1/P2。** 不是运行PASS或生产资格；目录继续未封存。

- P1：sender的production业务分支使用捕获settings.token与live mode，旧synthetic token/mock门继续保留；不再落入旧必拒绝条件。
- P2：source在原_qualified后重验期限；admission在source证明完成后核context/source最小deadline；terminal在完整phase/history、journal_stage_accounted及末_binding后核原RUNNING lease、合同/Run/source截止和stop。没有续租或增加预算。

mode链已追到GA原live冻结、app_jobs从受验原generation传mode、NS Attempt/events/body owner、journal mode/version、Source实际计账和Cold独立Source证明；新prod不借旧gaapproval，旧MOCK历史不提升。新claim排除原associated入口是保留旧资格边界，不能为了让现有试验Run被新Worker领取而放宽。原key仍只读，captured原Store接收与归档/journal结算同事务保留；来源失效只转DENY，不恢复权限或继续业务成功。

固定resolver仍无来源恒拒、旧_qualified未删除。后续明确patch environment/source/_qualified并用MockTransport的七请求链能检验软件接线，不是真实来源/PG/LIVE/收费授权；test_only SQLite可进入旧读取段优化，不能代签non-test PG的并发/时间资格。本人没有读取在途测试原件或执行测试。

机器记录、当前观察SHA及限制见[implementation-fix-verification.json](implementation-fix-verification.json)；先前WIP原观察保留，未覆写。仅允许的只读源码/Git diff；没有产品/DB/网络/Git远端/模型动作，旧sealed与私有留出集未触碰。
