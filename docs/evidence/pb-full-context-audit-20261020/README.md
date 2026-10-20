# 原完整 PB 执行上下文及新窗口判断：只读对账

基线 `279609678406250fec942cfe3e33c3d7e98144ea`。本轮只读源码、Git字节及封存tar/JSON/日志，没有PB、producer、pytest、Worker、模型、数据库打开或权限写入，不恢复任何窗口、不修改产品/测试。

## 当前判断

**现在不能执行：本轮明确只授权对账、禁止PB；此前那次完整Mock窗口已消费，不能继承为重跑权。** 但永久取消的旧窗口与此服务器完整节点是不同目标，不需要、也不得为执行后者恢复前者。

若父侧另行明确批准“当前冻结源码、下列唯一节点、全新隔离SQLite、一次最多1200秒的原完整Mock验收”，并满足下面的开跑前隔离/收尾条件，源码核查未发现还需要真实模型、账户凭据、PG账号、主机安全权限或产品改动的前置条件。它将是**当前执行上下文的新有限Mock验收**，不是原37.279秒因果复现，不保证通过，也不能据此关闭真实模型/语义或全平台资格。

唯一目标：`tests/test_pb_spec_production_controller.py::test_pb_production_original_source_extraction_explicit_use_and_cold`。不代跑、改名或夹带旧安装竞态、恢复/负例矩阵。当前任务没有创建可执行新runner或启动任何测试。

## 永久取消的准确对象

[原取消记录](../pb-exact-install-window-20261012/cancellation-20261012.json)在2026-10-12T10:16:43Z记载用户永久取消：`Old/new precise candidate installation digest concurrency comparison`，状态 `CANCELLED_PERMANENTLY_UNVERIFIED`，禁止改名、换框架/agent/tool/环境替代重试。对应[原平台拒绝](../pb-exact-install-window-20261012/current-rejection.json)针对 `/root/pa_independent_review` 的精确旧/新JS双actor安装digest对照。旧两trace的latest_reads=0，只发生较早supersession拒绝；相关动态验收推论已被撤回，不补签。

该窗口要求原key首个latest200→精确候选GET和真实digest→第二actor prepare201→最后latest409，并对比旧/新JS安装结果。指定服务器节点没有浏览器安装digest、第二actor并发prepare或旧/新JS对照；它测试API→正常Worker→G3/Source2→原正文提取→明确per-use→冷Store/Worker→Cold2/七槽账链。产品内部的合成trial批准/撤权记录，和用户撤销这项测试授权，是两个不同概念；不能把旧取消笼统称为“所有PB被撤销”。

## 原完整失败的实际计时和负载证据

| 原封存观测 | 实际值/边界 |
| --- | --- |
| 完整pytest / 外层wall | 621.90 / 634.128503秒，exit1，非timeout |
| 整进程CPU | 未记录；不能用局部thread CPU当总CPU |
| G0 wall / thread CPU | 37.521112 / 37.481985秒，差0.039127秒，threadCPU/wall约99.90% |
| 首binding wall / thread CPU | 37.279449 / 37.240321秒，差0.039128秒 |
| 原G0路径 | 3030 SELECT、2048 check、2183 input_key；有真实合成Cold Attempt/响应结算上下文 |
| 原heartbeat | 91次返回、11次错误，其中10次sqlite_errorcode=5；原tx BEGIN IMMEDIATE栈在日志内 |
| 原guard错误 | 2次；前一次已SUCCEEDED/lease0的尾心跳拒绝，不能冒充Cold失败；后一次RUNNING/fence1/lease1792458659.1644099，01:11:07.703313Z记录Stale worker lease |
| faulthandler | test300秒的一份主线程Source/sender_guard堆栈与等待心跳线程；不是G0采样，不是外层timeout |
| 完整G0 input原bytes / 逐条有序SQL参数 | 原full档未保存该状态输入与逐条SQL，只存聚合指标/模型wire正文；不能拿后来的dormant原件倒填 |
| 同机进程、loadavg、CPU型号/配额/频率、cgroup统计 | 原完整runner/receipt均未采集，无可用同步负载记录 |
| sys.gettrace/getprofile/tracemalloc状态及trace独立成本 | 原完整runner未采集；命令无trace/cProfile参数，autoload禁用，只显式原成本observer和pytest内建插件；不据此反推所有hook必为零 |

