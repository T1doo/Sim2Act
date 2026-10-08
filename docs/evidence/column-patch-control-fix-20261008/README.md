# Complete column-patch key boundary repair candidate

本候选基于 `eb2e5fbe72ac8585a65c441eaff5e02dd50825a5`，分支 `dev/column-patch-control-fix-20261008`；精确源码和测试 SHA：`f40d9751771166bc877fcfd10237f06fc9e59a48`。原 a3831127 与 eb2e5fbe 审查分支保持冻结，本候选不含 DAG 代码，不合并 dev/main，不部署或发布。

第二 reviewer 已闭合 slash-key P2，但在检查 body 原键与解码路径发现 NUL 新 P2。本作者另用归档 eb2e5fbe 精确源码，通过真实 loopback HTTP 独立复现：SQLite 检查 JSON NUL 键被接受 201，PG 同请求 500；编码 NUL 路径 PG 500（baseline-reproduction.json）。加载模块字节 hash 与该 Git SHA 对应文件核同；没有冒称获得 reviewer 实例文件。

统一 `validate_request_key` 覆盖定义、检查 body、解码路径、load 与 read_pair，均在可能绑定这些键的 SQL 之前拒绝：键长 1–128、无 Unicode 控制字符（Cc）和无法编码的代理字符（Cs）。定义/检查模型在 Pydantic 字符串转换之前调用同一校验，避免默认验证错误回显坏代理字符导致 UTF-8 编码 500。其他非字符串类型仍由原严格字段类型处理。slash/Unicode/空格/字面百分号及历史合法点段键的恢复、精确指纹、幂等与旧记录结构保持；新定义点段仍在接受前拒绝。SQL 原键是字面文本，不二次 URL 解码。

历史 SQLite 异常键不删除、不覆盖、不作为当前证明。授权历史读取在将键用于 SQL 查询前分离它们，仅返回 unsupported_keys 元数据，页面安全文本标明 UNSUPPORTED_KEY；合法计划/检查继续可读。历史兼容异常记录测试显式种入旧 ledger 合同，验证读取前后原行相同；并非声称做过真实用户数据升级。

| 精确 f40d975 定向验证 | PASS | FAIL/ERROR | SKIP | 时间 |
| --- | ---: | ---: | ---: | ---: |
| SQLite / Python 3.12 | 135 | 0/0 | 0 | 97.07s |
| PostgreSQL 17.9 / Python 3.12 | 134 | 0/0 | 1 | 168.41s |

135 个唯一用例包含新控制边界 91、原键修复 13、原列补丁 28、实际列补丁 DOM 1、原 CSV/Report 图 DOM 2。唯一 PG SKIP 是历史 SQLite NUL 文本行兼容 fixture，PG 无法历史存入这种文本；PG 的 JSON/路径 NUL 拒绝已实际执行通过。全部 C0/C1/DEL 及两种坏代理字符覆盖公共校验与直接入口 SQL 前拒绝；实际 HTTP 覆盖 JSON、编码路径、原始非法 HTTP 目标、字面百分号隔离、合法特殊键、重放和历史保持。非法原始 HTTP 目标由 parser 返回400；编码 LF可由路由返回404，均无接受回执。

独立真实 HTTP 证据 sql-before-proof.json：SQLite 和 PG 的检查 JSON NUL 与编码 NUL 路径均400，SQLAlchemy before_cursor_execute实际观测绑定字符串，控制键参数出现数均0。加载源码字节对应 f40d975。正式用例另对多种控制输入执行同样 SQL 参数断言。两个环境每轮源码及测试 hash manifest 前后相同（*-provenance.json）。实际 DOM 断言各20、29、29，所加载源码字节经原测试核对。Ruff src/scripts/tests 与 mypy 48 source files 通过。

失败和中间阶段保留：initial/sqlite-stage 为未冻结阶段57 PASS/34 FAIL，33例是测试误将错误码当异常 message 匹配，一例是旧 ledger fixture 错用不存在的 id 列；已改为明确 error.code 断言及真实复合键。ascii-stage 为7a890f5源码SQLite99 PASS。unicode-stage 为5b2adcf源码PG131 PASS/3 FAIL/1 SKIP：两例因 CheckInput 提前拒绝代理字符而用例未构造直接入口输入，一例是真实框架响应 UnicodeEncodeError 500；该500已由共享 before-validator 修复。baseline-first.log 为基线500后复用连接被服务器关闭，复现驱动改用Connection:close后双后端完整复现。这些均不当作最终通过证据。

原断言、页面6秒等待、90秒子进程、Windows900 / Edge240 / Node150及CI/依赖配置保持。LIVE=0，无真实模型调用、新CI、权限扩展或业务写入；Windows/原生Edge NOT_RUN。工程候选、语义UNKNOWN、人工PENDING，待同一第二 reviewer复验；本作者验证不是独立签收，旧1591全量不用于证明此改动。

PG 为自有 network none、无TCP、无PGDATA挂载、私有/tmp socket 的--rm容器。停止前实际查询 test schema=0、test role=0（pg-cleanup-query.json），正常停止删除与正常删镜像，无force。控制修复自有临时路径已清理（cleanup.json）；授权未完的DAG开发工具/阶段证据另列保留，不混作本候选资源。开发.venv保留。

DAG另存 `dev/fixed-csv-dag-20261008`，阶段提交 `7f7a9e61d0db3f5adb8decf505b533887b008018`。该分支已以cherry-pick接入71ae9f3→1961fda、6ed920b→bb92ccb、c19ae75→5848bdf；仍需挑选本候选7a890f5、5b2adcf、f40d975并记录映射，补页面脚本路由及最终恢复验证。DAG阶段未完成，不在此候选中。

复验：pytest -q tests/test_column_patch_controls.py tests/test_column_patch_keys.py tests/test_column_patches.py tests/test_column_patch_ui.py tests/test_delivery_graph_apps_ui.py；DOM使用自有jsdom30.1.2的NODE_PATH，PG仅给自有隔离测试库URL。runner.py保存实际编排；baseline-runner.py与sql-before-runner.py保存独立HTTP复现/SQL观测，不接受任何任意执行输入。
