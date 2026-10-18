# 未安装持久 journal 有限独审

**有限通过，当前未发现阻止普通开发分支交付的确定 P1/P2。** 冻结 `12958af924fad425fa619adccd1841fb8f8228a8`，输入基线 `080ea7b184a7476019431c1803b4bfe4864afbd9`。新增仅 journal 生产模块与新测试各一文件；旧 701 执行输入、135 生产输入逐字不变。旧 policy 的19 unique/20 executions仍只是独立历史资格，本轮未重跑或并入分母。

本轮作者一批 **12 unique / 12 executions / 12 PASS / 0 FAIL**，JUnit 47.523s，外层50.645257132s。我的工作是非作者代码静审及纯文件/Git audit，没有亲跑产品或pytest、HTTP、Worker/model、DB/SQL或网络，未写仓库/作者sealed目录。`audit-qualification.py`实际只执行文件/Git解析，exit0；script、stdout/stderr和结构化verification均保留。

## 实现与原P2

新增controller只从服务端可信journal pair载入Ledger和账户cursor，不接受caller旧/空snapshot。固定锁序为自有project→account pair→ledger pair→原fresh上下文/Run锁，四行旧fingerprint/requestFP/revision绑定CAS在同Store事务中提交；任一冲突回滚。全新quota双insert只容许全新或全已存在，不补齐单边；ledger引用的旧quota revision可小于当前全局revision。原身份/wire/scope先核，完全相同原key重复仅返回当前历史，不推进revision/不新mark；active写后再fresh，late正确usage与接受权限分离。源码并未安装API/Worker/source/sender或有效LIVE许可。

WIP曾有 **P2_READ_UNOWNED_SHARED_CURSOR**：空/伪造trial的read可返回共享账户cursor。本目录保留原字节SHA、原read片段、未动态复现的发现与后续修复记录。冻结read在任何quota查询之前核自有两个ledger kind/requestFP标量锚，失败OUTCOME_UNKNOWN，随后仍按account→ledger锁读并完整重验。测试正向校准winner quota SELECT观测器，再验证合法空trial与未批准forged trial均拒绝且quota SELECT0。原错误版本没有执行或倒签通过。

## 已逐项核对的原件

作者sealed目录 `/workspace/production-trial-journal-20261018`，清单SHA `c5057f6b9c371ff03e5f7bef1e8eeb660fc71a613854cee096cb82d3e8235d91`。55非DB路径、363044 bytes逐项size/SHA一致；12个物理fixture.db仅stat大小，未打开或重新hash。703/136 inputs before/after、全部Git/current字节、两份归档源码、runner/guard helper桥一致；无生产journal importer。design原稿与修订稿hash桥也相符。

- `run-1/junit.xml`、execution/stdout证明唯一12节点，exit0，无failure/error/skipped，stderr空。分母为两个一般争抢、一个CAS、两个missing mirror、一个子进程恢复、六个marker/control排序。不是每个断言或每次读取都算一个case。
- 同Attempt两个Store竞争仅一个新预留、另一个原key历史，revision/quota_revision=1、一个槽；后续marker/settle到revision3。旧rev下三个完全重复命令只读；测试实际assert全库前后相等。cross-project/trial同账户只有一个Receipt、一个RATE_LIMITED，真实断言四行/单cursor，loser不留下初始化账。
- 六份 `linearization.json` 各为marker/control×cancel/lease/fence双序。trace显示写后持锁→另一连接BEGIN尝试→双方活跃→释放；marker先则attempted=true/revision3，control先则marker VERSION_CONFLICT、attempted=false/revision2；结算均usage8、accepted=false、halt，原时间/槽保留。cancel通过既有Store.command，lease/fence通过明确测试SQL修改。**实际并发证据是SQLite BEGIN IMMEDIATE写事务排序；不冒PG行锁验证。marker只是会计状态，不是send许可。**
- 两份child stdout/stderr来自冻结测试实际 `subprocess.run` 的returncode0断言：pending revision1/未attempted；UNKNOWN revision3/已attempted、halt、prompt5、其余usage null。before==after、原keyduplicate无写、io_attempts=[]。这是两个真实新进程只读/dup，不是新Worker执行；未保存子PID，审查者未亲跑或另做进程资格。
- CAS负例在两个ledger写后传入旧quota fingerprint，真实事务全55表strict equal断言；原件保留该断言标记及恢复revision1/未attempted状态。两个missing mirror节点损坏后维持三行，读/写均拒绝不补齐。11份journal-state记录mirror revision/FP/rowcount与其它表保护标记；cross-project case单独保存争抢原件。

行证据是测试实际strict assertion、mirror revision/FP和返回状态；没有导出全行。本审没有独立重建55表或重算journal全部原行，也不称本轮有上一阶段那种逐operation55表窗口。fixture最终保护比较明确排除由控制/测试故意修改的Run/events；普通案例另有严格保护，CAS负例全55表相等。

## 限制与工具来源

已实现内部实际持久controller及SQLite有界争抢，不等于安装到正常API/Worker或整个系统统一生产quota。新namespace只覆盖本journal，不与旧synthetic桶冒称全局共用。SourceVerificationResult、wire、usage与AttemptID均为合成内部输入；没有真实生产Attempt、模型调用或发送。所有Receipt恒 UNINSTALLED_DURABLE_JOURNAL_ONLY、live/dispatch/real-source=false；监控的provider/Settings/InternModel入口attempts=[]，child也guard五个实际模型入口。

source/cold正向链、真实免费来源/账户/费用/模型/语义、PG、Windows/native、远端CI、UI和旧永久取消安装窗口均未执行；没有扩恢复矩阵或重跑旧19节点。当前合同仍绑定旧endpoint/model，未用官方资料/截图充当免费或执行授权，不要求provider每30秒续签。未背书未来push/部署。

作者保存import-sort Ruff工具失败与修正来源，未计作pytest失败；design修订保留原稿与hash桥。我首次将run-1下四个日志按root路径读取而得到不存在，随后依据manifest读取正确路径；`read-path-correction.json`明确为可见工具输出转录，非当时独立重定向stderr，未改原件/重跑产品。纯文件audit一次exit0，无解析失败。

本新review目录封存后停止全部写入；旧sealed目录全未修改。
