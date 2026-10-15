# 生产准入合同与 P-B 来源证据工程（有限交付）

基线 `255b6ac407ebad31aedbe1b8d9547ee3892cdc0f`；开发分支 `dev/production-admission-contract-20261015`。统一冻结源码/测试 `206de555e22c9a6e85c1ea87a33c1e55c0780968`。root为唯一集成者，隔离作者和只读独审；原199用例标识均保留；其中七槽Store测试只修正已独审的心跳清理顺序并加强取消后断言，其余14个原测试文件字节不变，新增四个测试suite及一个可选观测插件，并将既有四分支文本工作流纳入回归。文档/归档提交与冻结src/tests/pyproject字节相同。

## 具体合同与接线

`natural_trial_api.py` 原admission与production-admission入口共用 `production_trial_admission.production_preflight`。先核精确身份/项目/trial/原批准、材料与Goal授权和精确软件资格，再复用原gate.admit；HTTP没有resolver/sender/FeeAuthority/free/LIVE覆盖参数。生产没有注册账户权益解析器、受审网络sender或真实P-B归档resolver；缺这些条件默认LIVE_BLOCKED，零Run/预算/配额写入、零模型网络和真实凭据读取。

`production_trial_admission.py` 的隔离注册表只允许test_only SQLite、精确类型的不可变合成账户记录与固定数据sender。sender没有transport或可执行callback，字段形状也严格检查。账户记录冻结principal/project/完整trial指纹、provider固定intern-ai、服务端opaque account ID、共享canonical quota、证据hash/checked_at/expires_at/撤回/合法免费与强制不可收费/paid_cap0。quota由固定provider和account ID派生，跨项目/trial/整个注册表替换也不能拆账号桶；caller quota label不证明真实账户或权益。账户最长新鲜窗口30秒是本轮离线合同的保守有限上限，不是已核provider规则。

离线dispatch：校验wire→原key历史读取→固定账户解析与完整资格→原budget.reserve→临固定假sender前同事务fresh admission→原budget.settle。每次_admission先重解固定账户和完整软件资格，再由原gate完成当前审批/撤回、材料Goal/软件、stage/app/release/instance/version、owner版本栅栏租约、原3+2+2总账与期限检查，再核同worker_id与附加P-B来源。已扣原key重复只读，不重发；已预留后撤回/取消/失联/未知/迟到不会退款或把未知归零。损坏来源usage转DomainError，让原settle保留真实结算，accepted=false/halted。固定假sender的事务内外检查不能证明外部网络请求原子性或未来生产发送器幂等安全。

`pb_live_source_contract.py` 新增独立 `LivePBSourceContract`、只读来源解析接口和精确合成resolver。合同绑定完整PBTrialContract及精确批准输入指纹、provider/account/quota、同trial原成功source Run/app/key、两个原response Attempts、wire/raw原字节/hash、不同provider request/response ID、provider response中的完整known usage来源、两个原source槽/预留envelope、抽取key/响应Attempt/paired extraction锚、完整编辑Recipe及不同cold材料/完整Goal。默认与foreign callback均拒绝且不调用；成功receipt恒SYNTHETIC/NOT_LIVE_VERIFIED/live_allowed=false。

cold附加桥在每次准入中将typed来源与原budget.audit source Run、两槽keys、实际Attempt IDs、原source paired app、原wire hash/byte count、归档raw完整字节及usage、实际LIVE/VERIFIED/model/server provider/account/requestid逐项核对。实际MOCK不能换标签取得真实来源资格；旧gate对MOCK的完整检查不删除，因此当前MOCK实际冷链不能满足新的真实证据桥。两层均保持拒绝是明确边界：真实DB归档解析器未实现，真实成功桥NOT_RUN。纯typed两槽证据也不代替原Generate3/Source2/Cold2总账。

路由修复仅将带精确natural VERSION的dict上下文作为分流提示，在既有heartbeat loop内执行原完整advance检查，避免在线程启动前重复整项目分类。提示本身不授权；当前DB marker、owner/fence/version/lease、binding、材料授权和完整receipt仍检查。PA/spec独立元数据确认分支新增当前namespace必须属于FAMILIES的校验，阻止未知族继续发送；合法的两类draft及独立冻结Release仍可共存。非spec Goal应用先返回False，PB保持既有更严格族检查。

