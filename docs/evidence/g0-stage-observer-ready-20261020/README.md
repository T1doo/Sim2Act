# 五阶段G0观测器审查包：只构建验证，第三窗口未获准

基线 `30977f013dbcf7c9f20d88ccff7ae9d8a25106c0`。保存环境与远端/HEAD已核、启动时工作区干净。根为唯一写入者，审查者仅只读及指定纯测试。本轮不创建grant、不运行--describe/--execute-grant，不续旧库、不启动第三个Mock窗口或真实模型，不改变main、权限或费用。

## 目的及最小接线

旧完整G0已有本线程CPU32.037725秒、codec inclusive CPU19.904881秒、input_key累计SHA输入5,164,606,462字节（见既存pb-full-current-once证据）。这些总量不再重测，也不能相加或当作可追回预算。本次补齐的是原五阶段内部的四类调用分布，绝不由61KB两模型profile外推完整G0热点。

只新增诊断模块g0_stage_observer.py，并在原g0_prefix中安装四个模块属性wrapper及原_ColdCommitDiagnostics.stage wrapper。五区间仍是原_prepare、_graph_run_context、_graph_pb_accounting、_graph_resolve_trial_source、_graph_pb_archive_chain；只有boundary.entered、同一diagnostic实例、同一前台Worker.once线程且位于原stage yield主体内才计数。原context enter/exit/异常抑制、原业务函数调用及返回值均完整委托一次；未改产品src、StopBoundary、W5前停止位置、租约/TTL/Run/RPM、交易原子性或磁盘采样预算。

## 数据口径与热路径约束

- 固定5×4=20个聚合桶、最多32帧；没有逐调用日志，不保留args/模型/正文引用。wrapper每次在原调用前后各读一次thread_time_ns，计calls/returns/raises、inclusive CPU和observed-child-exclusive CPU。exclusive只扣已观测直接子调用的inclusive，仍含未观测工作与嵌套观察器残余开销；不能把跨metric inclusive相加当总CPU。
- 输入量只对精确dict/list/tuple记录O(1)根元素数，对精确bytes记录根字节数；其他输入根记unknown。typed模型不读取__dict__/字段/descriptor，不repr、不len陌生对象、不做额外遍历、model_dump、序列化、hash、pin或authority读取。根元素数/根字节数不是完整图字节量。
- codec成功返回精确bytes后才累计codec_output_bytes。该值在原input_key调用链是完整SHA输入量的代理，但这里没有包SHA，direct codec调用也可能不hash，故字段不冒称SHA字节或真实I/O。
- 未到达stage的metrics为null；故障时INCOMPLETE且timings_valid=false，不把残缺数值当完整观察。越栈、时钟、门控或聚合故障只停采，不抛Boundary、不重试/跳过原调用，不覆盖原BaseException或原context语义。计数及CPU仅在内存聚合；报告在G0原上下文展开、专用停止后（或未知失败退出后）加入原有诊断归档，计时主体内没有磁盘I/O。

## 本轮实际验证

[OBSERVER-UNITS.log](OBSERVER-UNITS.log)：9项纯本地测试通过，包括假CPU时钟的包含/独占嵌套、根单位、五阶段/实例/线程门控、原context抑制及enter/exit错误、原异常对象/原始frame、时钟/聚合失败与固定栈溢出、状态收尾。隔离子进程只调用真实pure codec/storage/copy/equal和原stage context，验证返回/异常/原counter不变，阻断Store/Worker/模型构造及所有transport，10秒上限；不导入业务fixture或开DB。

完整[PURE-UNITS.log](PURE-UNITS.log)52项：48通过、4旧native案例skip；[ruff](RUFF.log)通过。既有纯CLI测试只验证非法--child被BLOCKED、不分配业务输出，不构成窗口启动。[OVERHEAD-CONTROL.json](OVERHEAD-CONTROL.json)仅是10000个空纯调用的本地对照，增量本线程CPU约840ns/调用，固定20桶/32帧；它不是完整扫描、G0基准、上限或提速预测。

[设计预审](DESIGN-REVIEW.md)为有条件诊断设计ACK；[补丁独审](REVIEW.md)审查精确补丁与指定纯测试。原证据逐字节保留。没有新G0分段实测数据，COMPLETE_OBSERVATION只说明已到达区域的观测收尾，不表示业务成功或五阶段全部到达。真实窗口中的开销与兼容性仍须日后明确授权的一次受限运行检验。

## 冻结边界

审查通过后只冻结源码、测试和本包并正常推送开发分支。旧grant已消费，第三个最多6交换/8入口、600秒工作+10秒自有清理窗口尚未获准，本包不创建或暗含执行授权。若用户后来明确批准，必须绑定新冻结HEAD及源码清单、新grant、新目录；不得复用旧Run/DB，不自动重试，原更严prefix480/G0120和W5前停止均继续有效。当前G0超期未解决，不改任何期限或授权语义。
