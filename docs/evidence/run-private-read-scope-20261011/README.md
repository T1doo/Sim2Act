# 共享调度私有读取范围：原结论纠正与修复

基线 `2b53572ded47f83d51898356dae0e99a97a61bc9`，原普通开发分支 `dev/project-column-revalidation-20261011`。这是共享 scheduler/claim 的证据纠正与代码修复，产品新增功能暂停。精确边界见 [实施前合同](../../F2/RunPrivateReadScope20261011.md)。最终作者1730唯一选定节点 **1664 PASS / 66 SKIP / 0 FAIL / 0 ERROR**，另2升级deselected；30串行页面全部PASS。原650精确恢复，401冻结代码和141原证据同字节。独立59检查另计，有限范围仍受末段NOT_RUN约束。

## 原结论撤回

原 `project-column-material-reuse-20261011/independent/data-free-sql-trace.json` SHA256 `b6a94215b5db5c719942affb5fd93a5d9f988a8c79fa2fd3957c808d478edbf8`，2829 条语句，0 基 1091 / 1097 是 `SELECT runs.id, runs.context, runs.result FROM runs`，无 WHERE / 空参数；相邻还有全表合同读取。旧探针只查旧 Run ID 是否在参数，漏检全表扫描。因此原整个 Worker「无旧内容读取」结论及相关 LIMITED PASS 不可签收。没有据此证明实际用户泄露或旧结果复用。原 trace、脚本、报告和全部 141 文件 byte/hash 保留，见 [基线逐文件清单](baseline.json)。

## 产品修复

只改 db.py / protocol_jobs.py / protocol_recovery.py / protocol_pool.py：强制显式 Run ID/候选集合，取消全库私有标记 oracle；claim 与 expiry 先 ID/状态/租约等元数据，queue 锁定精确 ID 后才载入该 Run 全行；恢复提交前仍重核 lease/status/fence；pool 先实际非 NULL Attempt Run IDs，再识别命名空间。Run marker 只返回候选 ID；完整合同仅对实际带 constraints 标记候选验证 fingerprint，且复核解码后的合法数组。job/event/context/result/contract 五种 anti-downgrade fallback 全保留，残缺协议不得普通 F1 续跑。

