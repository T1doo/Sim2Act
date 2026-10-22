# 核查读取失效后的投影收口

修复基线 `c9ff939e0bd3d5d709b59ad7c4ca005346ce0a58` 的确定 P2：Source 已显示 PASS 后，定位 NOT_FOUND/403 或 FOUND 后新鲜成果 GET 403 虽清成果与可见回执，却残留顶部 SUCCEEDED/PASS/APPROVED 和旧 entry 的“已复读确认”。强制重新渲染还会从旧 Run 字段重开提取按钮。

只改 `web/protocol.js` 的当前显示投影：统一失败处理保留原键、历史回执及真实 Run status/version/fence；有回执的 entry 改为 GET-only 待确认，原未知无回执的 state 不变。顶栏和 entry/可见文案明确“不可确认”；当前 Run 无新鲜内容时，重新渲染也不恢复旧成果、回执或提取入口，迟到的提取点击同样拒绝。新鲜匹配 GET 成功可恢复确认。**没有把真实 Run 状态改成 UNKNOWN**，没有修改独立 Source completion 的实现或增加业务 POST。

## 红绿原件

复用上一片的封存 [cases.json](../protocol-receipt-readback-20261022/cases.json)，无新数据库、API、Worker、Source/extract、MockProvider 或真实模型。测试仅 Node 控制器 VM，不是原生 DOM/Windows、PG、OS 重启或 G0。

- [同最终测试脚本的旧代码红测](red/result.json)：脚本以显式测试参数读取 `git show c9ff939e:src/sim2act/web/protocol.js` 的原字节，三个场景均 FAIL；原源码 SHA `de5084429e7097e8e091c84de480c9f77e16d7cf787da88202ec55dcf189fb01`。未在产品运行路径注入旧实现。[原始日志](red/driver.log)保留。更早的初始红测也保留在 [initial-red](initial-red/projection-result.json)。
- [冻结修复绿测](green-projection/result.json)：**3/3**，覆盖 NOT_FOUND、locator 403、FOUND 后成果 GET 403。逐场断言顶栏、entry.message、可见文案不可确认；强制重渲染后结果/回执/提取关闭、提取 onclick 拒绝、原 key/status/version/fence 不变、仅 GET，最后新鲜重读仍能恢复。
- [原只读恢复控制器](green-readonly/result.json)：**25 项 PASS**，含 Source 未完成且核查定位失败后的独立 Source completion 兼容。其一个完成 POST 是纯 VM 假响应，不是真实业务/模型发送。
- [原核查控制器](green-review-compat/result.json)：**65 项 PASS**，含旧确认/不确定性/上下文与迟到读写隔离。原控制器的模拟 POST 均在 VM fetch stub 内，无真实网络。

三个绿测命令 exit 0，逐个外层 `timeout --signal=TERM --kill-after=5s 20s node ...`。没有跑完整 CI、后台 SQLite 套件或新窗口。Node 进程均终态，无常驻服务启动。没有新增权限、凭据、依赖或费用。

最终两文件 [冻结清单](frozen-source-hashes.json)运行后不变。[scope-proof](scope-proof.json)记录旧代码/夹具 SHA，并逐字节确认独立 Source completion 整块实现未改。此前 c9ff 的 14 PASS/25 VM 保留为原版本历史，不代替本修复的新测。此前后端只读授权/封印门没有改动，本轮不重复数据库证明。

源码独审限定 ACK：当前 Run UI marker、不改真实状态与原请求、known receipt 待确认/unknown 不换键、重新渲染和点击均关闭、新鲜读取可恢复，独立 Source completion 无差异；审查者未运行测试。精确终态与范围见 [summary.json](summary.json)。新增真实原生浏览器、PG、provider 和 G0 仍未验。

终态原件复审限定 ACK：独立代理只读核对两源码哈希、15/15 原件长度和 SHA、同最终脚本旧 3 FAIL/新 3 PASS、25/65 控制器检查与独立 Source completion 9166 字节不变。代理未重跑测试，也不代签原生 UI、PG、G0 或整体 F2。
