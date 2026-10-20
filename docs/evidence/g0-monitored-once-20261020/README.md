# 已消费的唯一监测窗口：保护适配器拒绝，G0未到达

结论：**UNKNOWN / INTERRUPTED**。用户批准的这一次窗口已真实启动并消费，未自动重试。失败来自本次保护适配器，不是原G0业务拒绝；不能据此解释此前PB超时。没有真实模型或业务网络服务调用、费用、第三次PGCI或旧DB改动。

修订合同及[独审](REVIEW.md)允许把原64MiB原生硬配额门改为诚实的采样预算，保留原TTL1800/run300/lease30/RPM60、审批/鉴权/全图扫描/完整账链及首次G0后W5前停止。实际代码为`4e85aecc0a8da3151df120f917f8da8feecea0f8`，从干净原开发分支启动。4131份源码/测试输入/依赖摘要为`87be3bda0ca5cb97a787f0c5a90835a6186cb975848019645354d31b8d2c1751`，父收尾重核一致。原18份冻结产品/测试/依赖源码均未修改。

## 实际发生的唯一失败

第一次Generate MockTransport async入口执行一次，原fixture `receive`已调用合成handler构造响应，随后准备写`mock-exchanges.jsonl`。原`Path.open("a")`会把默认`buffering/encoding/errors/newline`作为位置参数转发给`io.open`；`Files.fixture_open`错误地拒绝任何额外位置参数，抛出`Boundary("unexpected fixture writer options")`。原始trace定位于`tests/test_spec_production_controller.py:124`→标准库`pathlib.py:1013`→`scripts/diagnostics/g0_guard.py:248`。

这是保护程序兼容性缺口，预检和静态独审均未发现；未正确覆盖原Path.open调用方式。该次不是完整成功的Mock收发回执：原模拟handler已进入，但响应未返回调用者、wire/response日志尚未保存，不能把缺失正文重演或补造。专用Boundary作为BaseException退出，child与parent均记录UNKNOWN，不伪装成原DomainError/租约拒绝。原始[诊断](RUN/diagnostic.json)、[控制日志](RUN/control.jsonl)、[输出](RUN/output.log)、[回执](RUN/receipt.json)均按字节保留。

| 观测 | 实际结果 |
| --- | --- |
| 新grant消费/业务窗口启动 | 1 / 1；`grant.json.consumed`已保留，无第二启动 |
| Mock async方法/handler尝试 | 1 / 1；Source本地同步委托0，总方法入口1；上限仍为6收发/8入口 |
| Generate完成 | 否，首响应归档前中断；Source/Cold未构造 |
| G0/Cold W5/G1/finalguard | 全部NOT_REACHED；`g0_entered=false` |
| 原命名finite/end/stop及五阶段差值 | NOT_REACHED；没有原G0诊断实例，不填0或重读DB伪造 |
| 整轮工作/收尾观测 | 2.309956631秒，远低于600+10秒；自有PGID46859已空 |
| 磁盘监测 | 48次采样；峰值逻辑1,329,125字节，分配1,339,392字节（约1.28MiB）；无超限；这是采样预算，不是硬配额 |
| 父收尾 | `OWNED_GROUP_EMPTY`，`finalization_errors=[]`；独立/proc复核同组无成员 |

[运行后独立复核](RUN-REVIEW.md)认可上述 UNKNOWN 分类、唯一窗口已消费及不重试，并明确其未打开数据库、未执行测试或产品流程；13份归档哈希及自有进程组为空已独立核实。

## 账链原件和只读核验

新库`fixture.db`为692,224字节，SHA256 `df9f1c8de7a6e2a6d17dc828f666e1b18c969757d8821149ee0d1673f2df664e`。只在结束后用标准库SQLite `mode=ro`读取新库；前后完整SHA与父回执一致，没有写入/修复/续跑。原件仍留在唯一运行目录，归档以gzip无损保存并逐字节解压校验。

[只读摘要](READONLY-DB-SUMMARY.json)记录1个RUNNING Run（result=null）、1个STARTED Attempt（mode=LIVE、response=null、usage.status=unknown、tokens=null）、0个Operation。LIVE标签来自原隔离合成production形态分支，不表示真实模型访问。10条原delivery记录包含原批准/scope及seal、请求正文及seal、journal/quota及seal；没有响应正文记录。未补写拒绝/结算/终态，保留真实中断账链，不能宣称成功接收或已知用量。

[ARTIFACTS.json](ARTIFACTS.json)逐项记录13份运行/授权/description原件的路径、原始字节/hash及归档hash。SQLite和依赖manifest仅压缩归档，不做损坏副本/重签/状态恢复；原源文件仍保留。未知旧进程或锁没有被终止/删除。

## 必要预检和剩余条件

[PRECHECKS.json](PRECHECKS.json)及原始[单元日志](pure-units.log)记录23项：19 passed、4旧native案例主动skip；[ruff](ruff.log)通过。新监测单元验证未知/sparse文件、已unlink但打开的可写fd、symlink及扫描失败拒绝；原缓存SQL拒写、完整context后停止、真实网络/model handler前阻断和自有组清理单元仍通过。未把旧原生VFS资格或skip当作监测型完整运行证明，也未跑完整PB。

**精确缺失**是原`Path.open`默认参数转发与保护writer的接口兼容性及其纯单元覆盖。没有对程序进行事后补修或开第二个窗口。下一次若另获工作范围，须先只修此适配、以原Path.open方式验证并独审，再单独明确一次新执行授权；旧grant已消费，不恢复本Run/DB，不为凑G0数据继续外围保护工程。原G0真实拒绝根因和此前完整PB失败仍未验证。

本轮后续只有证据封存、只读审查和正常开发分支提交推送；不改main、不强推、不发布。最终交付提交SHA及远端/未提交/未推送差异见最终回复；运行代码SHA以上述`4e85aecc...`为准。
