# 已接受单请求 extract 的确定性完成

本片实现 V5 §8.2–8.3 / F2-T09 的一个窄恢复入口。只适用于现有 `test_only` Store、`mock` 协议执行器中，普通 extract 的唯一请求已 `RECEIVED`、候选接受见证已持久化，但完成事务尚未提交的状态。不是通用 UNKNOWN 恢复，也没有打开真实账户或模型资格。

`POST /api/projects/{pid}/protocol/runs/{rid}/complete-extraction` 只接收 `expected_version`、`expected_fence` 和本次完成命令的幂等 `request_key`（原发送键仍由 origin 绑定）。版本和 fence 必须为严格整数；不接收响应、文件路径、usage 或补证。原 `/recover` 状态接口和 F1 行为保持原样。

发送前的 V2 origin 同时落在原 Attempt 参数、Run/Attempt 双事件和实际 provider 槽中，绑定 Run、owner/project/runtime、接受快照、phase、Attempt、请求序号、原键、发送 fence、共享池 genesis/原占额槽、实际 HTTP 字节指纹、provider stage/scope 和原期限。返回后核对规范 usage、模型身份、安全响应、原响应指纹和 candidate，再由原 `accept_candidate` 接受一次；之后持久化 V2 accepted 双见证与原 sidecar 整体指纹。实验绑定、发送和结算必须一致，不能用两份相同内容给旧 V1 补造关联。

恢复端没有 sender/provider。它先核授权，再只读打开服务端固定的既有 sidecar/lock；拒绝符号链接，核同一文件描述符身份，非阻塞持锁至数据库提交。只有原 worker 租约已到期、当前版本/fence 匹配、未取消且未完成，才在原事务中 CAS 增加 fence，并复用原纯编译和完成 SQL。旧 Attempt/两槽发送 fence 与占额保持原样；不续租、不重新 accept、不退款、不清 halt。提交前再次核完整回执、当前 sourceproof、授权和原有限期限；任何故障回滚完成写入与 fence。

相同完成键返回已核完成回执；不同键拒绝。实验已合法 `advance(extract)` 时，历史审计还须核完整完成 seal 和精确 ADVANCED 的 stage/result/proof，不能要求旧阶段仍为当前阶段。未完成的恢复仍要求 extract 是当前阶段。

拒绝范围包括 STARTED/UNKNOWN、缺 usage/关联、旧 V1、多请求、source/cold/bounded-check、未决 Operation、撤权、过期、取消、暂停、活动租约、错槽/跨 Run/wire/namespace，以及 provider/shared pool/experiment halt。新完成入口没有把这些状态降级到旧路径。

最终冻结源码的隔离合成测试 **37 PASS，10.17 秒，8 次 Mock**；原兼容回归 **20 PASS，7.95 秒**。恢复前后业务计划、指纹、原回执和所有非完成账表保持一致，写点故障及提交前撤权/取消/过期均全回滚。实验推进后的实际 Cold 回执 verifier 无发送通过。独审发现并闭合历史阶段误拒；源码限定 ACK，不冒称独审执行测试。

[完整证据、失败原件、源码冻结与范围](../evidence/protocol-extract-completion-20261022/README.md)。本片未运行真实时钟 G0、P-B Cold2、W5、真实模型、PG、Windows、UI 或远端 CI；不签整体 F2、模型语义或真实账户验收。mypy 仍有未改动 native loader 的 3 项既存诊断，不能称类型检查通过。
