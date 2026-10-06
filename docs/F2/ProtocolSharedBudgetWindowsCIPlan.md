# 共享预算切片：既有 Windows CI 交付门

2026-10-06 后续父授权：普通 push 既有 dev/f1-foundation 并监测一次原标准 Windows CI 至终态。源工程本地7f4ae4f；远端9141fa6为祖先。保持 workflow/runner/权限/helper/超时/上传八文件范围，不新增 LIVE、业务外发或部署，不提升真实模型语义/完整P-B/F1/Win11/AT02。

PG口径：tests/conftest.py env 从 SIM2ACT_TEST_DATABASE_URL 建独立PG schema并显式 initialize；HTTP/reviews/recovery及concurrency继承该env。tests/test_protocol_jobs.py局部env现同样接该URL；pool别名、process别名和独立冷child继承同一PG地址/schema。runtime_role来自公共env，临时NOSUPERUSER/NOCREATEDB/NOCREATEROLE、schema USAGE与表SELECT/INSERT/UPDATE/DELETE，DDL负例。Windows原Test阶段仅该进程读私有owner.env，runtime/浏览器仍业务role；原Setup先显式migration再GRANT既有角色CRUD，不由API建表。

仍SQLite：test_protocol_schema::test_api_construction_never_creates_protocol_tables；pool::test_explicit_default_pool_zero_live_and_offline_and_no_reset、test_controller_genesis_prevents_coherent_zero_to_fourteen_raise。scripts/agent-ui/fixture.py固定SQLite，旧agent/registered HTTP DOM和nativeUI fixture都不能叫PG。model_budget fixture只Settings(sqlite://)用于MockProvider/sidecar，无PG Store；model_protocol为纯协议/Mock单测。固定合成回复/gold不等于真实模型语义。

同源775 collected：ci-collection-inventory.json记录有PG-selecting fixture的661项，其余114不走该公共/jobs PG fixture；这是静态路由清单，不能把774全量PASS当774真实PG。上一轮131口径明确91PG40SQLite，原报告保留。

验收：检查CI head SHA和原workflow；工程全量终态及平台SKIP；显式迁移/新pool表受限角色CRUD与禁止DDL、共享budget、末槽/五崩溃点、三Run锁序用例在Windows工程门中的状态。原 -q 不输出JUnit逐case明细，若只能用同源收集顺序对应进度字符，会如实注明该定位方法，不假称JUnit独立明细。旧Edge38/agent33/registered29原受保护浏览器覆盖保留，新增protocol/recover HTTP没有新原生UI验收，JSdom optional平台skip单列。Report/Cleanup和原上传范围须终态检查；CI失败先复现有界修复，不自动扩scope或无限重跑。

本文件为实施前计划，不预写CI成功。push后确切sourceSHA、run/job URL、backend路由、关键用例和cleanup另存证据。LIVE总预算0。
