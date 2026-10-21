# accounted Run/Attempt 边界来源：只读独审

基线 `f51bbaae3f7f5bab64c79c4c135d0b0d3a2951c8`。结论：**可以证明部分来源和成功后局部字段的有限边界，不能把它们推广成完整Run18/Attempt13与原生RowMapping存储接受域的统一应用上界。** 这里的“无统一上界”不等于物理数据库可存无限字节；后端硬限制/解释器内存/整数解析限制没有被本项目固定成该合同，也不能用当前夹具大小代替。

## 真实写入口与列定义

`src/sim2act/db.py:95` 定义Run18列，`:178`定义Attempt13列。String没有length参数，JSON没有CHECK大小/节点/深度约束；所有相关JSON读写默认由SQLAlchemy序列化/解码。全src静态AST识别65个直接insert/update(...).values站点，逐项文件/行号/函数/列名及**values已存WRITER-INVENTORY.json。它是源码站点清单，不是外部SQL写者枚举。

Run插入共五处：db.py:1072 Store.submit_tx；app_jobs.py:369 enqueue；csv_dag.py:383 enqueue_tx；local_record_apps.py:899 confirm；protocol_jobs.py:733 enqueue。Attempt唯一插入为worker.py:258 Worker.reserve。另Run更新42处、Attempt更新17处。当前PB Generate沿Store.submit_tx，Source沿app_jobs.enqueue，Attempt都沿Worker.reserve，不可把其它通用写入口的接受域自动改成PB专属域。

| Run列 | 正常来源/边界与缺口 |
| --- | --- |
| id | submit等new_id("run")，固定run_+32hex；DB String本身不校验 |
| project_id/principal_id/runtime_id | 从当前owned project/instance取得，正常ID由new_id产生；列无长度/外键域CHECK，不能单凭String型证明其来源 |
| goal | HTTP RunInput和GoalSpec≤4000字符；Store构造FrozenRunContract时校验；其它固定family沿其合同；不推出所有JSON叶都同上限 |
| resource_refs | HTTP/GoalSpec≤8；PB完整门要求单一原resource；列表元素的ID格式和当前资源由另外授权门核实，列本身JSON无限制 |
| status | 正常各writer固定状态；Worker.finish的state参数/列本身不是数据库enum或长度CHECK |
| request_key | HTTP RunInput≤100、PB KEY≤100；Store.submit_tx没有同级长度门，内部internal:+app_run_id是另一固定来源 |
| fingerprint | 正常fingerprint生成64hex；列本身无pattern |
| created_at/lease_until | 正常time.time及原期限计算；PB run门校验finite/顺序；Float列自身无应用有限值CHECK |
| fence/version | 正常递增，部分DTO仅ge=1；没有应用统一上限。DB Integer位宽限制与Python/伪造Row里的任意int域不同 |
| worker_id | Worker.__init__ worker.py47 new_id("worker")；Store.claim db.py1355直接取worker_id实参，PB RunCheck另以KEY约束 |
| context | 初始固定计数，reserve/checkpoint/repair/dispatch再更新；worker.py346-351 checkpoint只合并tools便保存整个context，无全局大小/深度/额外键门 |
| result/error | 多family终态专属guard存在；普通Worker.finish worker.py353-448可透传通用JSON。DomainError.public errors.py10-28无message/code/submission_rejection大小上限 |
| cancel_intent | Boolean、正常固定True/False写；不是其它列有界的证据 |

