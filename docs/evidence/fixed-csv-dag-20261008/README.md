# Fixed offline three-step CSV DAG candidate

源码/测试精确 SHA `e8b1ed4199a1234060bafbe658cf7a9c52088fff`，独立分支 `dev/fixed-csv-dag-20261008`。复用既有 CSV 应用、DeliveryGraph、Store/Worker、Run/Operation/operation_intents/events；新不可变计划不覆盖旧应用定义、来源绑定、布局或 amount=30 预览。固定 preview→aggregate→report 三步只读执行，结果为 quantity=15、行数2、固定文字“列 quantity；行数 2；合计 15”，不生成 artifact 或 Release。

[复现指南](../../F2/FixedCsvDagQuickstart.md) 说明原页面入口、精确计划确认、既有 worker、逐步回执、暂停/继续/取消、同键未知接受恢复、冷历史读取与失效清屏。`source-boundaries.json` 及指南记录 f40d975 控制键依赖挑选映射；column_patches.py 字节与独审源码相同。父线程第二 reviewer 已闭合 slash/NUL 两个P2，独审38 SQLite PASS /37 PG PASS+1历史SQLite SKIP，仅覆盖键处理。DAG独审仍PENDING；author-review.md不是独立签收，parent-independent-key-review.json明确独审信息来自父线程消息，未冒称持有 reviewer 实例文件。

| 同一冻结源码，32文件、720唯一用例 | PASS | FAIL/ERROR | SKIP | 用时 |
| --- | ---: | ---: | ---: | ---: |
| SQLite / Python3.12 | 705 | 0/0 | 15 | 357.14s |
| PostgreSQL17.9 / Python3.12 | 719 | 0/0 | 1 | 681.72s |

分母不将两后端相加。test-summary.json按实际JUnit逐项列skip；SQLite15项为PG专属角色/恢复，PG唯一skip为不能历史存入PG的旧SQLite NUL行。新DAG64项覆盖实际三步、typed preflight/循环/隐藏边/权限/写/委托工具拒绝、预算、独立Fraction验算、preview/aggregate/report失败阻断、提交前故障回滚、source/owner/runtime撤权在步骤边界及最终提交前失效、计数/dispatch篡改、lease/fence/deadline、暂停/继续、cold Store与实际应用角色子进程在1/2/3已提交步骤后恢复、旧operation ID保持、未知结果和通用调和拒绝、最终回执/结果篡改、同键/精确确认、域保持、实际HTTP/DOM冷读和上下文ABA。原列补丁、键边界、CSV/Report交付图、manifest、preflight、Worker/Run/Operation、内部/协议/条件运行接口在受影响范围重跑。

每环境 provenance 保存所有 src/tests 前后hash，均source_unchanged=true，源码e8b1ed4；Ruff全src/scripts/tests与mypy50源码文件通过。实际新DAG DOM24项、原列补丁20、CSV29、Report29、ReportManifest49；每个实际驱动加载字节与工作树hash核对。DOM不是原生Edge，导航夹具关闭定时刷新，不声称后台polling或Win验证。保留既有Starlette弃用警告和PG原preview-extraction Pydantic alias警告，不换依赖掩盖它们。

双后端独立API域保持探针保存完整plan/accepted/cold_read/旧preview和逐表完整行比较：计划40表、接受37表、执行36表保持；允许变化仅既有交付请求、Run/contract、operation/intent、event、Worker.once heartbeat。使用独立csv.DictReader+Fraction读取冻结合成CSV，amount=30/quantity=15，SHA256 d5851306dd3ce833d82bced0abef12728f3e64e1ef1266ee8a9fef209a59619f。无模型、业务对象或artifact写入。逐步actual_reads和来源/输入/输出/前驱指纹、版本、operation ID见domain-proof及dag-proof。

中间失败完整保存initial/与initial-stages.json：首DOM因/csv-dag.js静态路由未挂载实际404导致JS语法错误，补入口后通过；PG夹具启动时默认初始化psql socket与自有socket不同、遗留私有lock导致连接/权限ERROR，改为容器内两个Unix socket目录、清自有遗留socket后就绪；不是产品PG测试通过或失败证据。两份大型原始setup ERROR日志/XML以可逆gzip保存，原字节hash见compressed-originals.json。初始域保持探针误将既有Worker heartbeat算禁止变化，修正允许集合后通过，无产品源码修改。这些中间结果不当最终冻结验收。

原断言、scripts/.github/.gitattributes、Windows900 / Edge240 / Node150与依赖锁不改，无新CI/main/forcepush/部署/真实模型或凭据配置。LIVE=0。semantic UNKNOWN、owner PENDING、publishable/formal_publication_enabled=false；原生Windows/Edge、真实任务gold、完整P-B、人工验收、DAG独审均未完成，旧1591全量不用于本改动证明。

PG为自有network none、无TCP、私有/tmp socket、无PGDATA宿主挂载；既有fixture按用例创建/销毁临时schema及最小应用角色。DAG回归结束后保存结果，暂留PG/Node隔离基础设施供紧接的授权CSV开发基线整合回归；最终cleanup证据在两阶段结束后补齐，开发.venv保留。DAG不混入CSV基线整合。
