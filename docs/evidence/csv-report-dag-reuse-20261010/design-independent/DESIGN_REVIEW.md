# 设计限定可行，候选实现未签收

只读基线HEAD f13ff8d7661490a7e42a1f7ce3e9179bda54da4b；作者随后正在改csv_dag_instances.py，尚无最终冻结。本轮无产品/refs写入，无测试、CI、PG或真实模型操作。

原V5§5.2–5.5和§10.1要求有类型工作流、发布绑定与新输入实例结果；现三节点CSV read→sum→report已经可以编译、执行和冷核Run，但内部版本复用只接受无条件两节点read→sum。将严格三节点成功源纳入独立内部版本，确实补上“报告链→冷新列复用”缺口，复用现执行器与授权即可；仍为固定离线工程子集，不等于模型生成、任意DAG、完整P-A/P-B或正式发布。

最小合同：保留旧internal.csv-read-sum.v1完整字段与两节点语义；新internal.csv-read-sum-report.v1只能由实际结构派生，恰3节点、read无前驱且同CSV data source；aggregate仅依赖read并固定column输入；report仅依赖aggregate，五个输入端口全引用同一aggregate的同名字段，无when/branch/额外节点/改线。唯一sink恰report。来源必须SUCCEEDED、3个真实VERIFIED Operation、工具计数3，源计划/图/draft/授权/实际bytes/hash/fence/run版本全部重构。

连接风险：csv_dag.final_result.output_by_step仅含真正sinks，三节点链aggregate不再是sink。现ledger按aggregate_step索引会缺键；建议新版本独立冻结result_step为report，从已核完整report sink投影csv_reports.FIELDS五字段到原typed schema，并由原receipts核report严格等于render(真实aggregatetuple)。报告全文与3个回执仍留Run；不能伪加aggregate为sink，不能只验sum而信text。

所有版本比较需要闭合：source_snapshot由真实closed结构选version；snapshot、ReleaseOrigin/body+双seal、binding.namespace、execution_source.version、accepted.internal_instance.version及cold enumeration全等于该真实版本。成员属于两版本集合不足以授权；同改所有标签但两节点结构不能晋升新版本。派生每列计划只能改原column/aggregate pinned column/requestkey，继续完整sealed body比较。旧字段不加新键，新字段仅新版本分支。

report虽纯计算、无Grant/资源读取/artifact/模型工具权限，仍为第3个计费工具步骤，原编译器按3分摊预算、来源合同/当前平台交集不变。max_tools不足3、deadline/租约/fence变化必须在全部写入及最终typed事务提交前拒绝。源码依赖hash本就覆盖模块，新增代码可能使旧图/计划当前证明失效；旧成功行要保留并返回既有409/NOT_VALIDATED，不改签、不承诺跨升级无缝旧历史。

页面按精确所选已核Release版本校验接受回执和冷Run，而非旧硬编码或宽松startsWith。prepare/commit/create/run独立明确确认；UNKNOWN保存原key/body，UNKNOWN后403/重试冲突不得释放；已接受晚回执可保存但不得跨应用/身份/代次paint或继续POST；冷历史零POST。报告用textContent，脚本样列名保持惰性。不得显示原single-action实例会执行报告或改变其路由。

必要冻结后独立负例：旧2节点晋升新version/新3节点降旧version（即使双seal一起改签）、Report混合五字段/不符前驱/额外节点/条件/不可信源、源3回执缺失或text篡改、预算2不足3、跨owner/project/runtime、撤权/sourcebyte/锁/fence/CAS变化、joint删除marker+joins保event、typed+AppRun联合伪造、UNKNOWN重试403及晚ABA、两新列报告/独立精确数值+冷零POST。既有共同门可按未变字节桥，不盲目全量重复。

## 有界容量观察

仅解析既有9002 raw事件：592start，其中591完成；591个start→next-start间隔总801.110秒。首start elapsed3.750，最后active start804.860，终态815.829，因此活动节点后10.969秒及前置collect/终态成本另存，不填0。该日志没有passed phase耗时事件，间隔包含执行/fixture/teardown，不能拆出每项占比。

最大已完成间隔：conditional native True24.672/False24.406；csv_dag_instances双冷列20.718；namedReport UI17.109。前591按文件累计csv_dag_instances27项113.078秒、controlled_branches53项58.687秒、csv_composition42项51.781秒。它们属于不同断言语义，不能仅因都启动source worker就删除重复用例。

旧1586项完整PG XML suite1064.925秒、case time总1063.744秒；旧1035项SQL/PG完整suite392.106/892.523秒。来源/收集集合与当前2250不同，不能混用预测当前最小预算。env是function-scoped，每个case隔离初始化项目/DB(schema)，UI另启真实HTTP与node进程；conditional native False/True各seed两份资料再启动独立进程。直接改为session共享可变fixture会改变权限/幂等/历史/冷恢复语义，不是已证明等价降本。

安全安排只可先从同源phase诊断定位准备成本，列清setup/call/teardown与启动次数，保存实际nodeID集合，再证明某项不可变准备材料可隔离复用而不共享可变DB/身份/权限/时钟。端到端900合同下，maxparallel1独立分片增加重复Setup，不能靠多个900作业宣称满足900；未测尾部成本仍UNKNOWN，不支持无证据扩并行或扩大预算。