| Attempt列 | 正常来源/边界与缺口 |
| --- | --- |
| id/run_id | reserve new_id("attempt")及当前Run；列String无格式门 |
| created_at/elapsed | time.time/monotonic差；列Float无统一finite/大小CHECK，迟到接收仍会保存事实 |
| mode/request_model | 正常MOCK/LIVE和settings.model；PB/Frozen合同为intern-s2，Settings.from_env另验证；dataclass构造本身无同级模型长度校验 |
| response_model | 直接raw.get("model")写入；通用mock分支没有全raw包络或model长度门 |
| status | 固定writer状态，列本身无enum/长度CHECK |
| usage | normalize_usage model.py125-139只取三个非负int并比较总和，无位数上限；成功PB再被checked_usage/accepted slot收窄 |
| reserved_tokens | reserve由wire长度+max_output；成功PB≤32768+1024，按run总≤64000；不是任意历史/拒绝/直接SQL行接受域的全局保证 |
| parameters | reserve固定顶层初值；worker.py335-344保留整个原dict再加model_identity；generation/activation等再合并字段。无通用递归schema或额外key总量门 |
| response | Generate接收安全msg≤16384 UTF8 JSON，另params原canonical≤32768 ASCII；Source response为canonical原串+evidence；通用parse_response仅限制content/calls局部，不涵盖所有Attempt列 |
| error | 常写DomainError.code；类型为String，code构造没有全局长度限制 |

## 哪些有限界确有来源

`natural_live_admission.py:50-64` TrialCaps固定Generate3/Source2/Cold2/总7、wire32768、responseASCII32768、每run预留64000/总192000/output7168、run≤300/lease30。`production_trial_policy.py:200-229`完成ledger验证后还约束slots≤7、每stage预留及accepted总tokens≤wire+1024。它们是已完成原门后的事实，不能提前代替全行验证。

`pa_trial_dispatch.py:1591`先select(attempts).mappings().all()，`:1592`才要求3或2，`:1595`选完整Run。成功accounted family一Run+3/2 Attempt及同数chains、Source两个ns_reads确有有限外形；失败前的查询/物化不能用后置count门声称已经有界。

`contracts.py:397-433` strict_json确有调用方max_bytes、depth≤20、重复key/非finite拒绝。Generate原archive由goal_applications.py:68-82 canonical ASCII≤32768，`:594-605`复核strict_json32768与完整回执；接收`:1634-1655`安全msg≤16384。Source请求/响应经pa_trial_dispatch.py:1540-1559原字节/strict_json及canonical门。真实被这些门约束的parsed JSON可推导与包络线性相关的粗节点/叶字节界，但不能转给整个Run.context/result/error或Attempt.parameters未知额外值。

Source context在natural_spec_runtime.py:927-954有exact key集合（7个基础键+可能关联marker）、计数与messages绑定门；Generate `_check_counters_from_facts` goal_applications.py:1928-1947核四计数但没有exact ctx keys集合。同样不宜把Source特例推广给Generate/所有行。

## 纯源码反例（均未执行）

- **STORE_KEY** `src/sim2act/db.py:966→1072`：Call existing Store.submit/submit_tx with normal owned project, goal and refs but key="k"*N. HTTP RunInput max100 is absent at Store entry; request_key is stored directly. 范围：Actual Store/SQL accepted-domain counterexample, not a claim PB KEY100 accepts it.

- **CONTEXT** `src/sim2act/worker.py:346-351`：Existing checkpoint accepts context containing required counters/messages plus an arbitrarily large/deep JSON extra and only merges tools before updating runs.context. 范围：Worker helper/database write domain; strict Source ctx later rejects extra keys, so not an accepted-full-Source claim.

- **RESULT_ERROR** `src/sim2act/worker.py:353-448;src/sim2act/errors.py:10-28`：Ordinary non-special mock finalization can receive result/error JSON or a DomainError message/code with arbitrary length; helper/schema has no uniform container/length gate. 范围：Generic row/helper domain; specialized generation/CSV/success/authority checks must not be bypassed.

- **MOCK_MODEL_NAME** `src/sim2act/model.py:22-44,48-122;src/sim2act/worker.py:335-344,724-746`：Existing general synthetic model returns valid assistant content="ok" plus raw.model="X"*N. Parse_response bounds content, not raw.model; enforced=False does not reject the name. Actual update stores response_model and model_identity.raw_returned_model. 范围：Ordinary mock writer path, not a real model run or a passing PB archive/identity claim.

