# Source + Generate accounted prewrite consumer mode — 2026-10-21

基线 `f387c391b78554fa117c614c5a6af3ce37bf647e`。本片实现实际源码中的显式内部 prewrite 模式，不是又一孤立表示原型。默认模式和 post 模式不启用；没有 settings/env/API 开关。未运行 Worker 构造/执行、业务 Mock、真实模型、G0、W5 或第四窗口。未改变 main、费用、凭据、外部权限、租约、TTL、RPM、Run 或其他原预算。

## 实施闭包

1. `_owned_prewrite(graph, explicit_bounds)` 创建绑定同一 pre CGR / SQLite 事务 / source-read token / epoch / 线程 / binding 的私有 mode。只允许 test-only SQLite；没有默认产品 bounds，也未赋予生产安装资格。
2. 原 `_graph_stage_accounted(..., _owned=mode)` 在入口拒绝重复 role，执行全部原 producer 读查询、scope、Slot/Capture/NS/usage/Operation 和最后 full guard，随后一次发行对应 family。Source 两 aid、Generate 三 aid 共用同一 scope；不会调用旧 `scope.issue()` 再跑 producer。producer 中途或最后 guard 失败立即清空整个 mode，包括已发行的另一族，未等外层 context 清理才撤销。
3. `_ColdTrialGraph(..., _accounted_prewrite=mode)` 接入 `_typed_parameters/_accounted_fields/_fields/_prepare/commit`。两个 accounted 属性、私有 logical accounted inputs、complete.source/generated 和两组 stage tuple 均引用同一 scope 的对应 family。stage 的 Generate Run、Source job 为固定 owned Record；与独立 upstream Run 逐字段完整比较，不仅比较 id。
4. gate 的 accounted / stage raw+model / stage-current / run-context 边界按显式 mode 消费 issued family。Generate usage 遍历三 aid，Cold 的 Source usage 遍历两 aid。archive Source bodies/resolver 与 dispatch archive-chain 的业务字节、canonical、usage、公共回执来自 owned records；外部 Ledger、完整 key 查询、Release/授权/approval/当前 Run/fence/租约/取消/期限仍走原路径。
5. 动态前沿与内容分离：每次 owned 访问检查 scope/事务/epoch/driver 写入计数、worker/settings/current binding、model/max_output_tokens、stop；原完整 CGR 和 typed 检查在边界保留为对照。没有缓存一次“验证成功”以替代新鲜读取，没有移除旧扫描。

`_LegacyOracle` 隔离原 tuple/models/row-storage，只有返回 `None` 的断言或旧 raw pin 组装接口；不向业务调用者返回原 job/tuple/usage/receipt。owned 数据没有 thaw/model_validate 回可变模型的路径。logical complete 的 generation 映射冻结，Run 链接核 exact Record/schema/node/ref、同 family 与发行节点；两条 Run 入口均有伪造对象零回调反例。

## 命名空间与传输合同

| 层 | 内容与用途 | 不跨入的合同 |
| --- | --- | --- |
| `mode.inputs` / `mode.complete` | 私有 family / handle / issued Record；两个 logical accounted key 与 complete 指向同族 | 不传给旧 pickle，不持久化，不作为 Authority/业务指纹 |
| `guard.inputs` | 原 raw schema 的完整 legacy witness，仅用于保留的全扫描/typed oracle | 无 Family、Packet、Node 或私有 digest 混装 |
| origin / 软件 / 公共回执 / post bridge | 保持原 schema、codec、业务指纹字段与动态验证路径 | 不用 family digest 替代原字节 SHA、origin/software 或 pre/post raw key |

代码修改会正常改变软件内容指纹；这里没有声称旧软件批准能跨修订复用，也没有为此开启新窗口。没有承诺不同对象分配下的临时 pickle key 必须数值相同。

`transport=None` 只是上一片 additive fixture 的历史限制，不是产品安全不变量。新完整 mode 接受非空 Sentinel，原 CGR transport identity 见证保留；prewrite 不读取 handler、不调用 transport。构造/发送/handle tripwire 与 Sentinel 属性访问断言实际通过。原 `spec_production.environment` 门未放宽。

