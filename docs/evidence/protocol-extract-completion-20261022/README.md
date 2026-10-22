# 单请求 extract 已接受响应的完成恢复

基线 `52cf3f63580fd5f301876a2b409f0037a89727db`。本目录是明确 SYNTHETIC / SQLite / Mock 的工程证据，产品合同见 [说明](../../F2/ProtocolExtractCompletion20261022.md)。没有真实 HTTP、真实模型、收费、生产账户补证、G0、Cold2 或 W5。

## 最终冻结结果

- `final.log/xml`：37 PASS / 0 FAIL / 10.17 秒；实际 8 次 Mock（共享普通 Source2 + 正常 extract1 + 中断 extract1 + 普通 Cold兼容1 + 独立实验 Source2/extract1）。实验推进后的 Cold 只核回执，没有发送。
- `final-budget.json`：实际 transport 计数及合成请求原字节；上限8，180秒 timeout + 10秒清理信号宽限。明确测试业务时钟，原 lease30/run300 不变，不作真实时间准入结论。
- `compat.log/xml`：原状态恢复全文件与 V1 provider 关键路径、旧完整 Source→extract→Cold 合成链，共20 PASS / 7.95秒。120秒 + 10秒清理宽限，原 Mock-only 夹具；该进程未增加总 transport 计数器，不伪报聚合发送数。
- `final-source-manifest.json`：最终运行前553个 source/test/config文件 SHA256，运行后逐项复核未变。`static-equivalence.json`：抽出的纯编译与原完成 SQL 语句 AST 完全相同，旧 recover/recover_expired/recover_expired_protocols/_classify AST 未改。
- `persisted-facts.json` 与四份 `.sqlite.gz`：原正常/真实中断/冷新连接完成/真实实验绑定的终态原库和关联事实。普通 Run 的不同审计 ID 不被假装相等；恢复结果与中断前已算出的同一 compiled/result 完全一致，另核正常链业务 candidate/proof 一致。恢复只改 runs/protocol_jobs/events，原 Attempt、共享槽、预算和 provider 文件字节不变。

反例覆盖错槽、wire、跨 Run、缺 usage、V1/缺 origin、STARTED/UNKNOWN、多请求、错误 phase/bounded、未决操作、原始 namespace、sidecar/双槽不一致、halt、撤权、原期限、取消、暂停、活动租约、错版本/fence；每例独立复制真实已提交夹具，拒绝前后完整表指纹与 sidecar 相同。另在实际完成写点注入故障，以及完成写后撤权/取消/时钟过期，整组回滚。不是 W5 五写组。

同一 pytest 进程中的原 Worker 调用以 BaseException 在已持久化 accepted 之后、原完成函数入口中断；新 Store 冷连接没有 runner，测试将 call/reserve/accept 设为立即失败。这37项不证明 API/Worker 进程重启或 PostgreSQL 并发。正常线程均 join，测试进程 exit0；没有恢复旧实例、创建其他写入者或停止未知进程。终态进程检查另存 `cleanup.json`。证据 lock 文件保留，不能把文件存在当作锁仍被持有。

## 开发原件和独审

`initial`：1 PASS / 1.97秒，原 provider 槽计数4（当时没有总 transport 计数器）。`round1`：35 PASS / 1 FAIL / 9.64秒 / 8Mock；失败是 namespace 负例夹具把两个 pool 主键更新成同一值，原 IntegrityError 栈保留；修正夹具只更新 offline 行。`round2`：37 PASS / 9.70秒 / 8Mock。独审随后发现实验 ADVANCED 后历史回执误拒，修正并补无新发送的实际 adapter 审计后才产生最终结果，旧版通过不冒充最终版。

四次新测试进程合计28个 Mock 槽/请求（initial按原槽计数，其后三次有 transport 计数）；恢复本身0请求。兼容进程另列，未混为有总计数器。本轮没有启动600秒性能窗口。

`/root/independent_gap_review` 只读静态审查的最终增量限定 ACK：历史分支必须 SUCCEEDED、完整已完成 seal、精确单条 ADVANCED(stage/resultfp/prooffpNone)，原 binding/send/settlement/授权/source/pool 仍核；无历史分支仍要求当前 extract。审查者没有执行、加载、打开数据库或写入。其绑定的最终 SHA256：

- completion：`3f10b6b6bb61bfb8f492c8be117ab16e9b68b53ced98189306887b527d15dd56`
- test：`0b316745ead54eb71e97533ba35fe1c81e8bf3d75647de7b7f6b7692ed103a6f`

Ruff 与 diff 空白检查通过。`mypy-initial.log` 保留3项未改动 `_cold_typed_native_candidate.py:188–189` ModuleSpec/loader诊断，本轮不能报 mypy PASS。唯一既有 Starlette/httpx 测试依赖警告保留，未为消警安装依赖。

原件位于 `/workspace/sim2act-extract-completion-20261022`，各文件哈希见 `originals-manifest.json`；最终复制原件另有本目录 `MANIFEST.json`。不删除失败原件、不补零未知观测、不将此窄恢复视作通用 UNKNOWN、真实源、PG 并发、Win32 锁或产品整体验收。

随后在同一冻结产品源码上完成的[独立进程恢复验证](../protocol-extract-process-recovery-20261022/README.md)另计：原 Worker/API 进程退出后才启动新 API，4 Mock 准备、恢复0 Mock。不把它倒填为本目录37项原来已证明的范围，不合并兼容回归发送数。