非SAVE本地节点末尾原有两次完整commit_guard，之间仅本地outputs/proved赋值，无DB写入/回调。删除较早的重复调用，保留原尾部最终guard与所有当前owner/lease/stop/期限/scope/binding/receipt检查，不新增续租路径，不在写后或事务外缓存授权。

完整回归显式加载冻结在tests中的观测插件，COMMAND记录hash，执行源码归档含插件。插件记录fail_owned接收的公开error与run_id、pytest已有失败longrepr；原函数调用一次，异常原样传播，观测失败不替代产品结果，无DB读取、凭据读取、调度或许可更改。

历史47e仅改两份测试文件，src/pyproject与5ed逐字节一致；当时84模块资格pin911及review candidate660不变。七槽Store测试先stop/join并确认无运行期心跳错误，再主动cancel；新增验证线程确已结束、取消后心跳因停止状态拒绝、lease未变且仍未自然过期。原3+2+2、真实60.05秒间隔、Run300/lease30、全部原预算/总账断言保留，AST核所有原Assert多重集保留且只该函数变化。

新版冻结观测插件另记录Store.heartbeat原单次调用的begin/return真实lease/error；异常只含DomainError.public/类型/真实sqlite3.orig数值，无SQL字符串/参数/连接URL。原参数、返回和异常保持，未新增续租、DB读取或时钟/调度规则变化；日志有观测I/O开销。各新版批单独运行，不并发诊断。

206版本进一步将非SAVE本地节点的pure/validate/receipt构建放在PREPARED写前，随后一次完整fresh guard(delta1)并检查当前version/UNKNOWN，再原子写入PREPARED/intent/VERIFIED/context/AppRun/event。保留原最终full guard，并复用receipts完整读回与预期outputs/proved/context比对、公开owner/version/lease前后指针比对与再次UNKNOWN检查。最后只在同一无写/无回调/无事务退出的读段重验实际收集的授权，并重验真实lease/原最小Run期限/stop。SAVE可达AST与47e逐项相同。不延长lease，不新增续租、跨事务缓存或模型发送路径。新增21例：6个实际写后抛错全表回滚、14个写后状态变化拒绝、1个纯计算/回执构建先于唯一写组的正常提交。其故障用例明确claim后冻结测试时钟，不作墙钟性能证据。该有限优化不能保证任意负载下30秒容量，也不能宣称旧历史首因已根治。

## 实际验证

冻结版本完整批 **339 PASS / 0 FAIL / 0 ERROR / 0 SKIP / 0 deselected**，RC0；4774.01秒。339 unique，原199/306/318用例标识均保留；仅原七槽测试清理顺序作精确修正，其余14个原测试文件字节不变，新增local写组21与route8及既有TXT/MD4分支；collection↔XML逐项双射。495文件执行前后、拷贝执行源码、root与Git字节一致。XML SHA256 `0fe6266bd8a8cfc78ddb0e43fedf1faf74261115963230883e834d604b4dfd71`；RESULT SHA256 `1d9d95046524ea2e436d6cab65d756418dbb5ca99b3727d227bce07797a2a50f`。5ed版本独立探针14PASS另列，不累加339。

同SHA独立定向批35PASS/0FAIL/ERROR/SKIP、RC0，520.57秒，495文件before/after/copied/root/Git闭合；包括local21、route8、正常取消与人工锁2、TXT/MD4，不累加339。20份实际故障回滚回执均为全表相同。正常取消有4次提交续租返回且仍有3次code5，最大单次HB总调用5.073秒；锁等待/证明耗时未分段记录，不作历史根因或容量保证。

原两应用分段后完成用例，两次CHECK各实际领取1次并SUCCEEDED，原Run300/lease30/maxclaims3不变。原三项七槽用例均PASS：实际MOCK P-A与P-B各Generate3/Source2/Cold2，7 accepted/KNOWN7000 tokens/envelope48354；每条六个预留间隔均≥60秒。第三例为Store实际reserve/settle/heartbeat非模型链，14tokens/envelope7868，由原断言核验，原测试没有JSON导出。