## 实际验证

最终冻结源码：**100 passed, 1 warning in 88.95s**。36 项真实 SQLite 集成、38 项组件及 26 项既有纯 cohort/diagnostic/Source 回归。唯一 warning 为原 Starlette httpx TestClient deprecation。Ruff 通过，五个修改源码模块 mypy 通过。

测试使用新临时 SQLite，主命令显式 unset 两种外部 PG 配置；旧 DB/已消费 grant 未恢复。新 mode 的正向测试实际断言 producer 调用顺序/次数 Source 一次、Generate 一次，全部 2/3 aid，旧新 Source 回执/私有字节和 StageAuthority/业务指纹一致。还实际覆盖：

- 同 scope / logical inputs / complete / 两组 stage tuple 的 family 归属；禁止旧 `scope.issue()`，禁止 Family 进入旧 codec。
- 真实 Cold stage/context 当前 SQL，实际 lease/fence/cancel 拒绝，worker/settings/binding/model/caps/stop/写入拒绝。
- legacy witness 变更时 owned 内容仍为发行副本，保留的 full oracle 在消费者/动作边界拒绝。
- producer 中途链失败、最后原 guard 失败，在外层 ExitStack 清理前立即撤销 Source sibling；重复 role、commit/rollback、scope 结束、post 拒绝。
- logical Generate Run 不可重绑，schema/node/ref/foreign family 反例不触发攻击对象回调。

```text
env -u SIM2ACT_TEST_DATABASE_URL -u SIM2ACT_RECORD_PG_CONFIG .venv/bin/pytest -q tests/test_cold_accounted_component.py tests/test_cold_accounted_sqlite.py tests/test_cold_trial_pure_cohort.py tests/test_cold_admission_diagnostics.py tests/test_source_accounting_fact_leaves.py --basetemp=/tmp/sim2act-accounted-prewrite-20261021/final-pytest-data --junitxml=/tmp/sim2act-accounted-prewrite-20261021/junit.xml
```

`default-path-ast.json` 对新 mode=None 作显式特化，18 个入口/方法的剩余 AST 与基线相同；原 CGR、pickle/输入校验/row-storage/read-scope、TrialContract/PBTrialContract/caps/current Run 谓词另有 10 项完整 AST 未改。脚本一并归档；这是静态证据，不冒充实际运行。

独审为只读源码审查，8 文件清单 SHA-256 为 `5a83199c964e2d53ee711b441f18057d091b3981383cc2ac2911e0d5b1faa16a`。其指出的 immediate-close、logical generation 链接与 exact schema 屏障均已修复并实测。审查时最终测试尚在运行，随后主写入者完成相同冻结版本。首次 100 项回归及最后 exact Run 屏障修补前的清单保存在 `before-final-exact-run-guard/`；不得把两轮或独审当成 G0 性能结果。

## 精确剩余边界

上游 native candidate/bound/Source proof/audit/review 明确为合成事实；原 producer、CGR、事务、查询、授权门及上述消费者核心是真实实现。runtime typed/base/check 试验用精确未初始化载体，`trial/platform/audit=None`，没有伪造完整原生资格。

**未执行完整原生 `_prepare` 前段、constructor→commit 全 continuation、生产 PostgreSQL、完整 PB 或 G0。** `_prepare/commit` 的完整源码路由已经接入并独审，但其 native 前段的实测不能由当前核心用例代替。没有要求或开启新窗口来补该证据。

聚合 bounds 尚未从生产 Run/Attempt JSON、5 链及 hidden sidecar 的完整规模推导。夹具 allowance 仅对这一有限数据实测成功；不能冒充产品上界、删字段或换取生产启用。本片保留全部原扫描；不宣称提速或解决原 30 秒 lease 失败。以后是否移除旧 oracle/扫描，仍依赖这两类资格闭合，不由本次静态 ACK 自动授权。