- **USAGE_INTEGER** `src/sim2act/model.py:125-139`：normalize_usage accepts arbitrary nonnegative Python ints and only verifies additive identity; no bit_length/digit bound at this leaf. 范围：Normalizer accepted domain; later successful PB ledger/checked_usage narrows numbers.

- **ROW_HIDDEN** `sqlalchemy/cyextension/resultproxy.pyx:14-24;src/sim2act/natural_spec_runtime.py:1680-1710`：Construct exact native RowMapping(parent18keys,None,index,tuple18values+(hugeJSON,)). Constructor preserves entire tuple without length==keys check; storage validator checks known positions then serializes all _data, including last invisible value. 范围：Native RowMapping/legacy codec accepted storage shape; genuine exact select(runs) alone does not generate this extra position.

- **ROW_SAFE_INDEX** `sqlalchemy/cyextension/resultproxy.pyx:14-24;src/sim2act/natural_spec_runtime.py:1696-1709`：Add arbitrarily many/long string aliases mapped to valid position0 in native _key_to_index; visible keys remain18/13, but current codec reconstructs and retains all safe string index entries. Foreign keys are ignored semantically but still iterated. 范围：Native legacy row-storage accepted shape, not genuine exact select metadata provenance.

这些反例有意区分“Store/DB/原生Row接受”与“成功完整PB lineage”。没有声称大model名或额外Source ctx能通过PB原identity/context门，也没有提出篡改、续租或重签旧库。

## 原生RowMapping hidden storage来源

安装源码 `sqlalchemy/engine/cursor.py:1552-1565`将DBAPI raw row传给Row与column processors；`cyextension/resultproxy.pyx:14-24`与纯Pythonfallback`engine/_py_row.py:39-66`只保留parent/index及处理后的tuple。`engine/row.py:171`将同一parent/index/data交给RowMapping。它不验证keys/data长度相等，也不验证必须来自某一SQL。RowMapping迭代keys与_values_impl/len使用完整_data的差异见row.py:363-381。

因此，本次原固定select(runs)/select(attempts)自然产物确为18/13位置，没有join额外列；但exact RowMapping类型不是该来源证明。构造器/恢复路径允许额外_data，安全字符串索引别名也可超出可见_keys。`natural_spec_runtime.py:1680-1710`明确保留全部原_data及所有str/quoted_name有效索引，不能只投影业务键而丢hidden位置。foreign Column/其它对象键虽不进入安全payload，原dict迭代仍有其线性成本。`cold_accounted.py:718-728`验证visible字段集合但保留raw sidecar，故18/13 visible gate不消除hidden成本。

SQLAlchemy JSON处理器 `sql/sqltypes.py:2805-2820`默认json.dumps/json.loads，没有调用本项目strict_json。DBAPI与JSON解码发生在计量器收到RowMapping之前，所以后置流式计量器只能界定自身复制/编码成本，不能宣称已封闭查询/JSON解码内存。另 `_cold_graph_row_storage`先构造完整lookup，`_capture.row`又构造names tuple/set、visible dict与sidecar；若先调用这些再检查packet上界，也没有限制这些前置自身分配。

结论供主线程分流：可以用小而明确的工作预算选择有界owned快路；对来源未证或超界值保留原legacy完整字节/guard语义，不能新增全局硬拒绝、裁剪未知字段/hidden数据、忽略字符串索引，也不能把digest或既有身份当授权。若要把全DB/Store域真正改成统一大小schema，属于另行合同/迁移任务，本次未授权实施。

本人仅文件读取/AST/哈希，未导入产品、未开DB、未运行Worker/Mock/G0/PB/测试，未新增产品writer；只写/tmp报告。当前父侧新增scripts/diagnostics/cold_accounted_size.py未由本报告审核或运行。完整源码SHA及反例分类见BOUNDS-REVIEW.json。
