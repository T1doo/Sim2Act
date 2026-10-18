# 本地记录写入的同 Run 控制

从 `5f25e6c7dcbc024294d3640e3e9010e3bae9609c` 接续。原 F2-T09 与产品 §8.2 要求用户明确控制已受理任务。本地记录后台已有暂停、继续、取消的专用版本化控制接口，页面却只有提交和读取。本片补上这个实际使用缺口，不再包装历史，也不扩大原故障矩阵。

用户在原应用中选择实例和 Run，点击“读取所选同一 Run”，才可按当前状态明确暂停、继续或取消。每次按钮使用已核版本；双击只发一次请求。控制回执只显示状态与版本，原完整 Run 正文清除，成果仍须重新读取。暂停/取消不声称撤销此前已保存记录。

复用现有专用 `/commands`：严格核六字段、同 Run、准确状态转换、version+1、content_access=false 和未发布标记。未知回执保留该范围的内存控制意图，锁住控制，只允许明确 GET；相同版本不解除未知，版本推进只确认当前状态，不认领原命令。已知拒绝也须先重新读取。账号连接、项目、工作区、应用、实例、Run/读取代次及原 Map intent 共同隔离迟到回调。既有业务 durable intent、权限、工具和版本边界保持；没有新 API、executor、Grant、表或撤权 metadata 读取合同。

唯一实际页面链使用正常 preview/commit 得到的 QUEUED 合成 Run：pause(v1)→PAUSED/v2；resume(v2)→QUEUED/v3，实际 200 回执跨第二空实例延迟交付；回原实例明确读取后 cancel(v3)→CANCELLED/v4，实际受理后丢失回执；明确 GET 核当前终态，再冷页读取。页面 **22检查通过、39 API（36GET+3POST）、54资产、2次 boot**。三次控制均双击，合计恰三次 POST；无自动跟读或重发，没有新业务记录、成果或模型调用。

原 pytest 包装 **FAIL/17.24秒，外层25.023秒**：页面及正常 Worker.once 未领取断言已通过，随后全表比较漏算该探针自身写入的心跳。原 JUnit、NOT_COMPLETED summary、HTTP、IPC、55表完整前后导出保留。另一个只读闭合 JSON pytest **PASS/1.02秒**，补核原 Run/AppRun、三条 COMMAND、唯一新心跳和其余51表不变。原 inline probe.id 未单独捕获，不能称精确比对过当时对象；未来 harness 已补捕获。修正后的实际包装未重跑，不能写成整条 pytest 全绿。产品与 CJS 完全等于实际页面输入；原 Python 测试为明确标注的精确 hash 重构。

[原件、字节桥及有限独审](../evidence/local-record-controls-20261018/README.md)。实际仅排队控制；RUNNING 边界、UNKNOWN 同版本 GET 与已知拒绝后读取本轮只做源码核查。原生浏览器、Windows、PG、真实人工/语义、远端CI未执行。真实模型及外部 API 调用为0；真实账户官方 source 和可执行零新增费用依据仍缺失。旧修正链 pytest FAIL 与同 Run 后续 PASS 继续分列。未探测远端、推送、部署或触碰旧封存、旧实例及私有 holdout。
