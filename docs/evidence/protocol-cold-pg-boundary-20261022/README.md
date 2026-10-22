# Cold 封存事实的 PG 应用角色接线，2026-10-22

本片结果为 **离线 7 PASS / 实际 PG 1 SKIP / 0 FAIL，0.96 秒**。基线 `74bf5bde2dd91fae59995f3dbae28bab8c53f209`；最终测试的五份源码 SHA 见 [冻结清单](frozen-source-hashes.json)，运行后逐份复核不变。未修改产品代码、workflow 或依赖，没有触发 CI、Source、extract、Worker、Mock 或真实模型。

## 原计划与真实缺口

[F2 持久事务门](../../F2/ProtocolExecutionGatesPlan.md)和[既有 PG 应用角色证据](../../F2/ProtocolSharedBudgetWindowsCIPlan.md)已有实际 PG 协议/恢复/并发及受限角色覆盖；不把它们说成全未实现。历史自有 PG 已停止、连接已清除。本次缺口限定为最新封存 **Cold** 的完整持久事实在已有应用角色下导入、事务失败回滚、两个连接同键等待和新 Store 重放的组合验证。

当前环境无显式 `SIM2ACT_PROTOCOL_PG_RUNTIME_URL` / `SIM2ACT_PROTOCOL_PG_SCHEMA`，未观察到 PG 服务或原生服务工具。旧 `env/runtime_role` 夹具会创建 schema/角色并 GRANT，本轮不调用。没有安装、启动替代服务、创建角色/密码、扩权或尝试连接未知数据库。环境检查见 [environment.json](environment.json)。实际 PG 仍 **NOT_RUN**，不是 SQLite 代签。

## 已交付的测试入口

`tests/protocol_pg_sealed.py` 只复制已有封存 SQLite/四份 sidecar 的核验原字节，读取固定 55 表全部列（96 行），保留 JSON SQL NULL 与 JSON null 的独立见证；按原类型绑定值导入已有空表，并在同一事务内全量复读收口。异常让原事务回滚，不截断字段，不重建业务事实，不重新发送或接受候选。

`tests/test_protocol_pg_sealed.py::test_existing_pg_app_role_sealed_cold_atomic_and_original_key_wait` 为显式 opt-in：

1. 连接前要求已有 `postgresql+psycopg` 回环地址、显式端口/数据库/应用身份及**已有非空密码**，schema 为 `test_` 加 32 位小写十六进制。拒绝 URL query 和 `PG*` 环境覆盖；实际 DBAPI `host/hostaddr` 均钉定该回环地址，固定连接 5 秒、SQL 20 秒、锁 10 秒超时。此限制仅为本测试入口，不是新增产品认证规则。
2. 只读核当前用户等于会话用户、无五类管理员标志、原 READ COMMITTED、已有 schema USAGE/无 CREATE/非 owner 或 owner member、55 个普通表及逐项 CRUD 权限、列/类型家族/nullability/主键、原键唯一约束与空表。类型家族匹配不等于精确 DDL 等价，真实导入后 typed digest 不可省略。未发 DDL/ROLE/GRANT，也未执行破坏性 DDL 探针；不声称全数据库权限审计。
3. 同事务导入完整封存事实；注入真实 review INSERT 失败后要求全部 55 表回到导入后的指纹。随后两个独立连接使用同一 body / `sealed-cold-pg-concurrent-original` 键；在第一个事务持有时核 `pg_blocking_pids(second)` 包含第一个 PID，再放行，要求仅增加一个 review/event、相同严格回执。该见证证明事务串行化，不单独证明等待源就是 unique index。
4. 新 Store 只复读原键，核 Cold SUCCEEDED/v3/f1/PASS/APPROVED、owner PENDING/未发布；仅原 Cold Run 的 status/version 及一条 review/event 可变，四份 sidecar 不变。明确合成业务时钟沿原封存时间，不改变产品时钟/租约/期限，不认 G0 或真实语义验收。
5. 模型/预占/候选接受/Worker/claim 均设立即失败陷阱；退出释放本轮事件并 dispose 自有连接。**真实运行会一次性消耗预授权空 schema，并保留完整合成数据及最终 review 作为持久证据，不自动 DELETE/DROP。** 重跑必须另有已授权空 schema，不能清除未知数据。

最小剩余条件是：指定环境已有获准运行的 PG、上述应用角色连接与预迁移空隔离 schema，且该 schema 可接纳并保留本片合成数据。无需为本测试新建凭据或权限；本轮不主动 provisioning。若这些条件具备，可在已有安全注入两项环境值后只运行该 test，外层保持 `timeout --signal=TERM --kill-after=10s 120s`。不要把连接值写进报告、命令历史或 Git。

## 本次实际验证与保全

最终命令及结果见 [summary.json](summary.json)、[原始 pytest 日志](final-pytest.log)。7 项为：完整映射往返、真实中途 INSERT 故障回滚、两种 NULL/严格 JSON 类型和 PG 方言编译、三种坏表示前置拒绝、连接覆盖资格门。实际 PG 用例在创建 Store/连接之前因缺配置 SKIP。PG 方言编译不是 PG 服务器执行。

[完整往返原件](roundtrip.json)与[回滚原件](fault-rollback.json)分别保留 55 表/96 行 typed digest。SQLite engine 均已 dispose，pytest 终态 exit 0；未启动服务或子进程，未触碰未知进程。本轮自有临时 SQLite 留作离线证据，不把它称 PG 清理。

独审发现首版允许 query `host` 覆盖 URL authority；[离线反例](pre-review-connection-counterexample.json)使用 `remote.invalid`，仅检查 DBAPI 参数，**从未连接**。已修为连接前拒绝 query/环境覆盖并钉 hostaddr，新增 host/options/service/PGHOSTADDR 反例。修前通过日志与旧哈希保留在 [before-independent-fix](before-independent-fix/pytest.log)，不能用其代替最终测试。现存 Starlette/httpx 弃用 warning 保留，不安装新依赖迎合 warning。

只读独审结论见 [independent-review.md](independent-review.md)。实际 PG 角色、锁等待、持久重放、类型往返/回滚，以及 PG HTTP、OS 重启、真实模型、G0 均未验；本片也不替换既有 Cold TCP/ASGI 或 Source 原生 UI 的各自口径。

## 官方语义依据

JSON SQL NULL 使用 `null()`，JSON null 使用 `JSON.NULL`，不能用 Python `None` 混同，见 [SQLAlchemy JSON 文档](https://docs.sqlalchemy.org/en/20/core/type_basics.html#sqlalchemy.types.JSON)。逐个查询 CRUD 是因为逗号分隔 privilege 列表表示任一权限，见 [PostgreSQL 权限与会话查询](https://www.postgresql.org/docs/17/functions-info.html)。实际等待设计使用官方推荐的 [pg_blocking_pids](https://www.postgresql.org/docs/current/view-pg-locks.html)，不按线程启动时间臆测已发生数据库等待。
