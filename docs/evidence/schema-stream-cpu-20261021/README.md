# 完整候选归因及 schema 新鲜比较优化

基线 `16c3ba0f3c2a2b764f6cc698f34dd9db08da937b`。本轮先执行一条完整候选的
标准库 CPU 剖析，再据此修改一个确定热点，最后冻结一次完整正常链验证。
没有重开真实时钟 G0、真实模型/账户、Cold2 或 W5。原默认模式不变，未新增启用
能力；BEGIN IMMEDIATE、连接/scope、全部 SQL/授权/fence/stop/原时钟门均不改。

## 完整路径归因：成功走完尾段，随后记录器断言失败

新 configured 前缀 Generate3/Source2，加一条候选 Cold1，真实 SQLite/Worker/审批/
账链。保留原三个显式合成资格替换（environment / resolve_account / software），
HTTPTransport 拒绝真实网络，仅 Mock。明确的测试业务时钟不作真实期限验收。
全局保护在前缀前设为 **6 交换/8 入口**，真实监督 **300 秒+10 秒清理**；只执行
一次，没有重新跑剖析。原 lease30/Run300/TTL1800 和所有更严格动态门未放宽。

选择解释器为 CPython 3.12.14。无 Mock 双线程探针确认原 cProfile 会记录其他线程
事件，直接 `thread_time` 会混时基。仍用标准库 C cProfile 和原 C callbacks，
仅对本方 `sys.monitoring.PROFILER_ID` 九个回调筛 owner thread，不修改任何产品
资格/核心/serializer/prepare/commit/receipt 函数身份，不关闭 heartbeat。安装时先
关闭本方事件、安装全部筛选、clear 安装窗口，再恢复原 mask；foreign 返回 None，
退出由原 disable 清回调/事件并释放本方 tool。持续运行的其他线程探针 **1 passed /
0.05s**，owner 计数准确，foreign 不入统计，CPU 非负。方法及 profiler 不宜作
benchmark 的限制参考 [Python profiler 文档](https://docs.python.org/3.12/library/profile.html)
和 [monitoring 文档](https://docs.python.org/3.12/library/sys.monitoring.html)。

剖析保留完整原 context、最终正常返回及一次故意关闭 scope 后拒绝。实际 `_base`
569 次、`fixed_serializers` / `_typed_values_from_models` 各 275、旧 `_typed_parameters`
293、codec 8062，未因替换核心函数而测成 fallback。原 prepare 1 次、commit 2 次；
正常 context 返回、scope/mode 关闭和 closed-scope 拒绝断言均在失败点之前通过。

随后测试 **1 failed / 187.29s**：漏调用 `cap.new_case()`，因此分段计数为 0/0，
断言期望 1/1 失败。全局 6/8 限额已经生效，wire 原件确为前缀5+Cold1；但 Cold
专用分段计数保护没有切入，不能称该保护通过。原 profiling/pstats 已在 finally
完整保存，clients/Store 清理完成、无 sidecar；不把整个 pytest 称通过。
失败之后的 result/完整输出/SQL 归档和进程 CPU 快照未生成，不伪造或从旧测试继承。
8 个入口由前缀5个交换+2个 Source 同步 delegate+剖析内1次 Mock enter 路径复核，
不是丢失的最终 counter 快照。原失败源码已精确保全并核对原 freeze 摘要。

主线程剖析独占时间总和 **146.823767390 CPU 秒**。它包含 profiler 扰动，不能当作
无仪器运行成本。下表独占/包含均为原 pstats；包含列存在嵌套，禁止相加。

| 实际项 | 调用数 | 独占 CPU 秒 | 包含 CPU 秒 | 包含占总剖析比例 |
| --- | ---: | ---: | ---: | ---: |
| C Pickler.dump | 8062 | 19.415122 | 28.090953 | 19.132% |
| `_schema_shape` 完整形状重建 | 1,833,414（顶层10,001） | 6.947716 | 17.223957 | 11.731% |
| `_trial_typed_storage` | 8086 | 0.056138 | 16.956641 | 11.549% |
| `_trial_typed_values` | 3082 | 0.059378 | 37.044731 | 25.231% |
| SQLite Cursor.execute | 7735 | 0.149740 | 0.149740 | 0.102% |
| 测试 before_sql（含 deepcopy） | 7735 | 0.032060 | 0.228182 | 0.155% |

SQLAlchemy 全文件独占合计另为 2.183141 秒；不混入 SQLite execute。详细 call graph
见原 `profile.json` / `.prof` 与 `profile-attribution.json`。schema 顶层 10,001 次全部
来自 `_fixed_schema`，其中 9841 次经 `_base` 的 fixed_serializers 类循环；它不是
codec 次数推测出的热点。`_trial_typed_values` 的主调用来源为 base 新路径275次、
checked2271次、旧 typed_parameters293次及其他独立入口。

C pickle 必须保留 fresh C memo、完整行隐藏数据、字段/别名及原 bytes；本轮没有
证据支持安全省略其必要遍历。选择最大的确定、可控 schema 构造热点，避免删减
typed storage/动态校验；不承诺可省去上表全部时间。

## 实际产品改动及等价边界

`_fixed_schema` 原先每次构造完整 `_schema_shape(live, None)` 树，再与 bootstrap
形状 tuple 比较。改为 `_schema_matches` 对同一 bootstrap 形状逐字段流式比较，
取消第二棵形状树分配与随后的整树比较。bootstrap 仍用原 `_schema_shape`，原
`_CODE_LEAVES` 保持对象引用防 id 复用。没有 PASS 缓存、跨调用结果或 completed
memo；每次新鲜遍历每条 live 边，DAG 对不同 expected 分支分别比较。

保留 exact primitive/container 类型、dict 原顺序及先完整 exactstr-key 门、全字段、
原 DFS cycle 拒绝。前部值/类型/长度/顺序 mismatch 只记 False，继续检查后部非法键
和 cycle，保持原错误优先级。标量按原 tuple 的 identity-or-equality，保同对象 NaN、
bool/int 标签差异及 ±0；bytes、未知对象和容器子类仍仅 code-object id，无 foreign
equality/hash/repr/reduce。原 schema identity 不同先短路不遍历的次序不变。

新 matcher 纳入私有代码身份见证，替换前即不合格；unknown schema/serializer/helper
保留原路。未改任何业务序列化、原 bytes/业务指纹、回执、模型字段、权限、预算或
租约。没有用新版表示替换旧协议，也没有迁移更多可变根。

## 必要差分、反例及组件 CPU

- **41 passed / 30.72s**：全部59类真实 schema 与原 shape oracle、逐顶层字段修改、
  类型/顺序/NaN/opaque/DAG及同一 live DAG 对不同 expected；早 mismatch 后晚坏键/
  cycle；真实 issued SQLite 下原动态两端、入口损坏/混合拒绝、段内 mutation/stop/
  settings/write/epoch/scope、未知 serializer/helper 和新 matcher 替换。13项无关原
  用例 deselect；0 Mock。
- **2 passed / 4.34s**：真实 SQLite policy 两固定段，旧/候选模式、prepare/两次
  commit-facing 输入的完整 `exact_output` 严格输出及原指纹、正常 scope。21项无关
  用例 deselect；0 Mock。没有仅依赖 Python 的 bool/int 或 list/tuple 相等。
- Ruff 通过；mypy 两个变更 source 通过。
- 59类真实完整 schema，原 shape+比较与流式操作交替6轮、每轮25遍，未启 profiler。
  线程 CPU 中位数 **0.1841236175→0.100834649 秒（约45.24%下降）**。没有缓存成功，
  每遍都完整新鲜读；只证明该组件在这组完整 schema 上的收益，不是整个尾段或
  G0 的 CPU/墙钟改善。原计时序列见 `schema-cpu.json`。

## 最终冻结完整链

最终来源及全部相关测试的160文件摘要在 `freeze-final.json`；运行前没有旧 pytest。
修正 `cap.new_case()`，删除本轮不使用的 checkpoint/expectation 分支，使用另一份
fresh configured 前缀及隔离 SQLite，显式 **不启 profiler**。仍限6/8、300+10、原门
及原测试时钟。**1 passed / 74.30s，退出0**，没有追加运行。实际6交换/8入口/2个
Source delegate，完整两 commit 原 outputs、Cold receipt、7735条 SQL/参数全部用
`exact_output` 保存；原 context 正常返回、scope/mode 已关闭、故意闭 scope 拒绝、
Attempt 在 W5 前保持 RECEIVED。最终原期限门随原 context 返回而通过，未记录它的
原 at 样本，不用新采样或总耗时冒充该原值。

owner-thread CPU 33.400735150 秒，进程 CPU 33.626866140 秒，是本次新前缀正常链
单个无 profiler 样本；没有同输入无仪器旧链对照，不能与带 profiler 的146.824秒
作提速比例，也不能与上一任务两链总墙钟相减。未再次测量整链275个资格入口，
275是本轮第一条身份保持的实际 profile 观察；最终源码资格/核心函数未被包装，
所有160项冻结摘要一致。不能把这份新前缀输出与首轮丢失的输出称作整链 A/B。
改动等价性由上述针对实际算法的差分证明。

最终结束后没有 pytest/本次timeout进程，无任何 SQLite sidecar，线程断言通过。
两条运行合计 **12条 Mock wire**（各5+1）；最终入口8为实际 counter，首轮入口8
的证据限制见前文。两轮分别受6/8保护，没有超最初声明的总12/16上限；0真实模型、
0自动重试。所有动态门和原清理路径保持。16:58 UTC断开通知后实际命令和文件读取
仍可用；原唯一测试已正常终态，没有并发重启或对未知进程发信号。

## 原件和独审

原件、失败日志、pstats 全调用来源、两个版本源码/测试、完整输出/SQL/回执、Mock
wire 和清理记录保存在 `originals/` gzip；`artifact-manifest.json` 记录解压与压缩
SHA256/大小，SQLite 不提交。代码/设计/结果独审在 `reviews/`，只读未执行产品、
测试、DB 或 Mock。真实 G0、生产账户来源及 W5 仍未验收。
