# P-B 连续提取 WIP 首轮只读独审

基线 `4855d5250fd576bb04f81faad22ca6a4ccdfcbdd`；2026-10-16；仅 app.js/internal.js WIP 差异。审查者未改仓库。

此次核查的精确生产字节：

```
43b21a35b67e0b0c4ad63785f7aadaa70a25b011e5cb9de2304e929bf8a2cb4c  src/sim2act/web/app.js
403859d19a6abf2756f7dbb602acc16dfe653c5754a1790d7fd3d288e62d865f  src/sim2act/web/internal.js
```

静态格式/语法：git diff --check 与两个文件 node --check 通过。没有运行 Worker、真实模型或旧恢复矩阵。以下是 WIP 字节上的发现，不代表后续修复冻结仍存在。

## 已发送根线程的三个发现

1. 新 PB per-use 能力 GET 引入互斥时序缺口。最初检查 engineeringPending/pbUseUnknown 后等待 caps；等待期间只锁该 per-use s.busy，原默认运行仍可建立同实例 engineeringPending。caps 返回只核 current/review/edit，仍建立 PB pending 并 POST。须在创建 pending 前重新核 pbUseUnknown、engineeringPending（以及 view.busy），不能依赖 await 前的结论。恢复旧 key 仍应跳过能力 gate。已对实际生产 action 函数字符串用合成闭包执行：cap 等待后放入另一默认意图，实际仍产生 1 PB POST 和 1 PB pending，另一意图保留。证据 `/tmp/f2-pb-wip-cap-pending-race.json`。此隔离探针不声称完整 DOM/HTTP 验收。
2. 新 firstCreation PB 准备返回是异步且 p.returning=true，但 p 没有 per-use instance。原 showInternalInstance 第一行的短路判断随后访问 p.instance.id，可在返回未完时的实例导航/迟到调用抛 TypeError，未结束准备。最小修是在读取 id 前检查 !p.instance 或明确 firstCreation 分支；该实例选择应安全结束准备与旧 guide。已隔离执行实际生产 showInternalInstance，合成 firstCreation PB/returning=true，收到 `Cannot read properties of undefined (reading 'id')`，preparation_cleared=false。证据 `/tmp/f2-pb-wip-return-instance-null.json`。原生 UI 的实例按钮当前隐藏，这份探针只证明函数对新合法状态的不完备处理，不声称完整原生交互复现。
3. pb-spec-open 的失败收尾需处理新 guide。showApp(guide) 在首次 GET 前会 clearApp 并移除原 s.panel；GET403/来源撤权/candidate 冲突时，finally 仅复原 opening=false，guide 仍是 extract 且 s.saved 存在，于是提示“点击打开”但原按钮已不存在，原异步 onclick 也无 catch 状态。建议在该 guide/current 的失败或 false return 分支明确结束原 guide、报告已存 app 保留并引导目录重选；只清本 guide/本 opening view，不能覆盖新选择。成功交接仍须在完整 showApp 返回及 exact current/app 后才释放 temporary fence。

## 首轮有限正向核查

- 原 extraction review/ack/commit/body/request_key/by-key 严格校验没有更改，原 naturalTaskRequests 页面内存 pending 未清除或变成重发。
- 新来源按钮已对齐 node/view/instance/selection 的同步守卫。
- PB target 准备复用共享原 forms，返回先重读 source-options 验 proof/recipe fingerprint 与精确 source proof，再读目标 Goal version/fingerprint/唯一资源；只回填目标，未自动 POST review、提取或 Run。
- guide 在已鉴权 source-options + goals 读取成功后启动。PA 进入 PB 时清旧 guide 不清同一 source engineering view；新保存 app 打开后只有完整 shown/current/exact app 成立才释放 opening fence，绑定新 engineering view，而非继续依赖被移除的旧 extraction panel。
- 原 Release/instance 成功观察器继续比精确 id/fingerprint，返回目录只读，目录仍 metadata-only，后续使用继续现有 per-use。
- 新 gate 的 test-only mock/provider intern-s2/model intern-s2/no live 检查与 natural_spec_runtime.enabled 的现有离线配置条件相容；实际 MockTransport 仍由原后端发送门检查，不构成 LIVE 批准。仅 PB 新提交受 gate，原 key GET 不受 gate；PA 分支未新加该读取。

结论：本轮 WIP 暂不能签收，等待上述时序/失败状态补强与最终冻结；无需修改后端 source/权限/lease/executor 合同，也无需扩旧恢复矩阵。
