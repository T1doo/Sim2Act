# 组合终验交付日志

2026-10-07，冻结测试和唯一 Windows CI 源码为 `e6c03cf15b7473ebce4cd3d5b8c4dcc06405a676`。主工作副本 `/workspace/Sim2Act-bounded-product-candidate`，独立回归文档 `f38f64532f128f68ddc38d5b49467bc8111e959c` 已正常合并。204 个 src/scripts/tests/.github 文件逐项 SHA 匹配；两份完整 JUnit 均为 1035 项。SQLite 995 PASS / 40 SKIP / 0 FAIL / 0 ERROR，392.15 秒；其退出后 PG 配置全量 1031 PASS / 4 SKIP / 0 FAIL / 0 ERROR，892.57 秒。完整命令、skip、慢项、导入来源和限定清理见 [回归证据](../evidence/final-combined-regression-20261007/README.md)。首次并行的两个启动超时失败保留，未改源码、超时或覆盖；资源观察不能证明其因果。根复核证据目录 34 项哈希全部匹配。

独立实际 HTTP 复核已验证普通 Python 和 `-O` 下旧 protocol namespace 与跨项目 first-FIFO 均在 Worker 前拒绝、全表指纹不变、Attempt0/RunQUEUED；修复前 fcea 的缺陷及未启动全量事实保留。有限来源链仍为 source/cold UNKNOWN / NOT_ACCEPTED、owner PENDING；候选技术编译成功不替代这些状态。

两次普通 fetch 均确认远端 `7c02c66efc09ad8b23a5e92e2ee61a25e21dfc59` 为 e6 祖先。普通 push 精确 e6 到既有 `dev/f1-foundation`，ls-remote 随后确认 e6。唯一自动 CI 为 [37613698141](https://github.com/T1doo/Sim2Act/actions/runs/37613698141)，job `112766850163`，11:23:04 UTC 启动，当前自然运行；终态及像素待补。原 900 秒 job、150 秒 Node、4 分钟浏览器 step、runner、保护及覆盖不变。只优化已经加载页面的重复导航与逐 chunk flush，局部 Linux 计时不承诺 Windows 总预算。

等待期间另树保存命名持久 Report 草稿切片，分支 `bounded-named-report-draft`，文档 tip `3105aa743959d3962ed9a4a77ab93caa30b6b80b`、产品 `b326639b517a2dcfe37ca8360a4475a589c16b0f`：来源绑定命名保存、冷页列表/打开、输入新 Scenario、实际冷 Run 和历史。独立真实 HTTP 发现未知回执重试收到 422 后错误解锁可重复创建 Run，修复后同 key 两 POST 回同一 Run，失败证据保留。它是既有项目 runtime 的 PREVIEW_ONLY 声明式 wrapper，不是独立 AppPrincipal/AppManifest/Release；基于旧 fcea，仅批准新增切片，后续须先与修复来源正常整合并验证。该树未合入本次冻结源码，PG/full/native 未测，未 push。

本轮真实 provider / models 请求0，无新增产品 Principal/Grant、部署或 main 合并。全局 P-B、F1/AT02、Win11、用户/语义和正式发布签收未提升。

Windows 终态补记：11:35:18 UTC 为 FAILURE，job734秒，工程1017 PASS /18 SKIP /0 FAIL /0 ERROR（1035完整项，556.10秒，step567秒），受保护 Edge step105秒失败，Report/Cleanup成功。实际错误是 owned conditional fixture exited before reply，不是150秒超时；原session丢弃stderr，不能仅据日志确定child根因。仅6文件555chunks完整emit/bytes/SHA匹配，source-bound19/conditional22/protocol结果及两新PNG不可用；旧22历史不迁移。根实际查看4旧范围PNG，不作为新增报告态像素验收。step7曾因只看completed状态误报SUCCESS，已及时更正并以官方终态失败为准。完整失败、实际时间、decoder自测12/12、像素范围见 [本次Windows失败证据](../evidence/windows-bounded-native-e6c03-20261007/README.md)。未rerun；正在独立树复现旧protocol遗留QUEUE与新增严格FIFO组合，修复只限真实owner取消明确旧夹具意图与安全分类错误回执，需证明再验收。

后续诊断更正：`8de0c63` 的取消候选只复现人为增加3QUEUED的反事实；旧26最后的有界default16循环已自然drain，官方jobs5不支持该假说，因此根撤回取消方案，不合入或推荐该source。实际旧gated Worker source2/review/extract1/cold1→defaultdrain/recover到PAUSED、jobs5/旧4Attempt/noQUEUE后，新bound source普通/`-O`均退出：RuntimeError，Run真实WAITING_RESOURCE、0新Attempt，RESOURCE_UNAVAILABLE / Explicit experiment Run binding required。本地因果是原项目已有ACTIVE实验的正确门控；Windows原stderr仍不可恢复，具体异常仍UNKNOWN。最小修复只复用seed已有另一项目的既有授权A-S资料，经other_run当前可信snapshot/权限/hash核对派生固定fixture域，显式切换UI；other_run为PAUSED，不作为成功任务来源，新source仍真实Worker和独立检查。不关闭/伪造实验，不松FIFO/namespace，不新建项目/身份/Grant；并补安全enum/action/exit诊断。父线程已明确授权实际旧→新串接、独审及影响范围回归通过后再普通push并执行一轮原900秒CI，无需重新询问。

等待期named草稿必要基线对齐已完成，正常merge e6、无冲突/11个named源字节不变；独立本地分支最终clean tip `6d42966103f072f16b6234e9948b8fc614ac2767`，来源/FIFO与named恢复/篡改专项12 PASS /0 FAIL /0 SKIP，21.92秒。未合入取消候选或主候选，未full/PG/nativeCI/push/LIVE；保留PREVIEW_ONLY与原语义/正式发布边界。
