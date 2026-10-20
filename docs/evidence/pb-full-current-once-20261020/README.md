# 当前冻结源码：唯一完整 Mock PB 验收失败

父侧在[只读上下文审计](../pb-full-context-audit-20261020/README.md)之后另行授权了一个新窗口。本目录封存其**唯一一次**执行，冻结源码为 `a952866022a3976eedf045408778ea901760646b`。未恢复永久取消的旧 JS 双 actor 安装窗口，未修改产品或测试，未重试。

唯一节点：`tests/test_pb_spec_production_controller.py::test_pb_production_original_source_extraction_explicit_use_and_cold`。2026-10-20T05:46:02.755742Z 启动、05:51:48.055728Z 结束，pytest exit 1：**1 failed、0 errors、0 skipped，JUnit 343.763 秒；外层 345.299958 秒，未超时**。

## 实际结果与边界

| 本次观测 | 实际值 |
| --- | --- |
| 外层 Mock 请求 | generate 3 / source 2 / cold 1，共 6；重复 attempt 0；真实模型 0 |
| G0 wall / 本线程 CPU | 32.040857 / 32.037725 秒 |
| 首 binding wall / 本线程 CPU | 4.368145 / 4.367753 秒 |
| cold.limits_facet wall / 本线程 CPU | 5.717439 / 5.716334 秒 |
| G0 SELECT / check / input_key | 7188 / 7921 / 8125 |
| W5 / G1 / finalguard | 全部 NOT_REACHED |
| 失败 | `VERSION_CONFLICT: Production admission expired during verification` |
| 冷 Run / AppRun | RUNNING，结果 null；不是 SUCCEEDED |
| 冷模型 Attempt / Operation | REJECTED_KNOWN；usage 已知 100 prompt / 900 completion / 1000 total |
| 冷实例 typed 数据 | 0 行；NS_RECEIVED 后为 NS_REJECTED，没有 NS_SETTLED |
| durable accounting journal | 6 槽均 attempted=true、accepted=true，halted=false，包含 Cold 的已知 usage |

账本中的接收记账与业务结果验收是两个状态：六个响应已记账不表示冷业务成功。原测试在最终 `status == SUCCEEDED` 断言失败。失败栈精确落在 `natural_spec_runtime.py:3484` 的 `cold.commit`，继而 `:2824` 的 `require(not self.worker.stop.is_set() and end < min(finite), ...)`；本次没有记录到 `Store.guard` 错误，不能把它改称旧运行的 `Stale worker lease`。

G0 超过原 30 秒租约，原期限/stop 复合保护拒绝了提交。不过实际局部变量 `finite`、`end` 和 `worker.stop` 没有保存，不能仅凭最终库认定是哪个最小期限或 stop 条件触发。G0 input_key 的 SHA 输入累计 5,164,606,462 bytes、inclusive CPU 23.936526 秒；codec.bytes inclusive CPU 19.904881 秒，SHA 构造器 2.453848 秒。这些计数含嵌套、重复输入，不能相加或当作独占 I/O、可追回预算或优化结论。

本次首 binding 比历史失败短，但不能据此归因于代码、机器或 observer；完整 G0 仍失败。历史原件及其缺失上下文保持原状，不用本次硬件记录补写历史。此前被否决的 validator/SHA、身份缓存和 observer 方向没有重做或重测。

## 冻结、隔离与退出

开跑前独占输出目录不存在，可用空间 9,196,097,536 bytes。启动器 SHA256 `3384e7e67c472ab271179055b15424876ea14a4e54e42bcbd4bf6d6b052749eb` 已经独立只读审查；原 observer 整包 SHA256 `2209e9a71be5341cdac68abf314c991a51262a7ee61c5079ee87d3f7fdcc6c67`，没有删减。56 个观测安装均恢复，secondary observer errors 为空。

前后 723 份 source/test/schema/依赖声明文件及 32 个发行包的 5386 个实际安装文件均逐文件大小、SHA 相同，Git HEAD 与工作树在执行前后无漂移。source manifest SHA256 `d885baa8d4675331731cca8bc8335a1f7463e27f7217601552191bb6a902ca7d`；dependency manifest SHA256 `5182c1ff374af5892289f2c6577536e9e2da5d8183647e4eb49ce719a9111a11`。这些文件清单与 context 见原件，不把后续证据提交称为被测试产品提交。

启动器清除两个数据库选择变量、PYTEST_PLUGINS 和 PYTEST_ADDOPTS，禁插件自动加载，仅显式加载原 observer；原 no_real_http 与精确 MockTransport 断言保留。数据只在本次新建的 test_only SQLite 和原测试内置的四个合成损坏备份库中。TTL 1800 / Run 300 / lease 30 / RPM gap 60 秒、7 槽 / 输出 7168 / 预留 192000 / wire 32768 / paid cap 0 均未改变。未部署、未连接真实模型、未建 PG 用户或权限。

本次机器 AMD EPYC 9V45，cgroup CPU 配额 `400000 100000`、内存上限 16 GiB。前后 loadavg 为 `0.01 0.01 0.00` / `0.61 0.22 0.07`；cgroup throttled 计数均 0。实际自有子进程 CPU 为 user 74.570828 / system 3.790642 秒；不是局部线程 CPU 或整个容器 CPU。300 秒 faulthandler 是原诊断栈，未耗尽 1200 秒外层预算。

原 JSONL 有 89 次 heartbeat 返回、4 次 SQLITE_BUSY，没有 Store.guard error；它证明本次存在 SQLite 心跳锁竞争，未隔离其对失败的因果贡献。context 只是边界快照，不证明全程无竞争，也没有记录子进程全部 trace/profile/tracemalloc 状态。

子进程 PID/PGID 20663 正常以 exit 1 退出，收尾自有进程组为空；没有发送 TERM/KILL，无 cleanup/runner/after-evidence 错误。失败后不恢复 Worker、不改终态、不重试。只读闭库核查采用 SQLite URI `mode=ro&immutable=1`，total_changes=0，前后库 SHA256 同为 `802208e5b8299bc86a1e6427a303612af71410a5b496cc62f642f66f6903998d`。

## 可复核原件

[summary.json](summary.json)是派生索引。[MANIFEST.json](MANIFEST.json)记录每个归档文件 SHA/大小及 gzip 解压后 SHA/大小；gzip mtime 固定为 0，压缩前后原字节一致。

- `raw/`：实际 invocation、receipt、JUnit、stdout/stderr、完整 observer、前后 source/dependencies/context、fixture.db、四个原测试备份库和原始 JSONL。
- `inspection/`：退出后只读账本提取，属于事后检查，不冒充测试原始输出。
- `launcher/`：实际执行的 runner、原 observer 及开跑前 manifests/context，均压缩保存。
- `independent-review/`：精确启动器独审及事后结果独审。没有额外执行 PB、producer 或测试。

本窗口已经消费，结论保持失败。剩余验收条件仍是冻结目标在原限制和所有安全门下完成 Cold2、W5/G1/finalguard及最终七槽链；本结果未使真实模型、语义或平台资格通过，也不产生新的重跑授权。
