# P-B 逐次目标的共享读取门禁修复（2026-10-13）

父级暂缓 `29c03b82f2bb07528f9e21f9711f76f2071fd40d` 验收，要求先实际复现，再修共享入口。基线为该 SHA，独立分支 `dev/pb-target-read-gates-20261013`；root 为唯一产品写入者，独审只读并写自己的证据。

## 实际红例与权限范围

SQLite/实际 Worker 先产生同一个保存 app/Release/实例的默认 B typed v1 和第三份 C typed v2，只撤销该 app runtime 的 C `resource.read`，保留默认 B、来源 A 及其成果授权。

- 实例列表实际 **200**，响应包含 C 的完整 `source_content`，这是直接响应泄露。
- 单实例 inspect 实际 **403**，响应没有 C 正文，但阻断观察器在后置校验前捕获 C `internal_instance_data.data` 读取。
- 合法旧 B Run inspect 实际 **200**，响应仅返回 B，但它先读取同实例全部结果，捕获 C typed 正文读取。
- 原 C key 的逐次 POST 实际 **403**，不同请求体同 key 的共享 POST 实际 **409**；两者都先读取 C `internal_app_runs.output`，观察器各捕获一次。
- 补充 owner control-status 实际 **200**，仅返回状态，但捕获 C `runs.goal` 读取；错误实例路径实际 **403**，却先读取另外实例的 Run.goal。

上述五入口主探测前后数据库不变。观察器的 **500** 是注入的 SQLite 私有 cell guard 阻断，不是原接口状态；不能将所有红例都说成响应正文泄露。完整 `raw` 与 `guarded` 状态、SQL、目标读取计数均保留。

独审后又做两项人工污染红例：typed row 改为另一实例 AppRun 指针，读取正文后才拒绝 lineage；删除全部新旧控制 ledger/USE 并移除 snapshot.pb_use，控制路径降级读取完整 Run.goal。各实际捕获一次私有 cell；这是故障注入边界，不称正常授权路径的新增响应泄露。修复后补充探测均 **409、blocked=0**。

## 最小读取合同

1. `data_rows` 在完整 typed/AppRun 正文之前，用独立的 Release/App marker、RUN_META/USE 与 accepted overlay 标量 hints 判断保护需求。受保护实例必须显式提供 store/user；无上下文原始 reader fail closed。先核 actor/project、typed run_id/version/release 与本实例 owned AppRun 的 status/resultVersion，再检查所有包含 Run 的现权目标 scope。整实例失败整包拒绝，不静默过滤历史。
2. list、单实例 inspect、版本切换提案/提交均提供当前授权上下文。既有 hash/lineage 与后置验证保留。
3. 单 Run inspect 的 typed SQL 从一开始仅过滤自己的 AppRun；不先读整实例再 Python 过滤，因此 C 撤权不会剥夺合法旧 B 结果读取。
4. 同 key POST 先查 AppRun ID/fingerprint、scoped binding Run ID、Run actor/project/runtime/request key，核当前 job gate，再读取完整 Run/AppRun/binding。不同请求体仍冲突，合法 key 仍 cached，不重新签 grant、不新增 Run。
5. scope_run 先检查请求 IID 与 AppRun/accepted IID 标量关联，再读任何 Run 正文。封存 spec job scope 也直接授权 accepted meta.resource_id，不凭默认 Release 资源替代本次目标。
6. owner 控制只投影状态、版本、取消意图与绑定身份/指纹等元数据；先核 own project、instance/AppRun/Run、accepted event、双 scope 一致性。删除 hints 不回落旧完整读取。pause/cancel 保持不依赖已撤/到期的 READ，只改控制状态；resume 在完整证明读取前核现权 gate。控制分派避免读取完整 Run.context 来猜执行器。

停止控制允许 owner 读取状态元数据，不允许通过该路径读取目标、结果、完整 accepted snapshot、AppRun input/output。未改变正常 worker、模型/凭据设置、冻结预算、来源依赖或人工语义状态。

## 观察与测试边界

