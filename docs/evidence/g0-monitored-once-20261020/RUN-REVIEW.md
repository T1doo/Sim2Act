# 唯一监测窗口运行后只读独审

结论：**ACCEPT_ACCURATE_UNKNOWN_ADAPTER_FAILURE_ONE_WINDOW_CONSUMED_NO_RETRY**。本次准确分类为UNKNOWN / INTERRUPTED；唯一授权窗口已真实启动并消费，不应重试。这不是原G0业务拒绝、租约拒绝或旧PB超时根因证据。

执行代码HEAD为 `4e85aecc0a8da3151df120f917f8da8feecea0f8`。独立只读核grant、description、运行manifest及parent回执：HEAD一致，4131份源码/依赖清单相同，摘要 `87be3bda0ca5cb97a787f0c5a90835a6186cb975848019645354d31b8d2c1751` 与收尾重核一致。已知授权目录仅一个运行子目录与一份grant消费marker，未见第二启动证据；marker原件已封存，旧授权不能复用。

## 原始失败与未到达边界

原diagnostic两个记录均为Boundary：`unexpected fixture writer options`。首条trace是原 `receive:124` → CPython `pathlib.open:1013` → `g0_guard.fixture_open:248`。只读核实际标准库源码，Path.open确实把buffering、encoding、errors、newline默认值作为位置参数转发io.open；保护writer的`if args`误拒。`receive`在该行之前已调用原合成handler，之后才准备写mock日志，因此可以由冻结源码顺序推知handler已进入一次；这不是一个独立handler计数器，也不能称完成的成功收发回执。

原事件明确`mock_exchanges=1`、`mock_methods=1`、`g0_entered=false`、`partial=NOT_REACHED`，控制日志只有fixture_start和finished UNKNOWN，没有g0_enter。Generate尚未完成，Source/Cold/G0/W5/G1/finalguard全部未到达；原命名finite/end/stop及五阶段差值不存在，不应填0或重读数据库伪造。mock-exchanges.jsonl为0字节、response未交回调用者；不能重演handler补出丢失响应。

须区分：0字节是模拟收发日志，不是“所有wire均没有归档”。作者的新库只读摘要显示原请求正文及seal已随10条delivery记录保存；Attempt仍STARTED，response=null、usage unknown、tokens=null。它们与尚未接收/结算的中断状态一致，不能改名为已知用量或成功完成。

本问题属于作者保护适配器和预检覆盖缺口；本独立前置静态审查也未发现该Path.open接口兼容问题。19项纯单元通过、4项旧native跳过从来不构成该原fixture调用方式的实际覆盖。本次没有因此把UNKNOWN伪装成原DomainError，也不能解释旧G0超时。

## 资源与原件

parent回执整轮工作2.309956631秒、48次采样，逻辑峰值1,329,125字节、分配峰值1,339,392字节；无预算超限，仍只说明采样监测结果，不是硬配额证明。回执为OWNED_GROUP_EMPTY、finalization_errors空。本人另只读/proc stat实核PGID46859当前无任何成员，未对任何进程发信号。

独立逐项核ARTIFACTS.json的13份归档大小/hash，全部吻合；除原fixture.db外，其它原始授权/日志/JSON清单与归档逐字节等价。JSON gzip仅解压JSON比对。fixture.db.gz只作不透明压缩文件hash检查，没有解压或打开数据库；原数据库SHA仅交叉核parent receipt和作者mode=ro前后摘要，三者均为 `df9f1c8de7a6e2a6d17dc828f666e1b18c969757d8821149ee0d1673f2df664e`。作者摘要是1个RUNNING Run、1个STARTED Attempt、0个Operation、10条delivery记录；这些数据库值由作者只读提供，本人没有另开SQLite。

原G0与阶段资料NOT_REACHED必须保留；原件不得事后修补或恢复Run/DB。精确缺失仅为原Path.open默认转发参数与保护writer接口兼容性及对应纯单元覆盖。本次未修程序、未第二次启动，不应继续外围工程。任何以后另获范围的工作也须先最小修此接口并独审，业务诊断必须另有明确的一次新授权，不能续用已消费grant。

本次本人仅读源码/JSON/日志、计算hash、核JSON归档与/proc stat，没有运行产品、fixture、Worker、测试、编译、Mock/G0/PB/launcher，没有导入或打开SQLite数据库，没有读取原fixture.db负载，没有访问旧数据库，没有改仓库或发信号。逐项原件核验及限定见RUN-REVIEW.json。
