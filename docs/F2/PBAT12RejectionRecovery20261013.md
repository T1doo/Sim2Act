# AT-12：明确拒绝后的修正与原 key 恢复（2026-10-13）

父级已接受 P1 `0a05207b6a7f8af7f00cd26c913cb243a794c331`。本切片从该完整 SHA 创建 `dev/pb-at12-rejection-recovery-20261013`，root 为唯一产品写入者，独审只读产品。保持逐次目标读前门禁；只处理 P-B 逐次与保存规范默认运行的明确拒绝/未知结果状态，不扩展执行器、模型、权限或部署。

## 先实测的红例

- `red-invalid`：实际 HTTP 409（合成非法审批指纹），页面保留 pending，默认与逐次控件继续被锁；1 个预期 FAIL，56.98 秒，448 执行文件前后不变。原始两份新增测试源码已按红例的 SHA256 重建并逐文件核对；全 448 文件归档，未用后续修改源码冒充红例。
- `red-late-r2`：首个候选中，实际 HTTP 409 晚于导航返回；重开原实例依然 pending 永锁，1 个预期 FAIL，190.41 秒，449 文件稳定。第一轮因外部 pytest 未加载 fixture 的 1 ERROR 是测试入口错误，保留 raw；第二轮显式 `-p conftest` 才是产品实际红例。
- 默认 `create_app()` 使用有效 `db`，首版新 422 handler 却误用可为 None 的参数 `store`。在只替换 SQLite 构造器 test_only 标记、未传 store 的真实进程内 HTTP 探测中，schema 输入实际返回 500，独审和作者均复现。原生默认构造器拒绝 SQLite 的请求前 ValueError 也保留；不能称已运行 PG/生产原生启动。

首轮与二轮候选未完套件因具体已确认缺陷而对所属精确 pytest PID 发送 SIGINT，源映射均不变，所有原始 Return 2 / XML / SQLite 保留，不计最终 PASS。中断 XML 的 unnamed testcase 不能当真实通过。二轮 contract 中把 Goal 字典误作身份造成 ProgrammingError，也是夹具错误，保留失败并改用 fixture 的实际另一身份。导航探测的 15 秒等待先于实际 HTTP 回来导致 BrokenPipe，保留错误，新增有界等待为 180 秒；不把它当产品授权泄露。

## 拒绝证明与页面状态合同

普通 4xx、`effect_known=true`、`safe_retry=false` 不证明未受理：旧 accepted key 在撤权后仍可 403，错误 body 仍可 409。GET 恢复失败、HTTP 丢失、非 JSON、未验证的回执也不能解除重复提交保护。

明确拒绝证明为 `internal-run-rejection.v1`，绑定 endpoint、principal/project/instance、原 key 与完整精确 POST body 的规范 SHA256，并明确 `NOT_ACCEPTED`、`ABSENT` 和 `TX_ROLLED_BACK` 或 `VALIDATION_NOT_STARTED`。

- enqueue 保持既有单事务与项目锁；锁后仅用标量确认 instance 归属及该 actor/iid/key 没有既有 AppRun/请求账本。只有事务主体抛已知 DomainError、事务正常 rollback 退出才附证明。提交、回滚、连接异常、UNKNOWN、cached key 均不附证明。没有提前读取目标、结果或完整绑定。
- schema 422 handler 仅对这两个 POST 路由、有效身份/owned 项目/实例且原 key 不存在生成证明；使用有效 `db`。其余路径保留框架拒绝；数据库故障不伪造未受理。
- 前端只在初次 POST 的独立 catch 内核对整份证明及精确 body hash，然后只清同一 pending 对象。撤掉旧逐次预览及同意，必须再次明确选择、审阅、确认与新 key；不会自动 POST。
- 结果未知保持原 key GET 恢复，不自动重发，也不借后续 GET 的 403/404/UNKNOWN 清 pending。已接受但回执被污染同样保留。
- 晚拒绝的证据只结束原 map 中对应意图；旧 view 不向新页面显示回执。当前匹配实例/作用域的控件只按现有状态刷新。晚 accepted 202、身份/实例改变仍保留原意图，须回原 scope 核对。

实际 Worker、SQLite、HTTP 与离线页面均使用 synthetic 数据及模型 transport，真实/付费模型调用为零。每例纠正后的 C typed 成果新增，旧成功 B typed 行的 ID、内容、版本整行保留。出处核验没有变为语义验收。

## 验证边界

身份补充场景是显式的 token/connection generation 控制面切换，并用真实 synthetic B HTTP 身份读取；不是产品原生 UI 重连验收。实例补充场景以 API 准备第二实例，页面原生选择后释放晚回执。页面使用进程内 HTTP/JSDOM，不是原生浏览器。最终矩阵、精确冻结 SHA、独审计数及归档哈希在交付段追加；历史绿例不替代最终资格。