行级 SQLite TEMP-view/UDF/authorizer 观察覆盖指定 C 的 Run 私有字段、run_contract snapshot、resource content/hash、operation receipt/intent，以及 typed data、AppRun output/error。已授权 A/B 的读取可以发生；`blocked=0` 表示受保护目标没有被求值，不表示整个请求没有 SQL。另记录 scoped native full-binding SELECT，元数据 JSON scalar projection允许；不声称该 spy覆盖所有任意 SQL/账本字段。PG/原生浏览器未用该观察器验证。

实际测试覆盖撤销、READ grant 自然到期、当前授权正常/cold访问、cached key/错误 key、正确旧 B、跨实例/跨 user、无上下文 raw reader、撤权后 pause/cancel 与拒绝 resume、外实例 typed 指针与全部控制 hint 删除。所有材料、账户及模型响应均 synthetic，真实模型调用零。

所有红例、修复中测试、故障注入和命令错误保留。补充脚本首轮路径拼错 StopIteration 及重用被删 ledger 的故障库导致 NoResultFound，均发生在实际补充操作前；保留 raw 并改用独立复制 fixture 复验，没有用这些失败当授权泄漏。

最终冻结矩阵和完整远端 SHA 以交付证据为准。原 `29c03b82` 的 62 PASS 不能证明本次授权修复；本轮重新执行相关工程矩阵。NOT RUN：PG、Windows、原生浏览器、真实模型/付费 API、人工语义验收、完整通用 P-A/P-B、旧源码升级、来源退休、CI/部署；原取消窗口保留 NOT_VERIFIED。

## 冻结与独立复核

- 修复提交：`3b82af1a37db4538c8fc1a7f1d81b1c1bbee3565`。
- 精确资格冻结：`81987af3ff79fbfaa2549ed6b75468bb2331338d`。资格为 75 个 Python 文件（既有 config 排除），pin 为 `ee020adfd475ca48941bef8328524d2dbf2753e415809dbd431eed53a5b8d1bc`；没有新增文件豁免或实例 grant。
- 独审针对冻结版本，静态源码快照及完整 446 文件前后映射一致；动态 2 PASS / 0 FAIL / 0 ERROR / 0 SKIP，291.26 秒。两例均与作者矩阵重叠，不增加 unique 计数。旧轮 6 次独审不计入本轮。
- 作者门禁与资格 27 PASS，836.92 秒；相关确定性/spec 回归 24 PASS，347.77 秒；各组 446 文件前后一致。撤权与自然到期五入口均返回 `403,403,200,403,403`，指定 C protected-cell 与 scoped full-binding SELECT 各为零，查询前后数据库不变。
- Ruff PASS。mypy 在 76 文件中仍有既有 5 个错误（`status_report.py` 三个、`tools.py` 两个），不能称全项目类型检查通过。

证据保留基线 red-shared 的 1 个预期 FAIL、修复中绿例、人工污染红绿、两次补充命令错误及全部 raw/SQLite。最终 PASS 数只统计冻结版本三组作者矩阵，历史失败不删除、也不混入最终验收通过计数。

## 最终验收矩阵

冻结作者三组：27 + 24 + 12 = **63 个 unique PASS / 0 FAIL / 0 ERROR / 0 SKIP**。P-B 原有复用与失败/late-result、两例离线页面组 12 PASS，1248.82 秒。独审另有 2 次重叠 PASS，因此总 65 次执行、仍为 63 个 unique。两例进程内 HTTP/JSDOM 页面为 22 项检查（10 + 12），每例实际加载 20 个页面源码文件；不是原生浏览器验收。

三组作者及独审均锁定 `81987af3ff79fbfaa2549ed6b75468bb2331338d`，446 个执行文件前后 SHA256 完全一致。最终交付提交仅增加本文和证据归档，不修改冻结代码/测试。证据中的 `FINAL_VALIDATION.json`、`independent-final/FINAL_SUMMARY.json`、每组 XML/raw/SQLite 和 `FROZEN_SOURCE.json` 支持上述计数；`MANIFEST.json` 给全部常规证据文件的 size/hash，外部 `SHA256SUMS` 给归档哈希。pytest symlink 不收入归档，不重复计算其目标文件。

交付分支为 `dev/pb-target-read-gates-20261013`。main/core dev/旧 P-B 分支保持既有 SHA，owner 的未提交工作保持既有哈希。远端交付完整 SHA 由交付 JSON 与最终回复记录；不声称远端 CI 绿。
