# 主库交接与原生入口检查点：执行入口仍关闭

源代码在本检查点新增可选原生代码族10（租约/适配器）和11（原Store actor启动快照），原Source0–8和PB0–9校验范围保持不变。固定最终wrapper的code/default/closure及clock/connect别名；不把纯Python私有closure视作时钟资格。

首次family10验证真实SIGSEGV/exit139，发生provision入口、未claim/业务写。原因是CPython3.12静态object类型tp_dict可为空，而旧code_items直接使用PyDict_CheckExact。新增NULL拒绝，并按原PB模式只登记可变heap类，内建静态类独立子进程反例确保不崩溃；临时fprintf全部移除。原故障与分段原日志保留。

原生入口/反例/旧PB数据50检查通过；主库实际交接/新进程回执恢复/原语及基础功能45检查通过；增加Store actor见证后21相关检查通过。它们是不同阶段，不能合计成同一完整产品验收。软件资格核验通过，0模型/费用/新WindowsCI。

适配器使用实际主库Run与已提交marker激活control；续租不变main历史lease字段。真正全新解释器能以实际main receipt确认control pending，重复ack不重放，且authority.sessions仍空、不重发旧mono。该main receipt案例仅元数据桥接：未执行自然业务，Run.result仍None，不冒称保存目标已成功。

尚未闭合Worker/所有租约消费者/原DBAPI提交委托接线。新marker的Store.guard明确拒绝，legacy expired/queue扫描排除新协议，未设置可修改READY字段放行。未跑大型Cold，未默认启用，也未对新Windows/PG/live/安装包扩签。旧5af小型包与其原验收保持。
