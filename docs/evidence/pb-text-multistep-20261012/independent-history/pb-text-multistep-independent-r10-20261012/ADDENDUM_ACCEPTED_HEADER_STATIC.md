# R10结果之后追加静态锚核查

原54有限通过报告、原55次执行及manifest保持原字节。这项按root最新明确任务仅静态检查，没有新增动态探针或扩大旧取消窗口。

**确认缺少一个独立链接检查**：generic `app_jobs.enqueue`把 `ACCEPTED.data.input_fingerprint`保存为accepted snapshot的request_fingerprint；r10 `load_binding`核原snapshot、AppRun及重建request的fp，但不比该Event字段。`text_workflows.job_scope_gate`的ACCEPTED只投影instance_id/app_run_id并筛namespace；`verify_instance_records`仅核独立IDs集合与iid；`bound`/`verify_job`未核该header.input_fingerprint。当前有效binding、操作、结果可由别的锚验证，不能据此声称此ACCEPTED header字段也已完整冻结。此发现是**未动态复现的新静态合同缺口**，不是已有真实攻击或响应泄露证明，不能加入旧3真实FAIL数量。

建议在当前scope授权先门之后，要求该run恰好一份ACCEPTED，其完整data规范fingerprint等于从原accepted snapshot派生的canonical namespace/AppRunID/instanceID/ReleaseID/input_fingerprint；整字典比较同时关闭缺字段、额外字段与类型宽等。该新门属于精确已接受输入链，不扩功能。root已表示会在其现有回归自然结束后最小修复并另freeze/fresh验证。本独审54仅对应r10 414map8315/68PYccf4，不提前签未来修改或软件字节桥。

另原执行 `text_apps.compute`明确拒绝 `term != term.strip()`。`expected_lookup`中先strip是oracle内部处理，不意味着执行支持自动trim；有限输入应描述为非空、单行、前后没有空白的词。此处不提出新增输入功能或代为更改代码/文档。

新静态缺口使最终父交付仍需补齐此header门。本报告原动态结论未抹除，父作者后续45＋精确锚两例和对应字节桥不能在尚未运行时假称通过；原PG/native/model/取消窗口等NotRun边界保持。