进程内HTTP/JSDOM页面8例：119检查、143操作、895请求、189静态资源、9启动，资源全200；不称原生浏览器。9f版本独立冷进程补充探针1PASS仅证明cancel_intent后的原key重复恢复UNKNOWN/null、不重发/不退槽；子进程PID未记录、非Worker终态CANCELLED、仅delivery_graph_requests/runs全行前后相同，不归入新版339。

同SHA质量：fullsrc Ruff PASS、12个changed Python文件Ruff PASS、产品/夹具Node语法PASS。fullmypy FAIL仅status_report.py三条/tools.py两条既有错误，与原输出逐行相同，新增0；检查85源文件。作者曾新增的typing错误已修复并保留原输出，不归为基线。84模块精确资格pin `c48978cbcbd6b7d3b4c63c8a6911d1bb0298ab36b0dc5776d27c2c9b8a363ead`，candidate `3284f0bd3cb0f40a1e6cb87aa662ff2c4b99c621`；原ANCHOR_HASH/anchor bytes/CHANGED/来源/排除不扩，唯一AST literal zero64归一化。

独立只读审查已核实际接口/默认拒绝、合成账户与来源合同、namespace修复位置、84模块精确资格、质量、5ed14例独立探针及206原子写组v3/35例独立探针；完整339终态与最终成稿审查见证据内独审报告。先前静审漏掉namespace缺门已明确记录，不能用旧静审结论覆盖实际失败。

## 失败历史与证据分层

5ed完整批314PASS/4FAIL/0ERROR/SKIP，318全执行，pytest RC1；完整source494/copied/root/Git封印闭合，原始4份失败报告保留。Store七槽案例在cancel后才stop/join，正确的Heartbeat Run stopped误被收作失败；修正独立探针1PASS369.03秒，不与完整批拼合。P-B在Generate第三次准入时lease已过期约30.55秒，正确拒绝；此前只有2个Generate槽接受，Source/Cold未到。首个后台心跳错误未记录，UNKNOWN，不能猜作SQLite BUSY。typed[stop]/[deadline]两例在spec.advance准备阶段因lease过期退出，尚未注入各自fault；它们发生在独立诊断并行时段，但没有证据将CPU负载认定为原因。

正常隔离P-B原函数诊断1PASS479.56秒、七槽3+2+2均接受/KNOWN7000/envelope48354/六gap≥60，120条HB记录含16次code5 OperationalError/2DomainError；成功中的错误不推旧失败首因。该诊断缺自有执行前源码manifest和源码副本（NOT_RECORDED/NOT_EXPORTED），仅终态root494匹配原5ed封印，不能升级其证明边界。上述补充都不替换任何旧FAIL；其后各批独立记录，不合并317+1等结果。


47e批收集318后因实际cancel分支预期send1实际0而主动SIGINT一次；实际137PASS/1FAIL、138named、180未完成、1unnamed XML，pytest实际RC2，不能称318完整执行。494执行文件before/after/copied/root/Git在206集成前经独审闭合。此批公开观测直接记录同Run后台HB三次OperationalError真实sqlite_errorcode5，主HB总耗时28.329秒后Stale worker lease，无成功Run HB return；总调用未分段记录BEGIN获取和scope耗时，不能将28秒全称锁等待或CPU，也不倒推9f/2cb/5ed的缺记录首因。取消mutator尚未执行，无部分实例数据提交断言通过。新206与新增21例另列，绝不补计47e。

2cb完整批收集318后主动SIGINT以诊断首个失败，实际123PASS/1FAIL、194未完成，不称完整批。peer_lock预期发1实际0，mutator未执行；普通只读SQLAlchemy快照显示read_pick已VERIFIED而零Attempt、原Claim租约不变，不能沿用9f的零Operation。runner在无名中断XML条目上TypeError退出1，pytest子进程退出码未记录，不能倒推2。原始XML/streams/493文件before/after/copied/root/Git均保留；后续runner已先保存PROCESS_EXIT并支持unnamed条目。首版正常诊断setup缺父目录ERROR保留；第二版正常peer_lock诊断1PASS74.58秒，未复现历史发送前拒绝，不能据此认定根治。此后仅移除同事务严格重复guard。


