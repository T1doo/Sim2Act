# 未安装的持久生产试验 journal 与账户 cursor CAS

基线 `080ea7b184a7476019431c1803b4bfe4864afbd9`；普通分支 `dev/production-trial-journal-20261018`；源码及测试冻结 `12958af924fad425fa619adccd1841fb8f8228a8`。开工本地/远端一致、clean、约23GB可用，root唯一仓库写入者。父级有限审查通过前一内核后，本轮先做独立最小设计审查，再实现实际持久控制器；账户授权缺失没有阻止这片离线工程。

前一轮19个唯一节点/20次执行/20PASS保持其原执行与继承范围，本轮不重跑、不计入新通过数；其中取消仅顺序SQL，正向仅generate，不能借为并发取消或完整source/cold链资格。本轮独立新增12个定向节点，覆盖新存储及并发边界。

## 实现与输入

只新增 `production_trial_journal.py` 与其测试。控制器复用原 `production_trial_policy`、`Store.tx`、当前owner/project及Run/批准/phase/Grant/版本/fence/有限租约门；原701个执行输入、135个生产文件逐字不变。没有更改旧synthetic账本、resolver、资格anchor、Worker、模型、权限或表/DDL。

内部reserve/record_attempt/settle接受原principal、完整contract/approval key、完整ReservationIdentity、实际wire字节、内部SourceVerificationResult及expected_revision，settle另收Outcome。调用方没有ledger/cursor替换参数，也没有callback、source/sender selector或凭据入口。控制器自行加载服务端状态；所有receipt固定 `UNINSTALLED_DURABLE_JOURNAL_ONLY / live_allowed=false / dispatch_authorized=false / real_source_verified=false`，不是Permit或sender授权。

复用已有 `delivery_graph_requests`，在独立 `uninstalled-production-trial-journal.v1` namespace保存ledger双镜像及canonical账户cursor双镜像。账户桶沿用唯一canonical算法，在本journal内跨project/trial共享；不声称已覆盖旧synthetic或系统全部模型路径。显式内部调用之外没有初始化、迁移或注册。

ledger保存revision及最后观察到的quota revision；后者允许小于当前账户全局revision，不能因别的trial推进而误拒原历史。pair读取核精确请求/完整指纹/typed状态；缺一边拒绝，不补齐。全新quota两次upsert的创建数只接受(1,1)或(0,0)，mixed结果整事务回滚。首次ledger只从原requirements构造，调用方旧/空状态不能覆盖现有账本；不声称抵御数据库管理员同时回滚全部可信行。

只读read也须先核当前owner/project/trial的两份ledger标量锚与精确requestFP，然后按account→ledger顺序锁读并完整重验。无自有ledger或伪造trial返回OUTCOME_UNKNOWN，且不先读共享cursor；read不seed、不生成结果、不自动marker或重发。

## 事务、取消及历史

锁顺序为owner/project→account pair→ledger pair→原policy fresh（现Grant/phase/Run）→四行CAS。非重复写必须匹配精确expected_revision；每个UPDATE还匹配加载的完整旧fingerprint及requestFP（包含revision）。ledger和cursor四行同事务落盘并递增revision；任何CAS冲突全部回滚。cursor时间只在reserve推进，mark/settle不退额。reserve/record_attempt在CAS后再fresh核上下文、来源与有限deadline，失败全部回滚，不续租。

原Attempt完整身份/原scope/实际wire匹配后，reserve重复、已标记marker重复及完全同Outcome的settle重复，仅返回当前可信历史，duplicate=true/changed=false；可以承接旧expected_revision，但不写行、不重核来源以取得新许可，也不授send。错身份或改Outcome拒绝，新Attempt仍受revision与pending/halt门。

marker与实际控制写通过现事务锁形成明确顺序。控制先commit，marker fresh失败且原预留保留；marker先commit，后续取消/lease/fence漂移使结算accepted=false/halt，仍原子保留已知usage和占槽。结算接受判断位于同一持锁fresh段；迟到或来源失效不能把已知usage当不存在。这里没有provider发送，没有“外部IO与数据库原子”或“marker可发送”的保证。

UNKNOWN保留已知prompt及null completion/total，单向halt且不退槽/不重发。原settlement一旦记录，不新增UNKNOWN→KNOWN替换或人工恢复路径；不重复旧synthetic恢复矩阵或旧永久取消窗口。

## 新资格与证据

一次冻结运行12唯一节点/12次执行，12PASS/0FAIL，无SKIP/ERROR；JUnit47.523秒，外层50.645257132秒。703输入/136生产及runner/guard前后均零漂移；旧701/135桥不变。Ruff通过，初始import排序提示及修复如实记录，不计产品测试失败。

范围为同键两Store只一次预留、同账户两project/两trial首预留争抢、旧revision拒绝及ledger已写后quota CAS冲突的全事务回滚、ledger/quota各一种缺镜像拒绝修复、两个真实新Python进程读取pending/UNKNOWN并返回原key历史，以及marker/控制两顺序×cancel/lease/fence共六个两连接竞争节点。cancel使用实际Store.command；lease/fence使用明确fixture SQL。Event和SQL观测只在测试中控制已持锁写入与竞争者BEGIN尝试，有界等待并全部收束；不是PG行锁资格。

子进程stdout/stderr、六份竞争trace/结算、跨project争抢与零cursor读取、CAS回滚及镜像revision/指纹均保存。普通场景严格比较其他表；fixture收尾全表比较排除被实际控制/SQL改变的runs/events。CAS负例比较全55表严格相等。保存的是指纹/断言，不导出全库行，也不冒独立DB重建或逐操作55表窗口。运行级及子进程IO哨兵均未触发，没有模型、Worker.once、provider请求或真实生产Attempt。

独立静审先发现P2：原read允许空trial读共享cursor；修正双标量锚前置后，冻结测试正向校准查询观测器，再确认合法空trial/伪造trial的cursor SELECT均为0。修前仅静态发现，未动态运行或倒签。设计、WIP、修正、冻结及最终有限独审与原件见[证据索引](../evidence/production-trial-journal-20261018/README.md)。

最终有限独审通过，无当前确定P1/P2。独审纯文件/Git audit实际exit0，全部55份非DB作者原件逐项匹配，12个fixtureDB仅stat；没有独立运行产品/pytest/网络或打开DB。独审16文件50954B含清单已封存，作者56份及独审16份共72路径423219B逐字复制入仓库；这不提前背书后续push。

## 当前边界

此候选journal已在合成SQLite中实际持久写入并经两个新进程读取，仍未安装到API/Worker；没有真实producer、受审sender、有效LIVE许可或凭据配置。其缺失是后续执行依赖，不能再混同为必须等待账户才能编写持久控制器。

本轮未运行PG、Windows/native、远端CI、真实账户/费用/模型/语义、完整source/cold或UI链；没有重开旧取消窗口、扩展旧恢复矩阵或补回旧满盘未落盘独审。当前试验原endpoint/model/权限/caps及正式发布门保持，整体F2与生产LIVE不据此签收。
