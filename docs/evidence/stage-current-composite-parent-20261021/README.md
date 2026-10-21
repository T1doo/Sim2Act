# 内层 stage_current 复用已有复合 parent

基线 `e4dddb1c8fd9a67a622e5d69c8637e07a38f8836`。此前原窗口首次commit因最严
lease到期拒绝，end−lease=0.5311813354492188秒，实际未到回执段；该差值不是完整
G0所需总提速。本片不原样重跑，而补上尚未接入已审优化的明确内层调用点。

## 精确产品改动

只把 `natural_live_admission._graph_stage_current._parent_pin` 的原
`_graph_trial_pin → _graph_trial_stage_raw` 两调用，改为现成
`_graph_trial_stage_parent_pin`。该复合入口原先已用于外层run_context/resolver，
本片使它们调用的内层stage_current同样使用；不改既有复合实现或任何其他产品文件。
AST证明替换这个嵌套parent后整个模块与基线相同。默认None/非native旧模式仍由
原helper回退两步，独立入口继续自pin，无PASS缓存/新skip guard/更多根迁移。

所有typed cohort、SQL/授权和外部返回后的guard、stage完整关联、DB读集、txn/
fence/stop/最终期限及回执闭包维持。新产品source SHA256：
`84195d0061f965b8f1cc2e1bc385941c2739e09dce02293596b3025f14b4433a`。

## 必要离线证明

真实隔离SQLite、原 `_graph_stage_current` 两分支；禁止Worker/模型/transport，
不运行完整prepare/commit/G0。仅比较parent旧adapter与新helper，其他代码相同。

| 分支 | 整段codec旧→新 | parent次数 | 每parent旧→新 | family/Run谓词次数 |
| --- | --- | --- | --- | --- |
| Source | 376→226 | 25 | 7→1 | 78 / 51 |
| Cold | 754→526 | 38 | 7→1 | 119 / 39 |

完整family/Run谓词序列、Authority业务指纹和返回job一致；同一完整root集合，
不是跳原SQL或省新鲜读取。真实首次stage读先单独计量exact派生Release pointer
的原graph.add，记录其2次codec；随后两臂root集合固定。初30项28P2F/46.50s
是未区分首次lazy add，整段差比6*parent多2；未放宽断言，原失败日志保留。

冻结广批 **115P/207.52s**，覆盖stage parent/native/receipt/SQLite；源与测试前后
SHA一致。随后依独审只增强4个跨调用mutation/revoke参数反例，把异常断言收窄
第二次，并在scope外核已观察error非None/同一对象，因此首次意外拒绝不能假通过。
产品src始终未变，其他测试函数AST不变；最终4项定向 **4P/7.20s**。

115批测试SHA `a6bcdedb5f92fa69a662fbee2840cb98f10dfcccbfd09468b28233a928d85627`；
4项最终测试SHA `9265b2ea628a34c9a93604e6688c41eada81dd2974845b08f8d13bdaf21a5392`。
不把115声称最终test版本全批实跑，也不相加成119个不同测试。运行中未改源码/
测试。Ruff两文件、mypy源文件通过。既有强制close原fixture异常仍单列，未改
生产清理。源码限定独审及必要测试证据原件见reviews/tests，非G0性能验收。

## 一次原预算窗口

正常开发分支推送、冻结clean HEAD后，只读describe精确摘要。新目录/SQLite/
单次grant，最多6 Mock交换、8入口，prefix480/G0120/总600+清理10，原lease30/
Run300/TTL1800/RPM1/reservation不变。64MiB采样监测非硬配额，logical fuel非
CPU/RSS界。0真实模型/费用/外网业务/新增权限，禁Cold2/W5、无自动重试。
必须包括原receipt、第二commit及scope最终期限；首commit或单次wall<30不能
替代完成证据。实际结果随后归档；不承诺必过或把局部codec收益推广为G0提速。

## 本次实际窗口：更后方原提交前缀拒绝，仍UNKNOWN

