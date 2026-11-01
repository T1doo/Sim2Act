# 提交事实、固定物理连接及拒绝清理：冻结源码0d4bd59b

源码0d4bd59b08fb1fef15f9a63f20c04d642816a874，前保全074e7ccbf86cba4d69cdaedca198ca63910f9007。本轮不是完整跨库租约fence：默认新marker依然拒绝执行，原30秒大型验收未运行。

原DBAPI委托进入与正常返回的事实迁入C私有opaque capsule，不用公开属性或Python closure的可变表。源码新增独立family12（旧Source/PB校验范围不变），固定安装函数、最终Boundary类、方法code/default/closure、原DefaultDialect函数、SA Connection/RootTransaction/PoolFairy角色；可信install帧登记engine/class/entries。构造器借用在实例setter前拒绝；每raw/tx仅一份活体记录。Native facts从Snapshot运行帧的不可变code常量读取，替换class property不会伪造COMMITTED。

物理role在Python identity/tail读取前及最后委托前重核。拒绝清理只用入场原raw/owner或C保存roles，恢复原Connection类型不执行foreign getter/setter。角色打包先持强引用，scope退出释放heavy引用，事实保留至scope释放；engine.dispose撤销新发行。Runtime原生期望表也迁opaque capsule，避免gc.get_objects找到可改dict；活体weak callback手动调用不删除记录。

**有意收紧内部DBAPI接口**：有限事务的原DefaultDialect.do_commit仍只调用一次，但参数固定为本次实际raw DBAPI connection，不继续交可重绑pool proxy。沿已有raw协议，固定正确物理目标；不宣称观察proxy参数身份的hook行为等价。delegate返回即记已提交，再做物理复核；晚期proxy变化会invalidate并保留COMMITTED。delegate异常保留UNKNOWN，不假称回滚或重放。此事实记录不签授权/Graph PASS，也不声称截止时限包含所有任意Python观察回调或OS fsync延迟。

原始失败保留：v2合并30失败/66通过，误要求guarded拥有并未捕获的engine局部，修为实际Connection.engine验证；v3 98通过/1失败为Connection.close后invalidated属性断言错误，改核真实pool丢弃事件；v7 103通过/1失败为测试Foreign类型布局不兼容，改用合法空slots Connection子类，未放宽物理类型门。早期普通属性/closure方案及失败日志也保留，不合计为最终验收。

**冻结结果**：同一0d4bd59b源码161检查全部通过、零跳过、30.64秒，覆盖提交/快照/期限/控制主库桥接/原语/基础流程/原PB及Source原生行为；软件资格PASS。实际双库反例在clock或原delegate PY_START换proxy：不会提交另一库；后者正确固定主库提交，记录COMMITTED且另一库仍未提交。反射/GC、构造器借用、方法变异、foreign raw/c清理、foreign owner类以及property伪造均有反例。

**正常小型入口**：该源码原脚本prepare-pa成功（5 Mock、0live），独立新解释器verify成功，CSV30、两次P-A新材料/版本历史、3份已有结果回读一致；持久行未变，无新worker/model重放。完整demo/cold receipts随附，未公开DB、登录或HTTP认证原件。自然输出仍有原人工审核PENDING/语义未验，不能称自然目标整体完成。

Linux CPython3.12.14/GCC原生身份见native-identity.json，Windows/PG/live未签，新候选未打包。旧5af小型Linux包保持。剩余核心：Worker与全部租约消费者迁移、W5协议receipt纳入完整G1、独立control锁跨最终实际提交的fencing、两次大型原30秒保存/首开/持锁取消。0新增live、费用、WindowsCI、凭据权限，未改main/发布。
