# 授权行死锁与两个 DOM 热点 — 2026-10-08

冻结旧版 `0f11dcd6e4fcb6bbc004ea30e0e8cc154727c440`，继续新实例的独立分支
`dev/pg-phase-diagnostics-20261008`。本轮完成一项已证明的竞态修复：材料列表
先取得项目锁，再检查各资源的授权行。原实例及其未提交计划、阻塞日志未接触或复制；
main 和 dev/f1-foundation 未修改。

已有未跟踪目录仅含被动 Python/Node 采集器，没有先前热点运行结果。旧完整工程日志保留的
三次 deadlock，分别是 04:24:26.134、04:24:31.138、04:24:33.640 UTC，后端345/346，
同一 schema 的 grants FOR UPDATE。按原阶段报告累计估算，三次均位于 REPORT DOM call
时段；完整进程还有约3.823秒未分配框架开销。该历史日志没有绑定参数与 HTTP 请求映射，
因此其精确请求不能反推为事实。[核验结果](verification.json)保存时间估算与限制。

两个原始 DOM 用例没有注入、断言或预期授权行死锁。后台刷新每2.5秒读取材料，
catch 会将失败显示为后台不可用，但最终 DOM PASS 不要求每个后台请求成功。
本轮原始 REPORT DOM 自然运行实际复现了5次40P01与5个材料列表HTTP500，另一个
报告清单节点没有死锁。这证明同类错误是实际竞态，不属于预期授权拒绝。

具体循环是 `GET /api/projects/{pid}/resources` 已持有 CSV 授权行、等待 REPORT
来源授权行；同时 `POST …/delivery-graph/plans` 或 `GET …/delivery-graph/plans`
先检查 REPORT 来源、再在 PROJECT 扩展中检查 CSV，等待前者的 CSV 授权行。
旧版自然复现的资源请求编号64/70/90/97/169，对应图请求62/68/88/95/167，
实际后端98/99；参数与逐次查询时序见压缩的
[完整 Python 时序](baseline/python-timeline.jsonl.gz)、
[SQL/函数聚合](baseline/hotspot-groups.json.gz)及[分析](baseline/analysis.json)。
单次查询中的 grants.id 排序不能统一多资源遍历的锁顺序。

修复仅将 api.py:list_resources 的 `own_project` 改为已有 `lock_project`。
所有权谓词、双身份授权、过期/撤销过滤、返回字段、事务边界保持；未增加缓存、
重试或异常抑制。REPORT 读取本来先锁项目，现在两个路径会在取得授权行之前串行。
代价是同项目材料列表可能等待项目锁；本修复不保证系统所有路径均无死锁。

旧新均使用 Python3.12.14、相同锁定依赖、Node24.19.0/jsdom30.1.2，以及同一已缓存
PostgreSQL17.11镜像 `sha256:327daa8fae7178d61f93142f146b098467b345e10997b9eb79f63bd58e5c8f3c`。
各测量顺序运行在当前同一新实例，使用独立、一次启动的自有 localhost PG、原始 fixture
和相同被动采集语义；没有并行测试负载。每轮捕获启动日志、一次认证连接、源码前后散列、
JUnit、查询与 Node HTTP 时间，完成后核验只清理自有容器和卷。

|实际执行|结果|pytest进程墙钟秒|
|---|---|---:|
|旧版两个原始DOM节点|2PASS；REPORT内5次40P01/HTTP500|71.057|
|旧版四组受控并发回归|4FAIL；均记录真实40P01/HTTP500|19.667|
|修复版相同两个DOM节点|2PASS；40P01/HTTP500均0|68.384|
|修复版关联回归|91PASS，0FAIL，0SKIP|151.312|

旧四组失败是新增“项目先锁”期望在旧版实际失败的保留证据，没有修改断言把失败变为成功。
四组覆盖材料/图先启动及 plan POST/history GET。屏障在真实授权成功后持锁，记录不同物理
backend、pg_blocking_pids 和实际SQL；新版第二请求均先等待 projects FOR UPDATE，
尚未查询 grants，释放后双方取得200/201。观察器仅为自有测试事务设置7秒查询超时，
最终路径始终释放屏障；这些屏障用例不作为性能节省测量。

