# 当前源码唯一完整 Mock PB：独立结果复核

结论：**FAIL，完整 PB 未通过；不重试。** 原始 JUnit 为 1 test / 1 failure / 0 error / 0 skipped，343.763 秒；launcher 正常退出 1、未 timeout，wall 345.299957615 秒。该结论不继承或恢复旧双 actor JS installation digest 取消窗口，也不构成真实模型、PG 或正式发布验收。

本审仅用标准库读取原 JSON/XML/JSONL/文件哈希、只读 Git archive，以及多次 `sqlite3` 连接 `file:.../fixture.db?mode=ro&immutable=1`。未导入产品模块，未运行测试、PB、producer、Worker、模型、数据库写入或权限操作；只写本 `/tmp` 审核目录，未编辑仓库。

## 原件与源码一致性

- 授权源码 commit：`a952866022a3976eedf045408778ea901760646b`。723 份 source-before/source-after 条目完全相同，逐一核当前文件 bytes/SHA256，且逐一核该授权 commit 的 Git blob，差异均 0。
- 依赖 32 distributions / 5386 files 的前后 maps 完全相同，逐一核当前 bytes/SHA256，差异 0。此为 manifest 覆盖集合，不扩大为整个机器所有二进制的证明。
- 实际 launcher SHA256：`3384e7e67c472ab271179055b15424876ea14a4e54e42bcbd4bf6d6b052749eb`，与执行前最终 ACK 字节相同。
- 原 observer SHA256：`2209e9a71be5341cdac68abf314c991a51262a7ee61c5079ee87d3f7fdcc6c67`，receipt stable；56 安装、56 RESTORED，secondary errors 0。
- 本审核对原输出目录 21 个 regular files 建立独立 bytes/SHA256 表，保存在配套 JSON；它是审核清单，不替代原始运行回执。
- 关闭 fixture DB：`802208e5b8299bc86a1e6427a303612af71410a5b496cc62f642f66f6903998d`，本审前后字节 SHA256 相同。

## 实际完成范围与拒绝终态

原 observer 与 DB 一致：generate 3 / source 2 / cold 1，共 **6** 次 MockTransport 请求，均回 200；目标成功路径预期是 7，而不是实际已经使用 7。durable production journal 共 6 槽，均 attempted=true、accepted=true，halted=false，revision 18；相邻 reserved_at 间隔 60.249927 / 60.272548 / 60.950087 / 61.093069 / 62.787920 秒。protocol_request_pools/slots 两张通用表为空，不应误当本控制器 journal 的六槽记录不存在。

每个槽/Attempt 的已知用量均 prompt=100、completion=900、total=1000，总计 6000 token。Cold reserved_tokens=3974，保留 2950-byte request 和 476-byte response 的原归档回执；收到响应后 `NS_RECEIVED`，然后 `NS_REJECTED(VERSION_CONFLICT)`。**journal 接受原始接收结算，与后续语义/提交拒绝是不同阶段**：Cold attempts.status 与 model operation.status 最终均 `REJECTED_KNOWN`，不能把 journal 改述为 rejected 或 halted。

- generation Run：PARTIAL；source Run：SUCCEEDED，已有 source typed 1 行与 source artifact.save_text 证明。
- Cold Run `run_8ad68516b5464a2ab9852e098928db3c`：RUNNING、fence=1、result/error=null、cancel_intent=false。
- Cold AppRun：RUNNING、output/error/result_version=null；Cold instance 的 `internal_instance_data` **0 行**。全库 typed 1 行属于已成功 source，不能写全库 typed0。
- Cold 仅 read_pick operation VERIFIED；duties_pick model operation REJECTED_KNOWN。不能宣称 Cold 写结果、owner review、第二次 Cold model 或整体成功断言已完成。

## 失败点、期限与 observer

`failure-observations.jsonl` 原 traceback 指向 `natural_spec_runtime.py:2824`，`commit` 的 first prefix 内：

`not self.worker.stop.is_set() and end < min(finite)`

错误为 `Production admission expired during verification`，VERSION_CONFLICT，safe_retry=false、effect_known=true。这次不是旧 full 的 `Store.guard: Stale worker lease`。失败位于 first commit 完成 trial-output 前；W5 / G1 / finalguard 均 NOT_REACHED。

完整 `finite` 来自：RunCheck deadline、source.expires_at、natural_spec_clock.deadline、各有效 role 的 created_at+run_seconds、final frozen contract、draft runtime limits、call meta.deadline、call node deadline。RunCheck 本身在 `production_trial_policy.py:329` 取 freshly read actual Run row 的 lease_until / contract expiry / created_at+caps 三者最小值。

DB 可见的部分值为 created_at=1792475423.630554、最终 lease_until=1792475504.0387254、natural_spec_clock.deadline=1792475723.630554、trial expiry=1792476964.0777411、run_seconds=300。fixture source resolver 代码返回 contract expiry。但**失败帧实际完整 finite、end、worker.stop 以及实际被读 RunCheck row 未保存；唯一最小项未知**，不得把 DB 终态 lease 直接当作失败帧全部期限或排除 stop 项。2824 中的布尔复合条件不是逐项原因记录。

G0 wall=32.040857440、threadCPU=32.037724680；first_binding wall=4.368145081、limits_facet wall=5.717438897；G0 check=7921、input_key=8125、SELECT=7188。first_binding 本次返回成功，并不代表完整 G0 或 lease 验收通过。指标为嵌套 observer 时长，不能把各 inclusive 数字简单相加，不能把新 first binding 与旧完整 G0 混为同一测量边界。

lease 原件记录 89 个 heartbeat return、4 个 OperationalError/SQLITE_BUSY(5)，本次无 observed Store.guard error。它支持“本次确有 SQLite heartbeat contention”，但不构成唯一失败原因或可延长租约的结论。

## 上下文与清理边界

原 context 记录 Linux x86_64 / AMD EPYC 9V45，affinity 0–4，cpu.max=400000/100000，memory.max=16 GiB。cgroup 两端 nr_throttled/throttled_usec 均 0；loadavg 从 `0.01 0.01 0.00` 到 `0.61 0.22 0.07`。owned-child resource delta user=74.570828 / system=3.790642 秒。这些是 launcher 边界快照与子进程累计 CPU，G0 的 wall≈threadCPU 支持该区间主要消耗该线程 CPU；不能据此证明全程不存在机器竞争，也不能把低 load 倒推旧环境。

`/proc/self/status` 的 TracerPid=0 属于 launcher，原件没有 child sys.gettrace/getprofile/tracemalloc 全程状态证明。清 PYTEST_PLUGINS 与禁 autoload 已记录，但不能扩大为所有观测均未启用。

receipt 记载正常 exit、remaining_owned_group=[]、after_evidence_errors=[]、无 cleanup_error/uncertain，故无需 TERM/KILL。证据目录与 DB 按计划保留；这里的清理结论是“自有运行组无残留”，不是删除整个证据目录或销毁共享服务。实际依赖和源码未变化。

此 fixture 使用 synthetic account、noncredential placeholder 与 MockTransport；autouse no_real_http 拒绝默认 HTTPTransport/AsyncHTTPTransport，实际六次外层调用均标 Mock。LIVE 是合成 fixture 的模式名，不是真实模型调用证明。本审不声称做了整个 sandbox 的网络审计或穷尽秘密扫描。

有限结论：原件足以确认本次单次完整 Mock 验收失败、Cold 已接收再拒绝且无 Cold typed 提交、源码依赖稳定和 owned group 已结束。完整 PB、W5/G1/finalguard 及真实模型验收仍未关闭。没有重跑建议或新窗口授权。
