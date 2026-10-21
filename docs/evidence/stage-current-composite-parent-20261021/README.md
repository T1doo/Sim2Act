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
