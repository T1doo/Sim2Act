# 共享预算切片：既有 Windows CI 交付门

2026-10-06 后续父授权：普通 push 既有 dev/f1-foundation 并监测一次原标准 Windows CI 至终态。源工程本地7f4ae4f；远端9141fa6为祖先。保持 workflow/runner/权限/helper/超时/上传八文件范围，不新增 LIVE、业务外发或部署，不提升真实模型语义/完整P-B/F1/Win11/AT02。

PG口径：tests/conftest.py env 从 SIM2ACT_TEST_DATABASE_URL 建独立PG schema并显式 initialize；HTTP/reviews/recovery及concurrency继承该env。tests/test_protocol_jobs.py局部env现同样接该URL；pool别名、process别名和独立冷child继承同一PG地址/schema。runtime_role来自公共env，临时NOSUPERUSER/NOCREATEDB/NOCREATEROLE、schema USAGE与表SELECT/INSERT/UPDATE/DELETE，DDL负例。Windows原Test阶段仅该进程读私有owner.env，runtime/浏览器仍业务role；原Setup先显式migration再GRANT既有角色CRUD，不由API建表。

仍SQLite：test_protocol_schema::test_api_construction_never_creates_protocol_tables；pool::test_explicit_default_pool_zero_live_and_offline_and_no_reset、test_controller_genesis_prevents_coherent_zero_to_fourteen_raise。scripts/agent-ui/fixture.py及scripts/windows_browser_ci.py均固定SQLite，旧Edge/agent/registered原生浏览器fixture和两个registered_generation_native_dom模式不能叫PG。旧test_registered_run_generation_http::test_real_http_dom_generation_entry_and_lost_receipt继承公共PG fixture，本次在Node/jsdom前置检查时SKIP，不能声称实际DOM在PG通过。model_budget fixture只Settings(sqlite://)用于MockProvider/sidecar，无PG Store；model_protocol为纯协议/Mock单测。固定合成回复/gold不等于真实模型语义。

同源775 collected：ci-collection-inventory.json记录有PG-selecting fixture的661项，其余114不走该公共/jobs PG fixture；这是静态路由清单，不能把774全量PASS当774真实PG。上一轮131口径明确91PG40SQLite，原报告保留。

验收：检查CI head SHA和原workflow；工程全量终态及平台SKIP；显式迁移/新pool表受限角色CRUD与禁止DDL、共享budget、末槽/五崩溃点、三Run锁序用例在Windows工程门中的状态。原 -q 不输出JUnit逐case明细，若只能用同源收集顺序对应进度字符，会如实注明该定位方法，不假称JUnit独立明细。旧Edge38/agent33/registered29原受保护浏览器覆盖保留，新增protocol/recover HTTP没有新原生UI验收，JSdom optional平台skip单列。Report/Cleanup和原上传范围须终态检查；CI失败先复现有界修复，不自动扩scope或无限重跑。

本文件为实施前计划，不预写CI成功。push后确切sourceSHA、run/job URL、backend路由、关键用例和cleanup另存证据。LIVE总预算0。


2026-10-06 本次唯一授权标准CI闭合：精确source **b6c8acd450e51a8c1da6df735b9f03e73063608a**，run [37502853220](https://github.com/T1doo/Sim2Act/actions/runs/37502853220)/job [112403984046](https://github.com/T1doo/Sim2Act/actions/runs/37502853220/job/112403984046) **SUCCESS**。原Windows Server2025 job10m24秒；Ruff、mypy31、Setup显式PG迁移、最小role smoke、工程、旧受保护浏览器、Report/Cleanup全部成功。工程 **772 PASS / 3 SKIP / 0 FAIL / 0 ERROR**，775 collected，460.50秒。

逐项实际后端：同源收集顺序对应原-q进度、总数与JUnit Report一致，非单独JUnit逐case下载。公共/jobs及派生PG fixture为660PASS1SKIP（661路由项），另112PASS2SKIP（114其他）；不把772统称真实PG。协议关键9模块小计167PASS，其中145使用PG fixture，19是模型provider/文件账（无PG）、3是显式SQLite（pool默认/Genesis2、API无DDL1）。HTTP25/jobs39/reviews39/recovery14/pool19PG/process6PG/三Runconcurrency1PG/role2PG均PASS；pool模块21另外2SQLite，schema3另外1SQLite。新pool/slot和job/review既有非superuser业务role CRUD与DDL拒绝真实PG通过；6跨进程末槽+五崩溃点及永久三Run锁序Windows全部通过。19预算file-lock/Mock单测在Windows执行，含实际msvcrt非阻塞竞争，未忽略类型或削弱锁。

三项SKIP分别为registered_generation_native_dom正常/受控时序两个SQLite seed项，以及registered_run_generation_http lost receipt的公共PG fixture DOM项；可选Node/jsdom前置，未从原-q/Report单独取得具体skip reason，不虚构安装状态。真实受保护Edge38、agent33、registeredGeneration29均PASS，无unexpected console/pageerror，实际renderer AppContainer/restricted token审计PASS，原helper/SDK/权限/超时/上传八名称范围未变。原命名JSON/PNG六个存在输出按stdout chunks字节/SHA/2MB核验（failure文件成功时不存在）；PNG未额外写入或发布，视觉审查保持NOT_REVIEWED，不把hash等同像素可见验收。上述browser fixture仍SQLite，原覆盖不替代新protocol/recover原生UI，后者NOT_RUN。

清理：原owned API/worker stopped、temporary PG server stopped、Cleanup SUCCESS和原JobRoot删除正常完成，浏览器helper正常结束其owned API finally；Windows残schema/role未额外计数，不伪称实测0。推前真实临时clone已删，无本地新PG/运行服务。前两CI37499515105/37500554573失败记录、误判普通attrs LF的本地verifier修正、全量与fixture口径更正全部保留。gold/PINS原bytes与篡改拒绝不变。真实模型请求0，LIVE总预算0；完整P-B、真实语义、generic continuation、正式Release/F1/Win11/完整AT02不提升。证据见windows-ci-third-result.json、case-map、browser-summary及third-real-checkout。最后只追加docs证据提交，不改成功source实现。

2026-10-06 0389后续唯一授权标准CI结果：900 collected / 895 PASS / 5 SKIP，protocol/recover原生Edge26检查及六PNG实际查看已闭合；冻结job实际15分钟，未修改为父描述25。逐项q-order方法、SQLite浏览器口径、安全token检查、未测边界和cleanup见 [精确终态证据](../evidence/windows-protocol-native-0389-20261006/README.md)。本次后续仅本地文档，不追加push/CI或生产激活。
