# 30秒大型Cold：生命周期边界和最小完整架构

当前实际候选源码2ad3227621b48793a4d03747463b33207139147e；基线2d41ad38b84630cb817d87374122bce31e357d0d，已保全证据b5c3f898a352d100b890f7b243b17bcc39c9ae34和可安装ZIP不覆盖。本轮只实做更早state截止适用于已签署120秒结算，**未启用数据计划或任何加速／缓存PASS**。这是基于源码和真实反例的最小结构方案，下面未实现的部分明确列出。

## 当前阶段及不能后移一行的原因

Worker.once先claim并持有30秒owner/fence；advance_model只有在真实/固定Mock响应接收、Attempt RECEIVED及完整请求/原响应archive持久后，才得到完整G0的输入。完整G0包括本次aid/response/wire/meta/intent/当前owner和版本，因此不能整体移到claim之前。静态定义的expand/compile可前置，但此前诊断单G1约0.059秒纯编译，不足解决几十秒的大头；_prepare约11秒包含DB、授权、完整lineage，不能整段称纯计算。

当前普通结算original_interval沿真实已提交heartbeat的原lease、Run、node和state最早截止，并从续租前绑定保守monotonic；显式SQLiteSettlementCaps才可预约一次最多120秒，旧caps不会升级。该120覆盖G0、FIFO等待、五写、G1及commit；writer admission/首次DML另有最多30秒，不能把G0<30或G1<30叫完整旧合同恢复。

新真实SQLite反例两条：在G0读后，另一连接真实store.heartbeat成功只更新lease，旧快照随后升级并写入触发SnapshotChanged、完整回滚；在同G0连接执行续租UPDATE，则在promote之前被只读mutation门拒绝。不是换一个计时起点就能保留原Graph。关闭事务后把旧Graph／frontier／Binding／authority搬到新事务也违反现有driver/transaction/nonce/epoch约束，仍不得采用。

## 最小有意义的数据计划（尚未接入）

1. 响应archive已持久后，在独立、只读准备事务收集**整个Terminal Source与Generate事实族**的完整原始输入。仍在原Run/node总期限及正常30秒heartbeat策略内完成准备；准备事务不升级写，不能持有旧Graph去续接。输出仅深度自有不可变数据／纯计算结果，不携本轮授权、PASS、SourceBinding、Graph、Connection、角色或租约结论。完整原始数据中的历史状态字段仍须保留，但不作为现时许可。
2. 事实闭包必须包括所有Source/Generate Run、合同、请求原wire与响应原bytes、完整Attempt/Reservation/Operation/Intent/Event/Journal成员集及负查询、顺序/类型/别名、静态definition/recipe/schema、源材料和全部外部文件/代码输入。仅记录用到的id或终态SQL端点不够。生产口至**该族所有消费者**都迁移后才可停止重复纯重建；半新半旧再重复全图pin不构成提速。
3. 关闭准备事务，原普通heartbeat在旧owner尚有效且最早截止未到时真实提交；开启新G0事务和新Graph。重新完整核授权／撤权／退休、owner/fence/version/Run、当前limits/stop、epoch和双时钟；逐依赖fresh全量比对当前原始输入和成员集。变化直接有界拒绝，不自动换键／重试到通过，不把旧authorization当数据比较的替代。
4. 只有固定纯callee、完整参数/输入、未知类型/serializer、回调和数据库查询环境都证明行为等价时，才可消费准备的纯计算值；外来回调、schema/trigger/UDF或无法证明原SQL结果序列时走完整原路径或明确失败。不能仅看值相同、hash相同或终点相同而忽略中途callback/alias变更。
5. 五写保持同一原子事务。**还必须**为W5→G1闭合精确预期postimage／全依赖和实际写集的等价证明：rowcounts、新增事件／无额外写、完整postconditions及全部实时授权和期限仍执行。现有expected-post shadow只有DATA_MATCH且reuse固定False，缺Python/文件/回调、SQL环境／事务边界和查询序列，不能直接启用。原G1完整执行时，单移G0仍留历史44–46秒、本轮45.45／49.60秒writer区段，不能承诺旧30秒下完整保存。

这是最小能解决真实大头的工程范围；不是可安全启用的小租约补丁，也没有本轮未使用的新wrapper/backend或更长超时。最小可独立落地的当前修复是下面的截止漏洞，性能边界保留。

## 必须的差分与失效反例

准备后任一源／生成历史字段变更、缺失变新增／范围插入／删除、角色撤回／审批退休／owner/fence/version改变、外部文件／代码／schema变化、查询顺序／duplicate和alias分裂合并、callback中改后还原、跨快照heartbeat、自快照写入续租，以及原30／签120／更早node/state任一到期，都必须拒绝旧计划且不持久W5。验证正常两笔保存／首次新进程重开、实际持锁取消和旧键无重放；性能只用真实时钟、匹配recipe/规模和observer，虚拟业务时钟只能验证逻辑。

## 已实际修复的截止漏洞

当前signed120曾只读state的fatal_heartbeat，忽略更早state.deadline；普通30秒路径已有最早截止，不能据此假定120也已覆盖。三个原SQLite反例确实得到“过期state仍预约”和“callback越过state后仍持久sentinel”（snapshot False/True），0模型。修复在原state锁中捕获deadline，fatal保持原对象优先，缺失/非法值受控拒绝；finite值仅min收紧原cutoff，None/更晚不改变120上限。原booking、双时钟token、实际commit和cleanup自然都沿该min，没有新续租或新预算。修复反例及普通/120/commit/取消原回归各自保存，不称性能修复。

## 产品边界

原普通30秒合同下，大型Cold完整校验／原子保存尚未稳定可用，不能以小CSV或单文本PASS推广。现有UI配置缺失会停止提交，MODEL_EXECUTION_REQUIRED显示待执行，FAILED/WAITING_RESOURCE/RECONCILING/RECEIVED不成为SUCCEEDED；仅完整持久结果通过原核查才可显示可用。没有改usable_product、发布／人工验收或通用语义安全门。正式PG／新Windows／大型live仍未验，未新凭据／费用／CI／电脑执行。新可安装Linux候选仍限已声明环境与流程。
