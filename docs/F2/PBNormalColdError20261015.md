# Normal Cold 原始错误捕获：单次运行交付

状态：**NOT_ACCEPTED**。本次仅补齐正常 Cold 的原始错误观察边界；没有生产修复。本次正常完成未捕获历史失败，不能证明历史故障消除，也不能归因为 Stale、事务或续租。

基线 `058ed298bdaae3978485452eb58301d14ea77970`；实际测试冻结提交 `4a0096612757499d1eab0cccd8550d426249b360`；分支 `dev/pb-normal-cold-error-20261015`。

## 合同与实现

只修改 `tests/test_pb_trial_dispatch.py` 的 `test_pb_full_actual_worker_extraction_and_cold`。原始 Worker.once 调用及全部 50 条断言表达式、消息和顺序保持；模块其余函数 AST 不变，包括 Source、故障包装和 failure_trace。`src`、pyproject 无变化。

在原始 once 周围记录原始 fail_job 公共错误、已有受限 traceback，以及 once 原返回或直接逃逸异常；原函数同参数各调用一次，原返回/异常继续传播，随后恢复包装。后续状态和 HTTP 断言不在异常捕获范围。finally 写回执，写入失败不能替换已有异常。没有新增数据库读取、时钟读取、lease/guard/预算或生产执行器修改。

运行前 PREDECLARED_FORK.json 区分 guard984、其他 handler 错误、直接 Worker 异常、正常失败但无错误、正常成功但无目标错误。CONTRACT.md 的简写“zero fail_job -> early exit”受该明确前提约束：只有**正常测试失败且无 handler/直接异常**才分析早退；成功不属于早退证据。

## 唯一实际运行

原顺序、离线、1800 秒上限、-x：正常 Cold → 6 个阶段边界 → 9 个提取拒绝/原子回滚 → 5 个 Cold 故障。**21 PASS / 0 FAIL / 0 ERROR / 0 SKIP，退出码 0**；耗时 873.3391370773315 秒；正常 Cold 482.090 秒。运行前/后/执行副本的 503 个源文件一致，HEAD 未变且当时工作树干净。没有第二次运行。

原始 XML SHA256：`320bab9ef7e14c75ad791d46b4ad97fc547f893e34df1424fd78f70b5fd02bb1`。

正常回执：`worker_once_return=true, fail_job_calls=0, worker_public_errors=[], worker_failure_traces=[], direct_exception_trace=null`。原有成功状态、实际发送和核算断言全部通过；不是仅凭 once=True 判定成功。选中“正常成功但未捕获目标错误”分支；未观察到失败早退。

共保留 7 份实际边界回执（正常、Source、5 故障）。Source 完成且收到 2 个离线响应。5 个预期故障都实际注入且各发送 1 次；错误分别为 GRANT_REVOKED、绑定变化 VERSION_CONFLICT、lost_response 的原测试预期异常、VERIFICATION_FAILED、OUTCOME_UNKNOWN。故障路径保持原实现；不是历史正常失败的替代证据。全部回执中 Stale worker lease 为 0，guard984 为 0。source_revoke 的 guard977 先在 source_scope_gate 抛错，尚未获得行字段；相应字段为 Unknown。

## 仍缺少的观察与结论

历史正常 Cold 的 RUNNING/error=None 失败仍保留于 prior-normal-RUNNING.xml，原 XML SHA256 `85a7e5f099ee0c8976f3ae394355bcdc4c0b6b3b7e8dd645224408d3f1afb6ea`。当时没有本次正常路径包装，不能追补其原始错误/栈，也不能从 RUNNING 或 once=True 推断 Stale。fail_owned 在所有权/lease/status 不符时可无元数据写入返回；这只是静态可能路径。

本次缺少该失败的原始错误、原始事务/helper/renewal 栈和 guard984 当时行值。原比较时刻始终 Unknown，禁止用日志时间或事后时钟替代。因此不能选定失败分支、锁定事务/续租因果或提出有证据的最小产品修复。遵守单次合同，到此停止复跑与诊断循环。历史失败与此前 NOT_ACCEPTED 不撤销。

## 其他验证与边界

6 个包装合成控制 PASS：原 handler 返回/抛错、once True/False/DomainError/RuntimeError，各一次且保持对象身份。这不是 Worker/数据库/guard/写回失败验收。Ruff 已观察实际 CLI PASS，详见 RUFF_TOOL_RECEIPT.json；本次未重跑 mypy，历史 5 个既有错误保留，未称全库绿。

没有真实模型/付费 API、凭据配置、权限扩展、部署或强推。PG、Windows、原生浏览器、人工语义、真实 P-A/P-B、旧库升级及远端 CI 均 NOT_RUN；既有拒绝路径未重试。此前完整 389 项中的 1 个失败及其他历史失败仍未解除。

## 证据与复核

证据目录 `docs/evidence/pb-normal-cold-error-20261015/`：完整原始字节包、MANIFEST.json、ARCHIVE.json、公开回执和新旧 XML。fixture 与执行源码仅在进程退出后无损打包，每个文件和符号链接读回校验后移除解包副本。公开 XML 仅作明列脱敏，原始字节保留。独立静态审查已完成；最终实际证据审查记录随完整包封存。推送后精确远端/保护引用/工作区验证保存在仓库外，避免封存后修改证据。