按 [Python thread_time 官方定义](https://docs.python.org/3.12/library/time.html#time.thread_time)，该时钟统计本线程用户态与系统态CPU、不计sleep。结合这些原数据，支持“G0主要消耗该线程CPU，原30秒租约正确拒绝”；不支持把这37秒主要归给墙钟排队/抢占。heartbeat BUSY证明原过程存在SQLite写锁竞争，不能凭错误总数把它全部归给G0，也不能量化其对首binding CPU的贡献。CPU频率/机器差异、其他trace成本及完整上下文差异没有因果隔离证据，因此不能宣布具体根因或再改产品。

原执行时HEAD实际是 `dc34ce4b1311810e27cd33a0cd156b6f84333666` 加13份未提交产品候选及新增测试；本轮逐一核原receipt捕获的715份输入，全部与后来封存提交 `f9dfcf319b1a5bd66246aaa07a4dd0a082d1bd98` 字节相同。不能只按旧HEAD忽略当时工作树。原runner SHA `5d0d59bf6eec7d0120dcbe4fc25e199d6a4538f6e76afb95294554e89f53cb3b`，原observer `2209e9a71be5341cdac68abf314c991a51262a7ee61c5079ee87d3f7fdcc6c67`。

[最新唯一observer对照](../pb-cold-observer-pair-20261020/README.md)只有同一dormant夹具的3.866→3.797秒结果。原G0与dormant不同：原完整库1531904字节且Cold已RUNNING并有响应/Attempt；dormant闭库1142784字节、Cold QUEUED/fence0/无Attempt，使用未批synthetic pin，直接producer绕开整个_model_before上下文。dormant producer2814 SELECT、2028 check、2158 key，不同于整个原G0。两臂自身可比不能使它和原整链变得可比；该有限候选已否定，不再探针或堆微优化。

## 当前节点的真实行为范围

当前主测试及configured/setup/frozen/Mock helper与f9原字节相同；conftest随后新增PG环境选择分支，故必须显式隔离。现在`SIM2ACT_TEST_DATABASE_URL`、`SIM2ACT_RECORD_PG_CONFIG`、`PYTEST_ADDOPTS`、`PYTEST_PLUGINS`均未设置，但将来仍须重新核查。

- 不是DB零写测试。`env`新建test_only SQLite、两个synthetic用户、项目/runtime、材料与Goal；`frozen`给该夹具runtime本项目artifact.save_text Grant；原Worker/控制器正常写Runs/Attempts/Operations、资源/typed结果、批准与journal/配额/关联/事件。数据范围限本次全新fixture DB和tmp目录。
- 另有原测试内置四个隔离备份库`generation_marker/ns_provenance/trial_provenance/ns_body`，分别故意损坏合成归档边界作拒绝核验；不是旧双actor安装窗口，不增加为新矩阵。
- `configured`在该进程内令settings.mode=live/live_enabled=true，替换`controller.environment`、`evidence.resolve_account`与`admission._qualified`为精确合成fixture；token为字面占位符`isolated-noncredential-placeholder`，不读取dotenv或真实provider token。此test-only替换不授予生产资格，不得复制到服务配置。
- `no_real_http`阻断httpx真实同步/异步HTTPTransport；fixture AsyncClient强制精确MockTransport，factory接收有限合成响应。正常预期7次Mock（3/2/2），真实模型0。原失效运行实际只有6次，不把预期7当已发生。
- 原限制保留：trial TTL1800秒、每Run300秒、lease30秒、RPM1（相邻请求≥60秒）、7槽/输出7168/总预留192000/单wire32768/paid_cap0。全新批准、stage批准和当前源权限均由原fixture正常产生；不恢复旧expired/revoked记录，不改真实时钟。

## 父侧若选择新窗口：最小明确条件与清理

1. 建议新唯一目录`/tmp/sim2act-pb-full-current-once-20261020`（本轮只查不存在，未创建）。对当前精确Git/source/test/原observer及该新独占输出目录给**一次**明确新Mock授权，唯一上述节点；已消费窗口和永久取消目标均不继承。禁止自动重试、恢复旧Run或失败后换参数。全新SQLite、无生产URL/旧库，清掉两个数据库选择变量及PYTEST_PLUGINS/PYTEST_ADDOPTS，保留禁autoload、真实HTTP阻断和Mock身份断言。
2. 原observer整包和原产品guard不删改；保持原1200秒外层上限、300秒faulthandler（不是额外执行预算）、1800/300/30/60所有产品期限。最多7个Mock槽、真实模型0；不装LIVE source、不建PG角色、不请求新凭据/权限或部署。
3. 同一writer下避免并行测试/压缩等可控额外负载；仅在开跑前/后记录解释器/依赖、硬件/cgroup配额、loadavg、本人进程/线程累计CPU及退出码，原observer保留。它们是新验收上下文记录，不补造旧负载，也不另开性能探针。开跑前冻结全部输入hash，结束核零漂移。
4. 只在新目录存fixture DB、四备份、JSONL、JUnit、stdout/stderr与原observer；旧完整节点原件实际总7268492字节，建议父侧预留独立64MiB临时/封存空间并先核可用量，不用假容量探针替代。磁盘不足或超时即停止，不删除旧证据腾空间重试。
5. 外层只管理本次新进程组，超时先TERM、5秒后KILL、再5秒确认退出；记录不确定结果再处理，绝不按进程名杀旧服务。收尾关闭client/Store/heartbeat，核本次子进程全结束；先保全DB/原件及hash，再清理本次可重建临时副本，不删旧证据或任何他人数据库。无PG清理/系统权限动作。

以上是父侧可集中批准的具体条件，不是本轮已批准或已执行命令。即使新Mock通过，也只签冻结当前上下文，原G0失败和W5/G1/finalguard未到达的历史保持。

## 独立产品剩余项：只列原计划真实缺口

仅列原F2-T03/AT10–11的**既有read→two sums应用改用另一份已有授权单CSV**：`csv_material_reuse.py`明确拒绝`TWO_SUM_VERSION`，现`csv_dag_instances.py`只支持原材料上的逐节点columns。原[双求和范围](../../F2/CsvTwoSumInstances20261011.md)已说明新材料复用拒绝。可选同项目已有读授权目标，无需G0、真实模型或新权限种类；正常结果的派生READ仍按原合同记账。后续仍需冻结双列material intent及两结果schema、独立Fraction oracle/旧历史保持/冷新Run和必要旧单列回归。没有本轮实施或新增授权，不把“第二次更正”等未规定次数扩展包装为需求；记录采纳已交付，不重复列缺口。

原件索引见`audit.json`与`MANIFEST.json`；独立取消边界/原计划缺口复核在`independent-review`，审查者也未执行PB、测试或数据库。当前无产品修复结论。
