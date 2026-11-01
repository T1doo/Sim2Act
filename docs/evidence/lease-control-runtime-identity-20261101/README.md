# 主库激活、已提交回执和Runtime身份边界修复

前检查点25541314db2abeae87410869f426bd55cb362c93。新路径仍未启用，不是完整产品或大型Cold验收。

激活在marker真正提交后重取主库BEGIN IMMEDIATE，鲜读完整owner/version/fence/状态/marker；读取前后及原DBAPI边界检查零写，拒绝同连接SQL/commit回调改数据。恢复确认只读另一独立主库handle的已提交receipt，未提交再回滚的receipt不能ack控制库。

Runtime身份记录迁至C私有弱引用registry，只接受固定enable帧和精确8字段，核原Store类型、固定字段和无实例method shadow。代码、clock/connect和actor原见证保留；新增预发行PY_RETURN插入方法、校验后插入方法、Store改类型/实例方法、伪造Python状态反例。注册先分配registry成功后发布，NULL入口拒绝。内部方法不再用可覆盖的self.method查找。

v4结果5失败/51通过，失败为新测试清理重复delattr；原日志保留，未改变拒绝断言。修清理后v5实际57通过，15.59秒，零跳过；包括基础流程、主库竞争与原生反例。生产资格检查PASS。GCC/Linux CPython3.12构建；0live、0费用、0WindowsCI。

尚未完成：Worker心跳/所有Run租约消费者和DBAPI原始提交屏障整合，默认Store.guard继续拒绝新marker。未进行新大型Cold、30秒正常入口、持锁取消或新安装包验证，旧5af已验小型候选不变。