执行候选 `a6192df3b5b00cf891792af27ab47890da979ff5`，source/dependency 摘要
`7cbf3a6a12fb6dcdbef1a80dd8e900028ffd78ae645f21b753b32e6e6ee4405c`。相对前窗
manifest仅natural_live_admission与stage_pin测试两文件变化，launcher/guard/observer/
依赖/预算原样。实际父argv为规范绝对解释器/脚本；new grant消费一次，不重试。

| 实测项 | 结果 |
| --- | --- |
| parent/child分类、退出码 | **UNKNOWN / 2** |
| Mock交换/入口/Source delegate | **6 / 8 / 2** |
| 真正进入G0 / route | 是 / **OWNED**，native:issuance |
| 总work wall / G0 wall | **341.85972994199983 / 30.122223297003075秒** |
| 原首次Cold校验commit | **returned=true**，保存11项原deadline |
| 第二commit前缀 | 已进入，在原Store.guard拒绝 |
| 第二commit方法本体 | **未进入**；参数前缀先抛异常 |
| scope返回 / 最终期限 | false / **NOT_PROVEN** |
| 直接错误 | VERSION_CONFLICT: **Stale worker lease** |
| child / parent清理 | THREADS_CLIENTS_CONNECTIONS_CLOSED / OWNED_GROUP_EMPTY |
| 独立进程核实 | 父55992、子56016不存在，56016 PGID为空 |
| finalization_errors | [] |

实际栈 `advance_model:3720 → _cold_commit_prefix:2055 → _commit_guard_prefix:1985
→ lock_live:933 → Store.guard:1134`。**Store.guard该消息共享三个OR条件**：fence
不符、lease_until<=当前时钟、status不在允许集。现场r/now未单独保存；本报告
不能单凭消息证明唯一为lease到期，也不从G0wall−30计算“超限0.122秒”。first
return没有时间戳，不能把returned=true当作返回时间或最终期限通过证明。

对冻结源码的直线顺序和上述后续栈，能够**推断**原 `_cold_receipts` 已返回：
该调用内checked_counters、native begin、pin_receipt_binding、原_receipts、produced、
record_receipts、finish都在当前后续位置之前；随后原attempt回读、parse/usage/schema、
receipt_for、settlement-parsed也已走过。没有独立phase计数/root dump，实际m未
直接记录，因此这是明确的源码控制流推论，非额外运行采样，也不硬编码m=0。
前窗停在firstcommit，本窗已到其后的原第二前缀；仍未完成整个G0、Cold2/W5或PB。

五阶段本次 **5389 codec / 成功返回3750141856字节 / inclusive线程CPU15.172792443秒**。
run_context codec892→664（少228），resolver1143→993（少150），恰与局部证明
对应；合计少378个重复编码。prepare仍3628，accounting95、archive9。
五阶段wall依次15.386716115、2.690322941、0.392832366、3.996897175、0.032063194秒。
CPU/返回字节是原仪器口径，不是SHA调用采样，不含全部G0 CPU，仪器非零开销。
两个窗口停止位置不同，不能把单次总wall差当作受控提速或完整性能验收。

逻辑resident/live458430612、peak478097556、work188404034025305936651508，
scope后false/0/0；非RSS/CPU界。disk6785次采样，peak logical2256916、allocated
2273280字节；平均间隔0.05039171621653927秒，配置0.1非计划采样周期/硬配额。
源before/after/parent-cleanup摘要一致，原件哈希全部核实，DB仅本地保全与Git哈希。
0真实模型/费用/权限，无自动重试；W5仍为原static stop而非观测counter口径。

最小剩余条件仍是原第二提交前缀/方法及scope最终检查完整返回；先查明该复合
门具体拒绝条件，继续基于实际成本设计最小等价修复，不能原样再跑碰运气，亦
不能延租约、删检查或把首commit/回执返回当成全流程成功。

两份最终窗口只读独审均确认UNKNOWN/NOT_PROVEN和上述来源推论边界，原件已封存；reviewer未执行产品、测试、DB或新窗口。
