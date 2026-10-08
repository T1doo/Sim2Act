# Column patch request-key repair candidate

真正第二 reviewer 在冻结的 a3831127 上发现 P2：定义键 `independent/key` 可被接受，却不能经普通单段路由确认。该报告来自另一个实例，本目录没有冒称取得该实例文件或复用其测试证据。本作者另以 git archive 的精确 a3831127 源码和自有 SQLite，经真实 loopback HTTP 独立复现了 201 / 原路径404 / 编码路径404 / 双编码409；加载模块字节与该 SHA 对应 Git 文件一致（baseline-reproduction.json），原冻结工作树未改动。

修复分支 `dev/column-patch-key-fix-20261008`，基线 `a38311270fe943a971ec3afbe9ea237583f8a137`；精确源码与测试 SHA 为 `c19ae7504befe9e23bf355d0767fc1187c1095d2`。原冻结分支未改动。DAG 阶段代码另在本地 `dev/fixed-csv-dag-20261008` 的 `a6a483588533d811b9c5de37a8bc569d8a97736e`，不在此候选中，尚未接入修复或完成全部验证。

确认路由改为 `{key:path}`；完整键由调用方编码一次，支持 slash、Unicode、空格、字面 percent。双编码代表不同的字面键，不能拿来确认另一个定义。新控制字符在 SQL 前拒绝，新 dot segment 在保存前拒绝；已有地址可定位键的 immutable request/receipt 模型和历史结构未变。历史 dot segment compatibility 用例显式种入原 ledger 合同再恢复；不是声称运行过旧版本升级流程。

| 精确 c19ae75 定向验证 | PASS | FAIL/ERROR/SKIP | 时间 |
| --- | ---: | ---: | ---: |
| SQLite / Python 3.12 | 44 | 0/0/0 | 70.08s |
| PostgreSQL 17.9 / Python 3.12 | 44 | 0/0/0 | 110.75s |

范围为新真实 HTTP 键用例 13、原列补丁用例 28、实际列补丁 DOM 1、原 CSV/Report 图 DOM 2。每个环境实际 DOM 断言分别为 20、29、29；加载源码字节指纹经原测试核对。测试前后源码及测试 hash manifest 相同（`*-provenance.json`）。Ruff 全 src/scripts/tests 与 mypy 48 source files 通过。合成 CSV 实际结果 amount=30、quantity=15；原幂等键返回同一请求、指纹、结果及历史，错误指纹不会覆盖旧记录。

首次并行验证在 71ae9f3 上 SQLite 42 PASS/1 FAIL、PG 41 PASS/2 FAIL，原始日志/XML/源码 manifest 保留在 initial-concurrent：两例是新 HTTP 驱动默认 5 秒读取超时，一例是 NUL 拒绝前进入 PG SQL。后者已将控制字符检查移到查询前；新驱动显式 30 秒读取上限。原断言、页面 6 秒等待、90 秒子进程以及 Windows 900 / Edge 240 / Node 150 未改。pre-import-sort 保存 6ed920b 的 SQLite 44 PASS；仅导入排序完成后，对 c19ae75 两个环境重新完整验证。

全部 LIVE=0、没有真实模型调用、部署、正式发布、业务写权限扩展或新 CI。原 CI/脚本/依赖配置与 a3831127 一致；Windows/原生 Edge NOT_RUN，语义 UNKNOWN、人工验收 PENDING；仍需同一第二 reviewer 复验，本作者验证不是独立签收。旧全量 1591 未用于证明本改动。

临时 PG 为自有 `--network none`、无 TCP 端口、无 PGDATA 挂载、私有 /tmp socket 的 --rm 容器，结束正常停止删除并正常删除镜像，无 force。清理前 schema/role 查询误用了缺少 SQLAlchemy 的系统 Python，未获得实际计数，不声称查询为零；容器移除销毁整个临时库，`cleanup-note.json` 明确记录该限制。自有 SQLite fixture、Node/npm、socket 和临时 runner 路径全部核删除（cleanup.json），开发 .venv 保留。

复验：使用开发虚拟环境运行 `pytest -q tests/test_column_patch_keys.py tests/test_column_patches.py tests/test_column_patch_ui.py tests/test_delivery_graph_apps_ui.py`；DOM 测试以自有临时 jsdom 30.1.2 设置 NODE_PATH，PG 只传自有隔离测试库 URL。调用方路径编码指南见 ../../F2/ColumnBindingPatchQuickstart.md。
