# 连续 CSV 列修订：最小合同及风险只读设计

基线 `ce3fa86677cdaa58e076cc03e15a9b5414fd1e77`。只读源码/合同，root唯一仓库写者；本审未改仓库、执行测试/模型或旧业务链。本文件是设计评估，不签尚未冻结的实现。

## 可直接复用与最小新版本

接受root提出的新模块csv_column_revisions、`csv-column-revision.v2`显式namespace dispatcher。**共用原同instance/key的PREVIEW/CHECK/APPROVAL/JOB双seal日志空间可行，无须第二journal**：Preview/Reference等请求形状保持不变；value.namespace、ctx.contract、完整parent/source/version字段纳入previewFP，原CHECK/checkproof、JOB/event、Release snapshot与批准snapshotFP交叉锚定；未知namespace明确拒绝。并未找到在这些精确约束齐全时，仅通过局部重签能绕过校验的反例。

不能以新v2允许条件修改旧v1 effective/calculate、字典输出或指纹算法。load_preview在原pair校验后按冻结namespace分派；旧分支不补新字段。新namespace被剥离/伪装成v1，应被旧parent SOURCE禁令或旧重算结果拒绝；新增字段/规格修订不匹配也须被重构fp与独立接受锚定拒绝，不能捕获异常后fallback普通CSV。

`lifecycle.switch_preflight:542`现有pair(...PREVIEW,Preview)取context.limits可以保留：请求DTO相同、封存有效且新context保留limits，随后由validate_snapshot按namespace全验证。但pair的response含私有Goal/材料，**不是“公共seal数据”**；必须先经owned target→release_gate完成新父链及材料授权，不能先读payload再鉴权。

## 连续有效规格，三个版本轴分开

新context从当前已采用parent Release经 `csv_goal_revisions.bound(parent,current=False,snapshot=None)`取得已验证有效draft，不能再从parent.snapshot.draft（仍是原始rev1）重新套旧effective(1→2)。新增纯effective_next以parent有效manifest/action/binding的共同revision+1构造下一规格，保留原app/runtime、稳定ID、executor、data binding、dependency lock、输出/data schema及原生成来源。

至少独立冻结这些值：

- 业务instance iid、principal/project/app/runtime、当前instance revision、data_version。
- parent Release id/fingerprint、parent有效candidate fingerprint、parent规格revision。
- 原Goal card id/version/fingerprint/完整snapshot、拟采用Goal的同组字段及模式。
- 原材料id/hash/resource snapshots、当前graph/authorization/manual-lock基线、旧→新列、限制与新effective fingerprint。

sameGoal必须等于parent已生效Goal的version+fp+snapshot，且仍是当前Goal head；不PUT卡、不造Goal v3来包装规格rev3。nextGoal采用用户实际保存的同卡精确下一版/current head（有限方案建议只parentGoalVersion+1），材料refs/snapshots仍等parent与原材料。规格rev3、GoalCard可能仍v2、实例CAS可能revision3是三件事，显示、冻结、比较均不可互推。换列仍是显式结构化输入，数值oracle不升格为Goal语义接受；新Run人工声明独立PENDING。

baseline_column对连续层必须等parent有效单列enum；新列是同CSV另一数值列，不能任取“旧列”来伪造变更范围。

## 历史父链与当前新工作分离

当前层的新preview/CHECK/批准/运行/CAS校最新Goal head、graph/grant/实例等eligibility。**父Release、旧preview/CHECK/Run永远历史解析**：绑定原不可变Release、原Goal版本、旧封存与实际结果，不能要求父Goal仍是当前head。否则编辑到Goal v3时会误杀合法父Goal v2及所有旧结果读取。

父解析不跟随business instance当前Release指针；采用后其指针已指向child，沿它递归会形成伪循环。top CHECK的snapshot ref=P3时，解析parent R2必须用R2自身USE ref=P2，不能透传P3 snapshot给parent bound。

