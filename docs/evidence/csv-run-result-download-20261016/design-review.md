# CSV 结果 JSON 下载：独立最小设计审查

本轮用户已明确授权独立实现 CSV 结果下载。root 是唯一产品/Git 写入者；本审查只读，不运行模型、浏览器、PG 或应用。现有 PG/真实浏览器阻塞保持，后续合成 HTTP/JSDOM 结果只能作为工程验证，不能称真实浏览器落盘、PG 或四步端到端验收。

## 现有读取合同

`internal_api.py` 的 `GET /api/internal/instances/{iid}/runs/{rid}` 先 `scope_run(..., historical=True)`，要求 Run 所属用户/项目以及 internal_run_bindings / typed AppRun 的实例关联，再调用 `app_jobs.inspect_job`。后者重新读取 frozen contract、`load_binding(..., return_release=True)` 与 `read_release`/来源授权，调用 `lifecycle.data_rows` 核对 typed 行指纹、SUCCEEDED、结果版本、release 和 output。没有必要新增 executor、Grant、API 或持久表。

返回 `id` 是 queue Run；`app_run_id` 是 typed AppRun，等于 `internal_instance_data.run_id`。还返回 instance_id、release_id、status、result、result_version、known_effects（typed结果行）。不能混淆两个 Run ID。

## 建议的最小下载行为

1. 只在 use.js 所选成功 CSV Run 的结果下显示“下载此运行结果 JSON”，继续明确区分当前/历史与目标 NOT_RUN、人工 PENDING。
2. 点击时捕获冻结目标：token、identityConnectionGeneration、workspaceSelectionGeneration、project、view 对象/generation、实例 ID、app ID、选中 queue Run ID、app_run_id、release_id、result_version 和结果 resource_id/column/sum/count。必须以该选择为基准；历史 Run 应比较自身 release_id，不能一律强制等当前实例指向的 release_id。
3. 每次明确点击都发 fresh GET 到现有实例/Run 路径。下载前再次验证完整上下文、所选 Run/版本与收到的 id/instance_id/app_run_id/release_id/status/result_version，以及 typed 行 run_id=app_run_id、instance/version/release/result 的一致性。非 SUCCEEDED、403/其它错误、无合法 typed行、任何响应绑定或结果不一致都不创建 Blob。
4. 导出只显式投影实例、queue Run、Release、结果版本、resource_id、column、sum、count。不要直接导出整个服务器对象或 spread response；不包含 token/principal、授权、原始材料、events、known_effects 全体或调试内容。
5. `sum` 保持服务器原字符串原样编码，不转 JS Number、不格式化。底层 Decimal.to_sci_string 合法输出可含科学计数且大于 JS Number 范围，所以也不应以 Number.isFinite(Number(sum)) 判定合法性。count 为安全非负整数。resource/run/release 等 ID 校验，文件名只由安全标识/固定文本构造，勿用 column/name 路径。
6. 用独立、短寿命 in-flight 标记阻止重复点击；刷新重绘同一 Run 的按钮也不能在旧请求未结束时重复 GET。不要复用运行提交 pending/intents，不创建 Run。
7. 现有 applicationUseCurrent 不含 connection/workspace；新下载必须额外捕获这两个代数。仅比较 token/project 或最终相同 Run 不足以抵御切换再回切。readGeneration 或专用选择代数也需失效旧 Run→新Run→原Run 的回调；切 tab 后旧 DOM 即使仍存在也不得出文件。
8. 按钮/上下文失效后，迟到 success/error 都不出文件、不覆盖新页面反馈。完成和异常时清除原请求标记；只恢复原按钮，不修改新选择控制。Blob URL 和临时 anchor 用 try/finally 清理，click 抛错也回收 URL；不可泄漏下载缓冲。

## 最小工程证据

- 使用已有真实 HTTP + 测试 Worker/Store 产生真实成功结果，合成精确小数/大数，freshGET下载字节/JSON投影与 typed 结果相同；count/版本类型明确。
- 每次后续明确点击重读一次；双击与刷新重绘的并发下载最多一个请求/Blob；完成后可再次明确点击。GET 前后 Run、Grant 和全持久行不变（或明确固定检查表范围），不能仅计 events。
- 非成功、403、错误实例/Run/版本/Release/app_run_id/结果、缺失或错 typed行，均零 Blob。工程级导航换项目/身份/实例/Run/tab及回切、迟到成功/失败，均零 Blob且新反馈不变。
- Blob URL/anchor 在成功和激活异常后回收。JSDOM Blob/anchor 激活桩可检查字节和资源回收，但必须报告真实浏览器 download event/落盘 NOT_RUN、PG NOT_RUN。

以上是设计风险建议，尚未审查实现或宣称任何产品测试通过。