91项包括四组并发、新增CRUD角色材料列表过滤、原图服务、报告清单、同事务/后续请求
来源变更拒绝、原CSV DOM及所有权/撤销/过期负例。CRUD角色实际不是superuser、
不能建库/建角色/建schema；材料列表只发SELECT，外主体403，owner/runtime各自撤销或过期
均被过滤，恢复夹具后业务行与schema对象相同。原REPORT 29检查、报告清单49检查、
CSV 29检查以及全部原测试/驱动/网页/脚本/工作流字节保留。
默认仅收集验证1591节点=原1586节点逐项保留+新增5项；没有再次执行全量。
此前1559PASS/27SKIP仍绑定此前冻结源码，不冒充此次修复的完整验证。

原完整工程两个 call 34.903/27.150秒没有本次请求采集器，不能与新样本直接比较。
下表只比较本轮同采集方式的两个原始节点；各嵌套跨度和并行请求不能相加当墙钟。

|阶段或观察|REPORT图旧→新|报告清单旧→新|
|---|---:|---:|
|pytest setup 秒|0.338→0.310|0.171→0.245|
|pytest call 秒|32.686→29.401|36.595→37.427|
|pytest teardown 秒|0.016→0.013|0.014→0.014|
|Node全过程秒|30.607→27.713|36.258→37.139|
|Store.initialize 次数/秒|1/0.071→1/0.074|1/0.061→1/0.063|
|SQL cursor 次数/累计秒|51375/25.258→52536/24.216|68508/27.225→68496/30.803|

REPORT call 观察下降3.285秒，报告清单观察增加0.833秒；整体进程观察下降2.673秒。
死锁/错误消除有自然与受控重现支持；这些单对样本不足以证明普遍或稳定提速，
也没有证实总查询数量减少。采集开销没有单独量化，cursor不含fetch/commit/pool，
函数、SQL、请求累计时间互相重叠。

旧版报告清单27次历史读取累计12.058秒、18次inspect累计7.023秒，24次命名应用列表
累计7.469秒；6次MOCK worker HTTP合计约6.268秒，原7条MOCK wire断言保留。
14次promotion恢复请求是原故障/完整绑定检查的输入，不能删掉作为优化。
重复刷新与来源重验确实可见，但不是重复初始化。

旧版REPORT图8次历史读取累计9.805秒。16个普通图GET每请求调用load_family两次；
7个正常历史GET每请求调用7次load_family、其中REPORT load5次，含当前图、
同项目peer及scope job校验。`current → load_family → build → load_family`
重复调用有计数证据；报告preview也在7个正常请求中各执行两次load。
这些是下一候选调查点，尚未证明可安全复用。原同事务来源/封印/授权变更负例依赖
重新校验，本轮没有删校验、改轮询或延长预算。

[静态锁分析](static-deadlock-review.json)与
[独立修复复核](independent-fix-review.json)均保留。独审实际核对91项JUnit、新增五项、
不同backend的项目等待、CRUD角色结果、census与导出散列，结论无阻塞。
四轮前后 test schema/role/public表均0，所属容器/卷均已清理；退出137来自明确的
docker rm -f清理，清理前Running=true/OOMKilled=false。所有导出文件逐字节核验；
较大时序和聚合仅用gzip压缩，清单保存原始及压缩散列，原日志及原JUnit空白保留。
旧失败JUnit也包含原测试源码缩进，故代码/文档空白检查与原始log/XML分别核对。
新增测试运行时尚未跟踪，另存当前源码散列及修改时间先于关联运行的记录；
它不属于原283项散列清单，也不宣称已有新增文件的运行前散列。

可复算命令：`.venv/bin/python docs/evidence/engineering-pg-hotspots-20261008/verify.py`。
两节点阶段分析可用同目录 `analyze.py baseline|candidate目录`，兼容压缩数据。
采集器和一次启动控制器也在同目录；控制器运行会创建新的自有PG，仅在获授权诊断时使用。

本轮没有模型、外部业务调用、新CI或Windows/native运行。LIVE0/MOCK，
原Windows900/Edge240/Node150与NO_GO保持。稳定性能范围、系统其他锁路径及
当前源码完整原生成本仍未取得；原始工程缺口不因本轮局部Linux验证而关闭。
