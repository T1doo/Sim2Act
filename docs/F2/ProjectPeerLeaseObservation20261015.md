# peer_version 发前租约失败：有限公开边界观测，未证实修复

**没有提交产品修复；旧完整回归仍为388 PASS / 1 FAIL / 0 ERROR / 0 SKIP，RC1，整体NOT_ACCEPTED。** 本轮只完成两次原失败单例观测及独立核验，两次PASS不能覆盖旧FAIL，也不构成完整回归通过。

基线/观测源码 SHA `2747eec91fdcfdefb6f575a8d96dbb0dab26114e`，分支 `dev/project-peer-lease-20261015`。旧完整批代码冻结于056，2747仅追加原已审文档证据；历史见[原交付说明](PBSourceArchive20261015.md)。本轮src/tests/pyproject及85模块资格pin均未改变。

## 执行合同与真实结果

仅执行原节点 `tests/test_project_natural_revalidation.py::test_late_project_change_no_partial_save[peer_version]`，两次独立隔离SQLite/实际Worker/显式MockTransport，各次最多900秒，均正常结束未超时。原sent==1、零typed保存、两Release保持及变更后旧plan拒绝等所有断言未改。第二次额外观测竞争callback恰1次RETURN，证明实际版本更新回调完成，未以发送前拒绝冒充该竞争测试。

| 独立单例批 | 秒 | span数 / 丢弃 | 主heartbeat最大秒 | 主线程BEGIN取得最大秒 |
|---|---:|---:|---:|---:|
| 原公开边界 | 87.848491 | 6262 / 0 | 4.518040 | 1.854234 |
| 精确调用点及回调 | 134.423581 | 6046 / 0 | 7.845462 | 0.001517 |

各批均1 PASS / 0 FAIL / 0 ERROR / 0 SKIP，RC0；不与旧完整批或其他历史测试累计。各自499真实文件pathset与before/after/执行副本/root/Git逐字节闭合。观测器hash在执行前COMMAND记录；终态后封存的observer/runner副本标明时点，并核observer hash一致。

第一批XML SHA256 `faf6f14cb1ae776fde227e251b2463b56c0bd54cdfb65c63147951d5f29785f0`；第二批 `4276d848d0d538454e1b856bbca3700bd0813b362e56ec92c75251cd8268cd8d`。第二批公开回调耗时0.003708秒。真实书生/Intern及其他真实模型API调用0，未配置凭据或扩大费用/网络安全权限。

## 分段测量与不能推出的结论

SQLAlchemy公开cursor事件只观测原BEGIN IMMEDIATE取得/失败，不新增SQL，不录参数/数据。函数wrapper仍调用原函数一次、原事务enter/exit及异常行为不变；观测会扰动时序，不能用两次耗时作性能前后对照。tx.acquire包含连接和BEGIN，两者重叠。下面是第二次整条测试中的**inclusive嵌套调用**，不是互斥时间，合计不能当总耗时。

| 公开边界 | 调用数 | 最大秒 | inclusive合计秒 |
|---|---:|---:|---:|
| project.members | 17 | 4.534204 | 41.715901 |
| project.calculate | 15 | 7.130270 | 40.206485 |
| source_scope | 4938 | 7.820640 | 137.454717 |

第二次主线程最长guard为7.827240秒，其中直接source_scope为7.820640秒，scope之后余量0.006575秒。余量还含Run行读取、lease谓词与frozen contract证明，**纯lease谓词耗时NOT_RECORDED**。其他线程BEGIN最大5.131273秒、6次失败；BEGIN异常未记录SQLite errorcode，不能仅凭OperationalError类型认定全是busy或锁等待；回调后合同拒绝也不能当作旧发前Stale worker lease。旧68.5745秒失败的BEGIN/source_scope分段当时未记录，不能从本次成功运行倒推。

## 微去重候选的独立结论

members的load_family先走validate_frozen_candidate→compile_preview→自然编译器，随后members:145再次编译同候选且丢弃结果。独审证明编译器无DB/时钟/授权副作用，但两次SELECT的candidate一致性仍须明确保证。members/logic.context各自权限、版本、原来源及完整成员证明职责不同，不能删除这些验证。

第二次按caller文件/函数/行精确筛选members:145，实际34次、合计0.175312936秒、单次最大0.009776986秒，约占成员重验inclusive耗时0.4203%。第一批粗筛把graph.current中的编译也算入候选，上界72次/0.258204秒，并非精确重复次数；INITIAL_COARSE原输出保留，修正分析及METHOD_NOTE明确说明。

**该数据不足以将删除重复编译认定为租约修复，本轮未实施此微改。** 两次单例均未复现旧失败；具体瓶颈仍未知，因此没有获证实的最小产品修复可提交。未扩lease/Run预算、未跨事务或write epoch缓存、未删除授权证明、未改原竞争断言；也未转向其他微项。

## 剩余阻塞与未执行项

当前阻塞是旧发前租约失效未复现，且旧失效段缺公开分段证据。应保留旧FAIL，不能仅凭重跑通过关闭问题。此次已按有界范围完成两次观测，停止重试，未盲跑389。没有产品变更，未新增资格版本或声称修复后安全反例/完整回归通过。

完整389重跑、新修复反例测试、PG、Windows、原生浏览器、旧源码升级、人工语义、真实P-A/P-B、真实费用、远端CI、部署均NOT_RUN。没有新的工具授权拒绝；已知被拒私有DB/UDF/barrier、proc cwd及浏览器路径未重试，未删除未知锁。此前388P1F及审查JSON重建历史仍留在原归档，未覆盖。

[本轮证据索引](../evidence/project-peer-lease-20261015/README.md)含两批COMMAND/START/PROCESS_EXIT/XML/RESULT、499源码副本与manifest、公开边界数据、初始粗筛和更正、外部observer/runner及独审。证据完整性通过不等于产品通过；后续正常push核验回执单独存工作区，避免归档自引用。
