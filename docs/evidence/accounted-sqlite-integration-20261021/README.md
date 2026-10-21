# Accounted Source SQLite integration — 2026-10-21

本片是显式内部双跑测试桥，默认产品路径不切换。未删 pin、未变更原授权/fence/租约/期限、事务结构、预算或校验。未运行 Worker 构造/执行、业务 Mock、真实模型、G0 或 W5；未开第四窗口。原失败证据未改动。本片不宣称提速、G0 通过或完整 PB/Cold_prepare 成功。

## 实施与实际见证

- 每例在专属临时目录创建全新 SQLite，不调用通用 env，不读取外部 PG 配置，不续旧 DB。纯控制面只创建合成身份、材料、Goal 与排队记录，不 claim/派发。精确 `object.__new__(Worker)` 仅携带真实 CGR 所需状态，未运行构造器或执行器。
- 五对旧获准归档字节作为静态输入，配以新合成身份、历史、封存审批、3 Generate/2 Source Attempt、完整 ledger/cursor、controller+NS 镜像/锚、Capture、Operation、Release 与授权行。合成历史保持 60 秒间距、审批先于 Generate；不 patch clock、不等待 RPM、不 reserve/send。
- 原 `Store.tx / BEGIN IMMEDIATE` → `_source_reads / _ColdGraphRead` → `_graph_journal_state / _graph_stage_accounted` → 私有 issuer → 同一 Source handle → 原 Source bodies/resolver / archive-chain。原查询、typed/full guards、权限、回执、期限及失效路径继续执行；`_accounted_test` 仅加 owned 叶子与旧结果对照。
- 每次 owned 读取重跑完整 CGR；同身份 settings/binding/model/max_output_tokens 内容变化、stop 均拒绝。离线 factory 只接受 `transport=None`；可变传输（包括同身份换 handler）保守拒绝，不声称证明任意 handler 内容。默认产品调用者不创建 scope/bridge。
- Slot/Identity/Outcome 与外部 Ledger 全值匹配；完整字节、SHA、原字段及隐藏 RowMapping sidecars 保留。未从 mutable frontier 排除任何根，私有 Packet/manifest 不写入旧签名/业务指纹。

最终冻结源码实际测试：**55 passed, 1 warning in 38.68s**，其中组件 38、真实 SQLite 集成 17。覆盖新旧 Source 回执/私有字节一致，全 Slot/Identity/Outcome 反例，真实 commit/rollback/SQL write/native driver write 后失效及持久化结果，scope 关闭后 record/handle 拒绝，pre/post/跨 scope 隔离，动态内容与撤权。原撤权错误码为 `GRANT_REVOKED`。Worker 构造/once、InternModel 构造、同步/异步 HTTP/Mock model transport 均装有拒绝 tripwire。现存唯一 warning 为 Starlette httpx TestClient deprecation，不是业务发送。

```text
.venv/bin/pytest -q tests/test_cold_accounted_component.py tests/test_cold_accounted_sqlite.py --basetemp=/tmp/sim2act-accounted-sqlite-20261021/pytest-data --junitxml=/tmp/sim2act-accounted-sqlite-20261021/junit.xml
.venv/bin/ruff check src/sim2act/cold_accounted.py src/sim2act/natural_source_archives.py src/sim2act/pa_trial_dispatch.py tests/accounted_sqlite_fixture.py tests/test_cold_accounted_sqlite.py tests/test_cold_accounted_component.py
.venv/bin/mypy --follow-imports=silent src/sim2act/cold_accounted.py src/sim2act/natural_source_archives.py src/sim2act/pa_trial_dispatch.py
```

Ruff 与三个模块 mypy 通过。`default-path-ast.json` 移除仅显式测试分支/转发参数后比较三个原函数的完整 AST，均等于基线 `62f5e26fe6e2d54e2d2011e1d0e203590343ea84`；仅为静态补充。独审是只读源码核对，非第二次运行，六个冻结文件哈希见 `independent-review.md`。

## 边界与剩余条件

这是实际 SQL/producer/issuer/消费者桥集成。**上游 bound/native candidate/Source proof/audit/review 仍是明确合成输入**。`pb.candidate`、`pb.frozen_for`、`ConfirmInput` 使用原纯构造器保持完整字段格式；未执行全来源生成、audit、review、confirm 或完整 Cold_prepare，不由 helper 名称升级为来源/性能验收。四个 Source 输出指针使用同一独立合成 JSON 资源，未把输入材料当运行输出。

显式 `_Bounds` 只用于这一有限夹具：序列化大小是 allowance 的 sizing input，当前数据实际发行成功；没有声称编码长度给任意图通用上界。生产聚合 nodes/edges/depth/leaf/encoded bounds、全部消费者迁移仍未闭合，不能启用替代、免除旧 guard 或据此执行新业务窗口。旧全图读取、动态授权/Run/fence/期限/事务语义均保留。本片额外 full checks 没有 G0 收益声明。

参考核验：[SQLite total_changes](https://sqlite.org/c3ref/total_changes.html) 只覆盖同连接写入，不是跨连接版本。原 transaction identity、driver.in_transaction 与完整 guards 共同保留。[SQLAlchemy 2.0 connections](https://docs.sqlalchemy.org/en/20/core/connections.html) 提供 commit/rollback 生命周期背景；运行验证以本仓库锁定版本日志为准。

`source-hashes.json` 固定实际源码与旧静态字节输入。`sqlite-source-result.json` 是本次正向运行生成的回执/摘要，含合成标记。临时 DB 不纳入 Git，连接由 finally dispose。无 main 写入、强推、发布、费用、凭据或外部权限变更。
