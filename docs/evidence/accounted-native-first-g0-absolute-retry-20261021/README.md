# 绝对路径单次安全重试：OWNED发行，首commit期限拒绝

本次委托明确允许纠正相对路径调用错误后，以全新隔离目录／grant再执行一次，
失败不循环。先静态核规范绝对解释器／脚本与describe身份一致、旧PID／进程组
全结束、旧10原件哈希保全，以及无运行中launcher。实际父argv也在运行中只读
保存，含绝对脚本 `/workspace/Sim2Act/scripts/diagnostics/g0_bounded.py`。
未删除／放宽父身份保护，未绕过外部访问拒绝。

执行HEAD `102af120a66cda2c33ae2f7a48d5750e4e0fffa9`，与原冻结
`b4bac26b5ecbb98c864407170a94c202deee427a` 的src/tests/scripts/pyproject逐字节
相同，仅先前结果证据有差异。源码及依赖摘要
`39190dfc45d353346bf41c1c12786e02e94d652c603331bf8bc9569c348efedd`；
profile摘要 `f8758c85952d55e8d5ad8e257db62a20ba9cb7365deb15f94cd636da035f227f`。
没有修改执行代码、预算、事务、pin或期限，也没有重跑单元测试冒称运行成果。

## 实际终态与边界

**parent和child原件均为UNKNOWN／business_acceptance=INTERRUPTED，退出码2。**
本次实际进入G0，冻结profile对本次合成输入选择OWNED，在native:issuance完成发行。
首次commit进入原实现，但在 `natural_spec_runtime.py:2990` 原期限断言抛出：
`VERSION_CONFLICT / Production admission expired during verification`。
第二次commit未进入，原scope未正常返回，final_deadline_check=NOT_PROVEN。
保留原error_origin=UNDETERMINED_ORIGINAL_OR_CANDIDATE分类；traceback能定位
原期限断言，不把它改写为成功或覆盖原诊断。

| 项目 | 本次原件 |
| --- | ---: |
| Mock交换／入口／Source同步delegate | **6 / 8 / 2** |
| launcher work_wall_seconds | **348.2065204299979秒** |
| fixture_start至G0进入的monotonic事件差 | 310.199121651秒 |
| G0 wall | **36.6359487769987秒** |
| 最严期限：run_check.deadline=actual lease_until | 1792575664.9779332 |
| 原诊断end | 1792575671.5726795 |
| end超最严lease | **6.594746351242065秒** |
| 已返回commit数 | **0**；有1条首commit失败记录 |
| 撤停标志 | stop=false |

G0 wall和lease超时差使用不同起点，不用36.635949-30替代原end-deadline。
其他Run截止1792575880.7124422、source到期1792577125.381348均更晚。
本次没有触及prefix480／G0120／总600＋清理10的外部时限，但原lease30仍优先，
没有续长lease、Run300、TTL1800或reservation60秒节流。原三项合成替换保持明显
test-only身份；0真实模型、0费用、0外网业务或新权限，不是生产账户资格。

Cold2和W5未到达：依据首commit失败和原StopBoundary在下条语句前中止的控制流，
不是独立W5观测计数器。原字段对此明确写STATIC_STOP_BEFORE_NEXT_STATEMENT。
本次只有这一轮安全重试，没有新grant或重试循环。

## OWNED资格与资源／清理见证

本次输入选择OWNED，reason=null、diagnostic_incomplete=false；这只见证本次
合成输入通过发行前有界资格，不证明全域接受资格或两次commit能够完成。

| 逻辑账本 | 发行时／本次峰值 |
| --- | ---: |
| resident和live | 85803380 |
| peak | 105470324 |
| work | 50098473668149788430366 |

退出后active=false、resident=live=0；这些是受控新增工作的逻辑账本，**不是
物理RSS或CPU界**。冻结Bounds/Limits完整值见原profile与本次receipt，未扩额。

磁盘监测6911次，峰logical2270397／allocated2289664字节，未触及64MiB；采样
完成间隔min0.000112829／max0.136643420／mean0.050391371秒，约19.844668Hz。
配置0.1秒不是固定调度保证，监测不是native hard quota。

child报告THREADS_CLIENTS_CONNECTIONS_CLOSED，parent为OWNED_GROUP_EMPTY，
finalization_errors=[]。另只读复核child PID40388和实际launcher PID均已不存在、
原PGID无成员。源码摘要在child前／后及parent清理后均相同。没有删除证据库；
fixture.db留原地保现场，不能将保场行状态当生产漏收尾。G0 authorizer_denials=0
只表示未发生拒绝，不冒充本轮注入了写入拒绝测试。

## 已获得的实际成本与剩余瓶颈

| 已观测阶段 | wall秒 | check入口 | 旧input_key入口 | codec调用 | codec线程CPU秒 |
| --- | ---: | ---: | ---: | ---: | ---: |
| _prepare | 14.953486 | 3513 | 3499 | 3590 | 9.388694 |
| _graph_run_context | 5.509698 | 1510 | 0 | 1510 | 4.381916 |
| _graph_pb_accounting | 0.451085 | 95 | 0 | 95 | 0.336188 |
| _graph_resolve_trial_source | 8.900123 | 2324 | 0 | 2325 | 7.056982 |
| _graph_pb_archive_chain | 0.033015 | 9 | 0 | 9 | 0.026559 |

五阶段合计codec **7529次／5320311436累计返回字节／21.190339346线程CPU秒**；
这不是峰值内存、实际SHA调用计数或全G0 CPU。仪器有非零开销，不能与历史不同
观测合同的单次数字直接作提速比较；本次没有未插桩对照，也没有性能验收通过。

源码确认剩余机制：OWNED仅替换两accounted根及complete内已证明闭包；其余
可变根仍保留。`_Frontier.check→key→_ColdGraphRead._frontier_input_key→input_bytes`
每次仍调用原codec，原typed/current guards也仍进入CGR。新frontier入口不递增旧
input_key计数，所以后四段的旧key计数0不等于0序列化。确切剩余工作是证明剩余
可变前沿和实际消费者的安全边界后，减少这些重复编码成本；本次总量不能证明
哪个未迁移根可删，不据此删guard、缓存验证结果、重构事务或再开相同窗口碰运气。

## 原件和独审

原目录为
`/tmp/sim2act-authorized-native-g0-absolute-163d76cbc83647ae8f007dd917591761/`。
`raw-map.json`给原文件大小／SHA及封存路径；JSON大原件gzip无损封存，原始
fixture.db仅保留本地原件和哈希，不复制到Git、不续用。旧相对路径失败窗口原件
未覆盖。`reviews/`是两名既有reviewer的只读结果／源码核验，无产品／测试／DB／
Mock执行或下一轮授权。本片最终提交仅新增证据，执行源保持冻结。