SQLite 重复 context/result 键中任一精确残存 namespace 保守停止；合同保持 Python 最后键的完整指纹与合法数组判定。普通 JSON 类型/后缀/嵌套伪标记不获得协议资格。所有候选逐批 256 绑定且不静默截断。PostgreSQL SQL 仅编译，运行仍 NOT_RUN。JSON 处理规则依据 [PostgreSQL 官方 JSON 类型说明](https://www.postgresql.org/docs/current/datatype-json.html) 和 [SQLite 官方 JSON 函数说明](https://www.sqlite.org/json1.html)；本轮不把文档或编译当成 PG 执行证据。

## 真实失败与阶段结果

所有原始 log/XML 保留，不累加为最终 PASS：

|阶段|实际结果|性质|
|---|---|---|
|red-first|9 PASS / 2 FAIL|claim 真实旧私有 cell 失败；material 夹具先注册目标导致旧来源失鲜 KeyError|
|red-second|9 PASS / 2 FAIL|原 2b 的 claim 和 data-free 实际 Worker 均被旧 context 求值屏障阻断；77 生产文件仍精确原字节|
|green|11 PASS|初次范围修复|
|expanded|62 PASS / 1 FAIL|F1 reserve 夹具误传 request_tools=[]，走协议分支|
|edge-red|0 PASS / 5 FAIL|NULL Attempt 及重复键三种漏标记、一种合同误标记，实际修前边界失败|
|expanded-green|67 PASS|上述生产边界修后|
|scope-final|70 PASS|增加真实旧 receipt/request、前置注释 CTE 和旧 internal 行保留；最终完整集合已再次跑全部70例，不重复累计|
|prerequisite-interrupted|未完成，保留各分片完整原始输出|实际 child 缺 editable Sim2Act；另两个 DOM deadline FAIL 单独未归因|
|supplement 修前|15 PASS / 15 SKIP / 2 FAIL|实际净化环境的 child 无 sim2act 包|
|supplement 修后|17 PASS / 15 SKIP|正规 editable 本地安装后，同源码同测试通过；PG 未运行|
|baseline-ui|1 PASS / 45.99s|实际 2b git archive 的旧 material/report 页面对照|
|current-ui-isolated|1 FAIL / 42.91s|同页面原 DOM wait 超时，完整串行同预算重验已PASS；完整原因仍未确定，不能自动当安装问题消失|

实际原表按行/列 UDF 屏障包含 runs.context/result/goal/resource_refs/error、run_contracts.snapshot、resources.content/hash、operations.receipt、operation_intents.request。元数据读允许；全表、IN、join、alias、subquery、CTE、aggregate、显式 main、同名保留 CTE/前置注释绕过都以真实访问失败校准。旧表未删除/改名，DML 保持原真实表/CAS 语义；屏障是 SQLite 测试 fault injection，不是通用 SQL 安全层。保护集之外的实际 pool 候选内 marker JSON 求值允许，另核 ID-only 返回和精确候选参数。

作者 actual data-free 路径在旧 CSV 撤权但物理保留、旧 Run/contract/operation/intents 仍保留时，目标 net=8.75/count3 通过实际三步 Worker，另确认新 Release/Instance；cold typed net=8.75 与 units=13，data_version2，旧 internal/资源/Run 行保持。原始证明及负例在 [scope-final-artifacts](scope-final-artifacts/)。

## 环境与执行边界

实际版本见 [environment.json](environment.json)。初次正规 uv 安装仅因默认 `/home/agent/.cache/uv` 为只读 EROFS 失败；保留完整 log，后明确使用可写 `/tmp` cache 安装到原 `.venv`，无扩大权限/凭据。源/测试既有字节均未改变，仅新增5个忽略的 editable metadata 文件。16:03 断连通知后 16:04:17 UTC 实际命令成功，HEAD/未提交/测试进程保全见 [disconnect-check.json](disconnect-check.json)，没有删除未知锁或新写入者。

全树 Ruff10 / mypy5 与实际 2b 源码逐诊断日志相同，改动 Ruff 通过。早期新 mypy 第6条类型注释错误已修，原日志保留。主回归恢复650精确节点并扩大75完整模块，另4补充模块；收集1698+32节点，2真实源码升级 deselected。所有源码/测试/scripts非pyc文件冻结，安装后401文件；四后端分片完成后串行原有 UI，未改任何测试预算或断言。[复现脚本](run_full.py)、[精确选择](selection.json)、collection/partition/JUnit 与 [实际终态汇总](final-summary.json) 是依据；这是完整选定关联范围，不是全仓/全部平台验收。

## 最终作者关联回归

|互不重复的终态集合|PASS|FAIL/ERROR|SKIP|实际说明|
|---|---:|---:|---:|---|
|四后端分片|1617|0/0|51|各417节点；全退出0；最长pytest1068.09秒|
|串行页面5模块|30|0/0|0|原budget/断言，pytest1168.79秒，1个既有TestClient依赖warning|
|补充4完整模块|17|0/0|15|正规editable安装后，pytest2.004秒|
|作者唯一合计1730|1664|0/0|66|main1698与supplement32无交集，两个collection与JUnit逐节点相等|
|其中原650（不再累计）|641|0/0|9|精确原node ID全部恢复，不以相同数量替代|

主完整执行进程墙钟2239.7957秒，分片时间不累计。最终66SKIP=63需实际PG、2需指定真实旧源码归档、1需原生Windows，逐节点理由见 [SKIP记录](final-skip-details.json)。另两个真实源码升级仍明确deselected。[汇总复核脚本](summarize_final.py) 已实际执行成功：1730节点唯一、650包含、401文件前后/当前、141原文件以及独审37/性能17原始与压缩SHA全部一致。最终逐节点结果 [final-node-outcomes.json](final-node-outcomes.json)，五个主JUnit及supplement.xml原字节留档。

先前并发/隔离材料页FAIL完整保留；最终serial的post/read病例与其余28例均在原预算通过，没有drop/retry wrapper/改断言。性能补充仅定位已有递归热点并排除样本路径的新namespace执行，页面超时完整原因未闭环，保留为已知预算余量风险，不宣称端到端提速或原生容量合格。本有限私有读取修复在实际最终选定范围未见剩余FAIL；不把一次串行PASS提升为全部产品/平台或历史超时因果结论。

## 新独审与冷读性能补充

同一冻结候选的 [独审](independent/FINAL_REVIEW.md) 为 **59 PASS / 0 FAIL / 0 SKIP，LIMITED PASS**，这些是独立检查而非 pytest 节点，不计入作者合计。16项真实 SQL 负例/普通 claim，39项五标记全部31非空组合/损坏 JSON，1项实际 pool，3项实际 Worker/cold typed/全列原行保持；独立目标 net=5.75/count3，冷 typed net=5.750/units18、data_version2。保护5旧Run/3旧资源，实际47862条SQL、5016次允许当前载荷求值，保护旧cell触发0。37份原证据完整 SHA 转移；31MB的 actual-worker-barrier 原 trace 使用 gzip 并在 [转移清单](independent/archive-transfer.json) 保留原/压缩 SHA 与长度。首次独审 freeze map 夹具 KeyError、0产品执行，原文件单独保留。

最终 [只读独审追加](independent-final/FINAL_ADDENDUM.md) 为 LIMITED FINAL EVIDENCE AUDIT PASS：独立重建六JUnit的1730唯一节点、650原子集、每文件声明统计与实际结果，核401当前/前后、141原证据、37+17归档原始/存储/解压SHA一致；5个UI模块和5个CJS与精确2b预算/断言同字节。原59检查未重跑/未改报告，不把作者运行改称独立运行。新增10文件与18终态证据SHA绑定，见 [manifest](independent-final/manifest.json) 和 [转移表](independent-final/archive-transfer.json)。该追加首轮最终dict/list报告格式TypeError只在/tmp脚本，原脚本/日志/分类保留，修格式后再次完整只读核对成功；不是产品FAIL或产品测试重跑。只读发现目录的错误路径及无关受保护平台目录拒读完整输出另存 [discovery-command-results.json](discovery-command-results.json)，已停止该扫描，没有重试受保护目录、改工具/路径绕过或扩权；未影响允许任务目录及产品核验。

[独审性能补充](independent-performance/PERFORMANCE_REVIEW.md) 对实际 current-ui-isolated 失败夹具做只读 SQLite backup，真实 TestClient 24 GET回复一致、原业务历史/fixture/401源码不变。三次普通6GET路径分别10.721/10.002/9.472秒，每次26995条SQL，新 protocol_run_ids调用/namespace SQL为0，四修改函数不在route profile。实例GET8.36–9.59秒；既有调用树重复load_plan100、read_release46、validate_binding148、graph.current132、authorize4224次，热点文件与2b同字节。该样本排除了此处新 namespace builder 执行，定位既有递归校验接近10秒DOM预算；没有证明原页面超时完整因果，也没有把历史FAIL变成PASS。原JS全局page计数跨代污染仅是假设，未实测。本次没有改缓存/产品/测试预算。六个原生pstats及完整SQL原SHA保留，[性能归档转移](independent-performance/archive-transfer.json) 可核压缩后解压一致；未复制fixture DB。

PG/应用角色、Windows/native/视觉、真实旧源码升级、真实模型/付费 API、完整 P-A/P-B/AT10、人工语义/owner、远端 CI、部署仍 NOT_RUN。SQLite + 实际 Worker + TestClient，以及仓库已有本地 loopback API/JSDOM 工程病例；没有重试已知被拒浏览器路径。mock wire 不等于模型验收，本轮无真实模型请求。main/coredev/原CSV分支不改、不强推。
