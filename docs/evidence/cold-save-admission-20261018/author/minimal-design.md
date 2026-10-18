# Cold SAVE写后当前准入：最小修复与验证边界

基线f89f8f4431a63e22a9f067cd74e3bdd4051d84ea；本次源码冻结fd96df814e8c0fb6db6651ce77eb484951240ecc。
本文件先记录已实现与已知诊断，不预判正在执行的fresh结果。

## 唯一生产改动

`pa_spec_apps._advance_local`原1257处的`commit_guard`原位保留，仅在其外建立新的
`_journal_reads(worker,c)`。原SAVE写前guard先执行；artifact/intent/effect写入会由Store的
非SELECT监听器清除旧读段。新的guard读段从这些写入之后开始，结束于下一组写入之前。
它复用既有完整证明机制，仅限固定JournalTrialBinding/test SQLite/同Store、连接、事务、
driver transaction、线程和write epoch。没有新增缓存类型，其他绑定仍为原nullcontext。
未移动或删除任何guard、CAS或终态fresh检查，未更改任何lease、Run deadline、版本或权限。

静审移除新增import/context包装后，整个生产模块AST与基线一致。
本次只改1个生产文件与1个测试文件，137个生产blob未变。

## 原失效Run与只读诊断

封存run8 Cold SAVE的原31.750393177秒准入超lease7.866225481秒，是原有真实使用阻断。
原记录没有保留外层1220/1257 caller，不能补称已分辨该次调用点。
原夹具现在lease失效，不允许进入SAVE、续期、重放7请求或修改原合同以恢复它。

两个串行150秒上限诊断均以sqlite mode=ro打开原夹具，禁止模型/网络，原DB SHA前后一致，
两种读取路径都保留VERSION_CONFLICT：

- 单独当前准入：3390条SELECT，两种读段方式相同，约5.3/5.5秒，未复现31.750秒。
- scope/audit/current读取组合：3731→3627条SELECT，约4.65/4.31秒，SQL执行约0.2秒。
  主要CPU花在bound/lineage证明。该组合是guard组件诊断，不是完整SAVE或性能保证。

## 定向回归与旧安全边界

在原封存失败夹具的明确标记合成副本上执行原B9窗口，原始DB保持未变，未发任何请求。
随后首次回归脚本尝试构造旧Journal Worker，被软件指纹已变正确拒绝，exit1与原stderr保留；
没有覆盖旧合同或放宽软件安全边界。

补充命令不重跑9窗口，以合法generic原Worker（无旧pa_trial安装）验证旧SAVE入口及
显式新_source_reads中的原commit_guard均Stale worker lease/VERSION_CONFLICT；各窗口55表
不变。该命令exit0。它是组件回归，不代替新Journal绑定的fresh整链资格。

## Fresh验证设计

同一module-scoped generated_prefix先实际生成本轮gen3，B9只依赖该前缀。
A的actual_prefix再继续实际Source2、Cold2并保留全部原结果/owner入口断言。
A/C/D函数AST未变，B9主体及断言未变。单命令明确B→A→C→D，不设fail-fast、上限900秒，
仅执行一次fresh整链。所有ID、软件指纹与合同均重新产生，不使用旧响应或旧prefix替代资格。

外部被动observer不执行SQL或续租，不改返回、异常、clock或业务决策；记录guard caller、
线程CPU、SQL次数/driver执行时长、read-segment/epoch与最后committed heartbeat lease。
事务span结束点是SQLAlchemy commit/rollback事件，位于driver实际完成之前，不能冒称包含
真实driver commit全部时长。原始输入与helper在执行前后哈希核对。

真实API授权/key存在事实沿用；余额、强制无新增费用及真实source/controller受审安装仍未证实。
本修复不触发真实API；Windows、PG、远端CI、真实语义/人工验收及新PB/AT10不属本次运行。