建议在读取任何私有preview/Goal/Release正文前先做scalar元数据walk：每层owned principal/project/app/runtime/原业务iid一致；收集涉及Goal版本的resource id并完成当前READ/SAVE授权；按Release ID visited和明确depth上限拒循环/超深/未知父引用，然后按历史顺序核不可变批准与Release、双seal、fp、CHECK实际链。不能先recursive read_release完整正文，再试图在更深层鉴权或限制深度。若优化重复证明，只能复用同call/connection/transaction/limits/owner及未写epoch下的证明，不能加全局可复用许可缓存。

## CHECK 创建必须保持私有受控

当前SOURCE普通create_instance被拒，应继续拒。仅在原CHECK控制器、已持项目锁的同事务中，load_preview(current=True)已验证精确新namespace、business iid、parent rid/fp、preview key/fp后，允许私有helper/keyword创建该parent Release的确定性CHECK实例。不得新增HTTP allow_source/force字段或通用bool旁路。创建、enqueue、CHECK接受双seal/JOB/event与role pin必须同事务，失败全部回滚。

除create_instance与bound(CHECK)外，`verify_job:364`现有SOURCE→purpose USE限制也要显式分派：仅新namespace、精确原CHECK接受的run/appRun/checkInstance、parent rid及有效候选一致时，才允许SOURCE上的CHECK；其他SOURCE CHECK继续拒绝。

**可达混淆反例**：受控CHECK实例自身持有parent SOURCE。用户能直接请求其revision context；若new.context仅判断“当前有SOURCE”，可能从隔离CHECK再派生新的业务连续修订。必须拒CHECK pins，并要求parent origin.reference.instance_id及全部父引用等于原business iid，而不是当前隔离iid。目录隐藏不足以代替这个API门。

## 需覆盖的既有接线

- app_jobs的Reference解析、load_preview与JOB封存：同kind可复用，但新namespace必须到新绑定/Goal规格解析，不能丢marker后落普通执行。
- validate_family、release_gate、job_gate、pins：保留原paired/event/Release marker的独立反剥离检查，SOURCE被删或namespace改写仍拒；common kind有助于沿用已有索引，不要只信新增单一marker。
- lifecycle的release read/commit、switch_preflight/switch_target与CAS：新SOURCE进入新validate_snapshot、当前层eligibility和原保留结果/兼容schema校验；原实例/Grant/runtime不增加。
- 原同步run_instance继续拒全部SOURCE，所有连续使用仍走原durable AppRun Worker。
- 页面创建下一轮必须是明确新intent，保留已采用/unknown历史及原句柄。既有确认重入修复的每view重验、清ack、当前signature、expiry、late/ABA和GET-only原key恢复不能在连续模式丢失。UI明确区分parent Release、规格revision、Goal版本和实例revision。

## 冻结后最低证明建议

用原NoModel CSV工具链完成：既有v1修订→同Goal列修订（卡version/行数不增、有效规格2→3）→用户实际保存下一Goal后再列修订（Goal2→3而规格3→4）。同一app/runtime/业务instance，原draft/生成来源/旧Release/旧Run及typed结果字节保留；各CHECK为独立受控实例，业务新Run用各自Release/输入/Goal/规格与新结果版本，人工声明不继承。

另需有限负例：CHECK实例当business source、外scope/非current parent、父fp/effectivefp/规格跳级、same/nextGoal漂移、父链损坏/循环/深度及撤权在正文前拒绝；不能因子层Goal head更新而破坏父历史读取。旧v1 golden形状/纯函数AST及旧完整功能回归应保留。具体执行范围待root冻结后确认，本设计不要求新模型、UDF/private诊断或旧恢复矩阵。

基线8源码hash：`/tmp/f2-csv-continuous-ce3-contract-design.json`，SHA256 `49c3d5935e4414716fa19160e61b2319312e86eab960631c8041525eaaa43368`。