首次完整9f64批：305PASS/1FAIL（306唯一，无SKIP/ERROR），完整保留。失败是原项目cancel用例预期发送1次而实际0，取消mutator尚未执行；原Claim后无Attempt/Operation，未持久化续租。历史精确原因仍UNKNOWN。原版同用例正常时钟诊断1PASS，不能倒推历史根治。可控FAULT_INJECTION在claim后冻结测试时钟、仅对旧分类增加31秒，原lease30/Run300不变：旧路由1FAIL；这是受控反例，不是31秒墙钟、真实性能或历史重现。

随后a6a8路由探针12PASS/1FAIL：篡改当前draft namespace为未知值仍模拟发送1次，独审初次静态未发现这一缺门，实际测试暴露后修复；旧is_job也走同一门，不归因为新路由独有绕过。所有stdout/XML及前后493文件封印保留。2cb9新版结果另列，不覆盖a6或9f。


| 历史或证据 | 准确范围 |
| --- | --- |
| 作者首轮collection ERROR | 新sparse工作树缺旧helper导入的archived gold；仅恢复既有小fixture。P-B改纯本地Recipe fixture。保留输出，不计产品PASS。 |
| gate草稿红3FAIL/21PASS | 同账号跨trial拆quota、31秒陈旧权益、sender后worker漂移。修双向映射/freshness/每次同事务worker核验。 |
| canonical红1FAIL | 更换整个注册表仍能给同账号换quota；修为固定intern-ai+account ID派生。 |
| anchor红1FAIL | 同keys改anchor值仍被资格读段接受；修原始anchor bytes SHA后再完整资格。 |
| PB scope红4FAIL/47PASS | 同trial key变software/auth/expires/stagekey旧证据仍接受；修三层完整trial+批准输入指纹及抽取锚。 |
| 作者最终115PASS | 新43+旧HTTP8+PBtyped64，同一作者组合实际43.28秒；临时精确资格对应作者字节，不能冒称根冻结318的结果，不与318累加。 |
| PB纯typed64 | 合成归档合同与默认/foreign resolver拒绝；不是实际Worker/真实DB来源。 |
| 8个bridge负测 | 明确SQLAlchemy-shaped合成行+独立budget.audit stub：MOCK、跨sourceRun、错approval、缺usage/wire/raw/providerRequest/account；不是完整Worker冷链。 |
| 6个usage保账例 | 经实际budget.settle验证损坏usage转受控拒收，已知当次settlement仍持久化、accepted=false/halted、不退槽；不等于完整P-B实际来源验证。 |

前批ce6三次领取与2dda accepted=false的确切历史首因仍UNKNOWN，bb287实际续租时间NOT_RECORDED；前批最终199通过不倒推根治。本轮不改写前批完整归档。

[证据索引](../evidence/production-admission-contract-20261015/README.md)提供作者失败/修复、冻结源码、collection/XML、stdout/stderr、全部源码前后/Git封印、质量、公开回执与独审。每次实际失败与每个SHA分开记录；无deselection或预算扩大。

## 未实现与NOT RUN

生产可信account→quota/真实权益与强制不可收费解析、受审网络sender、真实P-B数据库/供应商归档resolver和真实成功来源桥仍未实现/未注册；没有真实调用许可。真实账号/模型/费用、PG、干净Win11、原生浏览器、真实旧源码升级、人工语义、完整真实P-A/P-B、远端CI和部署NOT RUN。已知拒绝的浏览器/私有SQLUDF/barrier路径未调用。执行观察曾发生exec-server transport disconnected，恢复后原日志继续；附加读取/proc/1056363/cwd被文件系统PermissionError拒绝，该项即停止、未换路径读取，进程cwd核验NOT_VERIFIED。完整错误及两工作树495文件/Git恢复核验保留在TRANSPORT_RECOVERY_206.json；未调整权限或凭据。工程合同通过不关闭F1/F2/F3/R0/C0：整体NOT_ACCEPTED，dependency BLOCKED_UNKNOWN、owner PENDING、semantic UNKNOWN、formal publication false。
