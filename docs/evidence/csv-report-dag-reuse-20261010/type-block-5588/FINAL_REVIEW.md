# BLOCK — 5588 typed实例数字类型误接纳

精确源码 `5588a94faeb90abb2052a8ae5327810b8d27c287`，365冻结文件before/after与Git/worktree精确一致，69产品不变。本轮只读产品，在新私有SQLite副本写入授权攻击；原本人LIMITED_PASS61白名单、数据库及日志未改，没有PG/CI/refs/仓库写入。

用本人原CRLF/负数/中文CSV成功三步报告链、不同于作者夹具。原count为整数2，Report Operation/回执及所有原5字段typed schema均完整。两个独立DB副本先各做3个公开GET并确认200，然后攻击：

1. typed record.data.result.count改2.0并重算row fingerprint；AppRun.output.count同改2.0；Run.result仅instance_result.record_fingerprint更新为新rowFP。
2. 同改typed row.count=2.0、rowFP及Run指针FP，AppRun.output保留整数2。

两个副本中的Operation及回执完全未改；实际CSV/来源/授予/Release/接受seal也未改。每个副本公开instance GET、instance/run GET、DAG/run GET全部返回200（攻击后共6个200），所有真实请求路径和完整响应正文保留。公开instance响应包含浮点2.0的typed结果；joint场景run.output也为2.0。直接用冻结Release typed schema调用原validate_value则明确拒绝这两份typed值，schema要求count integer；公开证明仍承认该rowFP。全部GET前后全DB快照相同，零读副作用。

根因不是只改hash自证：ledger_result同时使用Python dict==比较row.data与{result:ar.output}、ar.output与实际重构aggregate，Python2==2.0成立，允许违反typed合同的替代数据通过。运行最终result指针hash可同步改签，原最终证明hash于是仍匹配新指针。本轮攻击及原body没有harness异常或预先假定BLOCK；两例已真实复现。

最低修复应同时把上述两处比较改成严格JSON fingerprint相等：row.data FP=={result:ar.output} FP，再ar.output FP==aggregate_result FP。后者来自已逐schema验证且由原CSV独立重算的完整真实Operation tuple；传递将row/AR绑定同一类型化值，区分int/float/bool并拒绝额外键，不需要放宽旧version或新增缓存/DBschema查询。只修ar→actual会遗漏第二例row-only。后续须在新冻结上有限复验旧v1/新report版的row-only和joint，并保留正常新列/冷读结果。

当前BLOCK影响typed契约完整性；原有限功能与UI通过不被抹除，但不能据旧LIMITED_PASS签收此新发现门。parent确认当前native已结束后才编辑，新freeze独审另记归属。历史PG超时OPEN、全量900UNKNOWN、Win11/整体NOT_ACCEPTED及LIVE0不变。