NOT RUN：PG、Windows、原生浏览器、原生 UI 身份重连、真实模型/付费 API、人工语义验收、完整通用 P-A/P-B、旧源码升级、来源退休、CI、部署；旧取消窗口保持 NOT_VERIFIED。main/core dev/已接受 P1 分支与 owner 未提交工作不得更改。

## 最终冻结与保留的运行历史

最终冻结为 `7c8f5a5570dec525395b29c1df7ae1981ba246ec`，最后按钮修复提交为 `e1bda50917623313312cb542527f3f3e0743c88b`。75 文件资格 pin 为 `f30ed15e59d042bdb14f44ccc9f16175f8340c6d83387f7821e7de293541c8ae`；原 anchor、CHANGED 边界、config 排除不变。全部 449 个执行文件有精确快照与运行前后映射。

独审最终 6 个唯一通过（5 个合同 + 1 个晚默认 UI），实际执行 7 次，其中首轮 UI 在页面启动前耗尽 fixture 的三次 Worker claim，1 FAIL 历史保留。实际发生两次 WORKER_LOST→RECONCILED，原 30 秒 lease、300 秒 accepted deadline 均未改；之后同源码单独重验该 UI 1 PASS，257.19 秒，13 项检查、20 个实际页面源码文件，冷 Worker 的 C 结果保存成功。不得将第一次失败归为按钮失败，也不以推测的 CPU 原因豁免失败。

作者减少并发后顺序验证页面：先通过实际 Worker 建立成功 B 的 SQLite 基线，每场景独立、逐字节复制该快照；没有修改任何行、时钟、预算或 claim 上限。每次 C 都是新的明确审批、真实 HTTP 提交及实际冷 Worker，旧 B 行逐字段核对不变。这是在同一保存逻辑与真实历史上验证不同错误/恢复路径，不用旧 C 成果替代本次成果。共享基线与各冷副本、代码、HTTP raw、模型 synthetic wire、XML 全部保留。

独审另指出并经 `r3-late-ui` 实际验证的派生控件遗漏：两例中晚逐次 409 为 PASS，晚默认 422 后 `pb-use-material` 仍禁用为 FAIL（1 PASS / 1 FAIL，482.02 秒，449 文件稳定）。最终仅补同 iid/token/project 的当前 P-B buttons 刷新，闭包仍自验当前 view/身份，不改新 review 或显示旧响应。该失败与修复后的独审实际 UI PASS 分开记录。

本切片之后的关键剩余能力仍是清单中的更宽 P-B 任务可信整体验收、稳定逻辑的适用范围，以及实际用户新/错误输入评价，有限合成 AT-12 不替代这些验收。可独立并行完整页面路径、有限确定性 oracle 与来源/授权边界独审；保持唯一集成人员，真实 provider 与语义验收继续需要原声明的真实条件。本轮不新增该产品范围。

## 最终交付计数

最终断言覆盖 **43 个 unique PASS / 0 未解决 FAIL / 0 ERROR / 0 SKIP**：合同与资格 27、完整 AT-12 页面 9、P1 原读前门禁 5、身份/实例切换 2。作者实际执行 44 次，有 1 次到期例的 Worker 准备失败（尚未到到期断言）；其 claim/fence/clock 原样保留，同源码、同预算、同 lease 单独重验 1 PASS，194.49 秒。独审覆盖 6 个 unique PASS，全部与作者重叠；实际执行 7 次，另保留 1 次 Worker 准备失败。两者共有 49 次通过执行、43 个唯一覆盖，最终这一家族实际执行 51 次、2 个历史失败；不是“全部执行从未失败”。此前红轮、夹具错误和中断不删除，也不计入最终通过分母。

9 页面场景为 118 项检查，2 切换补充场景为 27 项，共 **11 场景 / 145 检查**。各例加载 20 个当前实际页面源码文件；身份场景仍是前述控制面模拟，不宣称原生 UI 重连。原 P1 的撤权/自然到期五入口最终均为 `403,403,200,403,403`，C protected-cell/full-binding SELECT 各零，查询前后 DB 不变；合法旧 B 仍可读取，晚任务/未知结果没有重复 POST。

全 449 个执行文件始终为上述精确冻结版本，独审 75 文件资格通过。Ruff PASS；mypy 在 76 文件仍有 `status_report.py` 三个、`tools.py` 两个既有错误，不称全项目类型检查绿。真实/付费模型请求 0。归档包含全部 regular 文件的 size/SHA256 MANIFEST、raw/XML/SQLite、精确源码及原失败；pytest symlink 不归档，不重复计算目标文件。最终交付提交仅增加本文与证据，冻结代码/测试不再变化。完整远端 SHA 与 clean/ahead/behind、owner 哈希核验记录于交付 JSON；不声称 CI 绿。
