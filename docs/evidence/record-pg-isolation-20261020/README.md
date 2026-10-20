# 原记录工作流 PG 验收前置：隔离夹具已修，实际 PG 仍 BLOCKED

基线 `80e63bd136b2df8934f112860334fc5877960dc5`，产品仍为已接受的 `fa244834efe50358459340b30f5a988a39089164`。本轮不新增产品功能；仅修正原记录测试四处冷 Store 的 PG namespace 继承。`src/`、Schema、依赖锁、scripts、workflow 与基线无差异。源码 hash 见 `source-sha256.json`。

## 当前真实资源边界

只读检查没有找到现成可用 PostgreSQL：postgres/initdb/pg_ctl/psql/pg_config 不在 PATH；Docker daemon 可访问，但容器及镜像列表均为空；数据库连接相关环境变量名均无值。没有搜寻凭据文件、创建实例、拉镜像或初始化集群。当前服务器版本无从确认，不能套用历史环境的17.11。脱敏布尔及命令实际结果见 `environment.json.gz`；独审另核无 postgres 进程/监听。

既有唯一 workflow 只接受 `dev/f1-foundation` push，没有 workflow_dispatch；`WindowsCI.ps1` 要求实际 Windows runner/PGBIN，并会生成两密码、initdb、createdb、CREATE ROLE/GRANT，随后跑完整工程及 Edge、清理临时集群。这是创建资源的方案，不是可复用的当前连接；不能在本轮无新凭据/安全权限、无共享服务变更及不盲跑的限制下自动启动。没有触发 CI、探测模型或改分支触发范围。

**未执行的具体动作：**在专用 PG 上执行原记录唯一11节点的真实事务、冷进程/连接池重启、schema 隔离及数据库服务重启。状态为 **BLOCKED_ENVIRONMENT / NOT_RUN**，不是操作被拒绝，也没有结果不明的 PG 写入。

最小条件是一套已批准、可丢弃且可启停的专用 PostgreSQL（记录实际版本及启停方式），通过现有安全机制注入现有连接；该角色已具备该测试库内创建/删除专用 `test_<32hex>` schema 和所需表 CRUD 的权限。无需新 LOGIN/GRANT/真实模型。不能对共享 PostgreSQL 重启来补证。若只能给不可重启的测试库，则服务重启门仍未验。

## 真实发现及最小修正

`tests/conftest.py` 用 `schema_translate_map` 指向随机测试 schema；原 `test_local_record_apps.py` 两处、`test_local_record_content_edits.py` 一处与页面 Worker 一处仅把 URL 传给新 Store，会丢失该隔离，PG 查询可能落回默认 schema。原 SQLite 冷读通过不能发现此问题。

新 `tests/record_test_store.py` 仅接受显式 test_only Store。PG 在新 Store 创建前强制检查专用 schema，兼容 `db.Store.initialize` 已允许的 SQLAlchemy 同值 `_none` 内部别名；拒空/public/错范围/冲突别名，净化为独立 `{None: schema}` 后用于新 Engine/Pool。没有 initialize、DDL、权限变更或连接探测。四处冷路径复用该 helper，原业务 oracle 和断言保持；页面输入清单补入新 helper。

该机制与 [SQLAlchemy 官方 schema translation 说明](https://docs.sqlalchemy.org/en/20/core/connections.html#translation-of-schema-names) 对齐；只据此处理 Table 所属 schema，不声称它覆盖任意裸 SQL 或替代数据库实际权限。

## 实际执行，分别计量

- 无 PG 连接检查首批 **9 PASS / 2 FAIL，0.33秒**：9个配置拒绝守卫通过；两个正常方言对照在测试辅助 `render` 为旧无 map 路径错误传 `render_schema_translate=True`，触发 SQLAlchemy 断言。仅修正测试编译参数，未改产品/helper。
- **仅复测两个受影响节点：2 PASS，0.08秒**，包含原生 map 与 `_none` map。PG DBAPI connect 被 tripwire 禁止；旧 URL-only 的资源读/回执读/实例 CAS/typed INSERT 编译不带测试 schema，新路径全部带同一精确 schema。原 SQL 原件保存在 `compile-fixed/`，这是方言编译，不是真实 PG 执行。
- 原内容更正 API 独立折叠冷读及实际 HTTP/JSDOM 页面各一次，**2 PASS，7.00秒**；仅 SQLite/NoModel。为把新 helper 纳入完整执行输入清单，随后仅页面节点再跑 **1 PASS，4.49秒**，144 输入前后零差异。两条原节点不重复计为新用例，不把之前的11P重标为本轮 PG 或父侧实跑。
- 每个 pytest 批次一个原 Starlette/httpx warning。Ruff 与 git diff --check 通过。没有 PG 事务/锁/CAS/JSON、最小角色、真实服务重启或 PG 清理回执。

所有批次原 stdout/JUnit、原失败、SQL、页面 HTTP/IPC/Worker/输入清单及独审报告均封存，`MANIFEST.json` 可按压缩前后 hash 核验。短暂 apply_patch transport closed 在文件读取前失败、后续命令未启动；只读重核环境和 Git 后恢复普通文件操作，没有新建或恢复实例。

非作者最终只读复核 **LIMITED_TEST_FIXTURE_REVIEW_PASS，P1/P2为空**，未重复作者测试；最终页面输入清单仅另补 helper 文件，不改执行逻辑。原产品两文件 hash 仍与已接受版本相同。

## 有资源后的唯一原回归

`existing-record-regression-nodeids.json` 从上一片原始11唯一节点列表机械转换为 pytest nodeid，未改变 oracle，不是本轮执行结果。资源满足后仅对这个列表安排真实 PG；使用原事务故障/取消/旧 fence/私有隔离及独立事件折叠。冷 Store/Worker 应继承同一个专用 schema；数据库服务重启需另外保留启停前后 PG 进程/版本/连接断开及原记录/回执读回证据，不能仅重建 Python Engine 就签为 PG 服务重启通过。

完整 P-B/G0、真实模型、Windows/native、语义/owner、正式发布及旧软件迁移等门均不提升。
