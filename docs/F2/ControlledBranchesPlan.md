# 受控条件分支：实施前冻结

依据 V5 产品 §5.3、阶段 F2-T04；基线 5bbc462b4ce0027fe9349e4b42064fe75f1470f5，独立 dev/controlled-branches-20261008。复用既有 CSV 应用、三节点计划、Run/Worker/Operation/事件账本及页面；不是新的任务家族或并行运行架构。preview 必经，aggregate/report 可各声明一个 when；不接受客户端任意 workflow/动作/依赖。旧请求不含条件字段时定义、回执形状不变；完整源码版本改变仍遵循旧证明失效政策，不改签历史。

when 为 eq/in/exists，只引用 manifest 中有 schema 的 input 或已声明直接前驱的输出；禁止 data、未来/自身引用、代码、组合表达式、循环。eq/in 常量须符合引用 schema，严格 JSON 类型：bool/int/float 不互相等同；in 有界非空最多20值。exists 不带 value，null 不作为可使用值；缺失字段 exists=false，eq/in 缺失 INVALID_INPUT。未知字段、未知 op、额外字段、类型不符、环和不可信动作在写入前拒绝。

本切片输入只扩展可选 include_report:boolean，运行确认闭合 branch_inputs，仅该字段；缺失保留缺失，不默认 true/false，不接受 null 或数值。输入、计划、源码/来源版本与精确确认一同冻结在已有接受事件和独立回执中。condition=false 记录 SKIPPED/CONDITION_FALSE；任何声明的直接前驱 SKIPPED 时下游 SKIPPED/DEPENDENCY_SKIPPED，不读取不存在输出，不运行该条件、不创建 Operation。跳过证明包含条件、已核前驱指纹、输入指纹和来源hash；成功执行回执包含同一分支决策。冷恢复先重建并逐字段核对全部已持久决策，不重发、不改路径。被跳过 report 的最终 output=null/output_status=SKIPPED；终态PARTIAL，不满足清单必需报告输出；只有实际产出并核验报告才SUCCEEDED。semantic UNKNOWN/owner PENDING/发布false，不能当报告或业务验收通过。

每事务重验来源/授权/精确版本，跳过与执行均经已有 project锁、fencing、最新租约/截止和有效预算门；tool计数仅实际 Operation，最多3决策，保守三节点预算不降低。并发/冷worker不能重复接受或追加决策，撤权、来源/保存证明篡改失败关闭。0模型、0业务写入、无Grant/身份/表/DDL/发布新增；人工锁公开入口不做。

验证：eq/in/exists与缺失/严格类型、前驱引用、跳过传播、循环拒绝、同一确认计划不同输入实际分路、冷Store/前缀恢复、撤权/来源/决策篡改、预算/租约/并发；原DAG/接线/局部修改及契约预检影响范围回归；SQLite和自有隔离PG及实际loopback页面/productJS。原Windows900/Edge240/Node150/依赖/原断言保持，无新CI/LIVE。候选普通push供独审，不合dev/main；原生/通用运行器/语义/完整P-B/人工签收保留未完成。
