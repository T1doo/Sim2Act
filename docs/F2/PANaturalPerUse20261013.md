# 已保存 P-A 应用的每次材料 / Goal 输入（2026-10-13）

从已有限接收并核远端的 `cb128cd7138f3e91678e640489579049b907769c` 创建 `dev/pa-natural-per-use-20261013`；root 是唯一产品集成写入者，既有独审仅生成外部证据。原方案 P-A §5 与 F2-T02 要求保存可处理新输入的应用；AT-10 专指 P-B 冷会话提取，本次 P-A 未见资料复用对应 AT-11，两路分别验收。本工程不关闭完整 P-A/P-B 或 R0 验收。

## 有限输入合同及实际结果

仅支持已明确保存的自然规范 P-A 应用（goal_application 或 spec_binding 来源）；不扩标签型、字面检索、任意应用或任意执行器。沿用保存的自然规范 recipe、模型契约、正常可取消 Worker、原 app / Release / instance。材料仍是当前获授权的单份 TXT/MD，至多 2048 UTF8 字节 / 40 行；新 Goal 必须精确绑定该材料。旧 Release 的空 input_schema 和默认材料绑定保留；新输入使用明确、封印的 per-use 协议作为每个新 Run 的独立 overlay，不改原 Release 或默认运行语义。

页面从保存应用的实例打开共用逐次使用表单，选择此次材料与已保存 Goal，显示原应用、recipe、当前版本、完整目标/标准、材料、精确所需 READ/SAVE 及有界模型节点/保存预算，再明确确认。`pa-natural-per-run.v1` 使用 `/api/internal/instances/{iid}/pa-use-reviews`、`pa-use-runs` 与 `pa-use-requests/{key}`，同意值为 `RUN_THIS_SAVED_PA_LOGIC_WITH_THIS_EXACT_GOAL_MATERIAL_AND_READ_GRANT`。每实例该协议最多 64 个受理请求；真实模型 allowance=0。

实际正例在同一保存 P-A 应用、Release、实例保留原 SOURCE 的 v1，依次使用 COLD 与第三份未见 THIRD，当前正常 Worker 产生 v2、v3。第三份实际模型输入仅含第三份材料和本次 Goal，不含前两份答案。旧 typed 行、应用、Release、Goal 和人工账本保持；新 Run / AppRun ID 及 typed 版本不同，新 owner 从 PENDING 和空选择开始，另作显式合成人工声明。机器成果仍 semantic UNKNOWN / NOT_RUN，人工声明不改写机器 PENDING，也不开放发布。

原生成来源和旧材料的当前授权仍用于保存应用的来源审计。不能称完全无旧私有材料读取、来源退休、任意 Goal 泛化或真实语义修复。

## 同一个权限、事务与恢复实现

复用 `pb_natural_uses.py` 内的有限 Family 描述符和同一 review / approve / seal / bound / audit / recovery / control 路径；没有复制 P-B 执行器或权限流程。P-B 旧 namespace、kind、同意值、请求形状及历史快照不变。P-A 保留 goal origin 与原 goal_application/spec_binding，并使用既有 P-A 来源验证/audit；不会伪装为 P-B task_run/spec_task，也不把无来源标记的候选默认当作 P-A。

共享 ReviewInput 绑定本人项目、app/runtime/instance、revision、Release/app/recipe 指纹、材料 ID/hash、Goal ID/version/fingerprint、原请求 key。P-A/P-B 使用各自精确 CommitInput 和独立路由；当前 OpenAPI 实际核得 PACommitInput / CommitInput 的严格字段及各自同意常量，不接受宽 union。

预览只读取当前用户授权材料并验证当前 app 的来源与 SAVE 权限，不运行模型或写成果。确认在项目事务锁内重新核全部目标、版本、当前 READ/SAVE 和 app target grant 前态/自然到期；显式同意仅为该 app 取得该份材料的最小 READ，既有 SAVE 权限不扩大。每次运行的受理、目标封印、app scope、binding、AppRun 与事件同事务；失败不留下 Run、grant 或成果的部分写入。已有 key 只能恢复同一请求；变更意图或默认运行重用同 key 被拒绝。

P-A 专用 `pa_base_data_version` 冻结确认时的结果版本，避免要求旧 P-B 快照具有新字段。执行前及提交门重查当前来源权限、Goal、instance/Release、fence、原时钟和证明。运行中只允许基线版本或精确本次 AppRun 已 SUCCEEDED、typed 同 aid/base+1 的自身最后保存阶段；其他 Run 抢先保存新版本时迟到结果不能提交。正常暂停/取消走本人受理元数据，撤权后仍可取消，不重授来源权限。

共享私有读取门识别 app 与 Release 的独立自然规范 namespace，以及各家族的独立 Run、ledger 和 snapshot 标记。删除全部运行标记不能把 P-A 降级为不需上下文的 typed / Run 全文读取。来源 READ 授权前只读标量关联；屏障证明有限受保护 cell 未被读取，不冒称整个底层 JSON 从未评价。

未知网络结果仅以原 key GET 恢复。共用页面 pending 绑定 token / project / app / instance / Release / family，冻结连接、工作区、编辑和 hash 等待代次，未知意图锁住该实例的默认与逐次使用提交。明确未受理必须具有本人精确 endpoint、完整 body hash、原 key 不存在及回滚证明；500、失败 GET、已有 key 或迟到其他 scope 不清当前意图。

预览完整性还校验 target_goal 的版本、指纹、完整快照对原前置 GET 的 Goal；内层 snapshot hash、effective candidate hash、候选 Goal 与 manifest.goal_ref 一致。外层自签名不能替换展示给用户的目标或标准。每个异步 hash 后重新核页面代次。

## 实际红例与终态证据

首个夹具 FAIL 是误读 Release 回执 envelope。修正夹具后，实际新 P-A 入队 409：共用 bound 误要求未持久化的 base_data_version，事务回滚；修为 PA-only 字段，旧 P-B 不读取该字段。

独立发现的全标记降级疑点实际产生红例：自然 P-A app / Release 不改、删除运行标记并撤销 READ 后，无上下文 lifecycle.data_rows 读取命中 typed 私有 cell，SQLite UDF 阻断。补独立自然规范 app / Release 保护后，同例实际拒绝且零受保护 cell / 完整 binding 读取。此 UDF 是测试屏障，不是工具授权拒绝。

第二、第三份实际 Worker 已成功时，人工声明测试又误读顶层 status 导致夹具 FAIL，改为当前实际 owner 状态核验。后续 13 个后端节点全部 PASS。页面首个 FAIL 是 JSDOM 缺 structuredClone，补的是 Node 原生测试 primitive；后一个 FAIL 是手动刷新与既有终态轮询同时重建，夹具在 owner 控件尚隐藏时立即操作。外部完整可见诊断等待真实控件就绪后 PASS；最终测试仅等待控件可见且含本次 Run，不强制显示、不以后台 API 代替页面手势。

实际 sibling Worker 竞争夹具先因模型 callback 内嵌 asyncio.run 失败，原 attempt/数据库保留。改为真正独立线程的另一个正常 Worker 后，在不改时钟、租约、预算或 claim 上限下完成：兄弟正常 Run 保存 v2，原 P-A 的迟到响应保持 REJECTED_KNOWN，不写新材料成果。

独立 UI 红例确证原预览仅核 target_goal.card_id：修改正文/验收标准并重算合法外层摘要后，页面显示伪 Goal 并启用 ack。没有错误 Run POST，也不声称真实网络攻击。补完整 Goal 与候选锚后，实际同一污染被拒；family/recipe 污染、未知 POST 后两次失败 GET、hash 等待切工作区、A 的迟到回滚保留 B 均通过。原红/夹具失败、完整 raw/XML/SQLite、源映射及不同源快照保留。汇总脚本误读独审 JSON 的 tests/result 字段的失败也保留，非产品测试失败。

最终产品冻结 `98beb4f9794115530f91018b9a0844cac91bb26f`，core `06b469bf8baf2e5bb54d76344f69c6730000cee7`。76 Python 文件资格 pin `5d6d0119083355df42381467aafacac7454f0055ee4bbd1672916dadb4385f91`，cb128 原 anchor / CHANGED / config 排除不变。459 个 src/tests/pyproject 执行文件各轮前后稳定。独审桥证明运行权限核心自 e8bf 未变、共享路由精确 schema 自 a6 未变；新 UI 完整锚在最终源重新运行。

当前 **51 unique PASS / 53 次 PASS 执行 / 0 未解决 FAIL / ERROR / SKIP**：作者 25 unique / 27 次，独立资格及旧文字 owner 23 / 23，独立当前控制器 3 / 3。作者仅重复 P-A 正例与 P-B fresh Worker 各一次；早期独立候选及额外页面就绪诊断不加终态计数。后端包含新材料/Goal 和非法输入、自然到期、撤权/SAVE 撤权、取消、错误输出、Goal/revision/fence 变化、目标读取门、重复 key、全标记降级、真实竞争、旧 P-B 历史证明及旧 P-A correction 回归。

最终实际页面三条（P-A 正常、P-A 丢失受理回执、旧 P-B 正常）共 **82 项检查 / 127 次可见有效手势**，每次页面加载 20 个当前源码资源；P-B 冷页面再打开一次。P-A 两条使用实际第三份正常新 Worker 并完成另一次合成人工声明。另 3 控制器探针 / 22 内部检查独列，不能当完整可见用户路径。

源码及新增测试 Ruff、internal.js 语法 PASS；全 tests Ruff 仍有 29 个既有格式错误，mypy 仍有 status_report.py 三个与 tools.py 两个既有错误（77 文件）。动态路由类型引入的 4 个新 mypy 错误已修；不称全仓静态检查绿。

NOT RUN：真实/付费模型、真实人工语义、PG、Windows、原生浏览器/身份重连、完整通用 P-A/P-B、旧源码升级、来源退休、远端 CI、部署。既有浏览器拒绝路径未重试。没有凭据配置、网络权限扩大、部署、强推或 main/core dev 写入。

归档包含 SUMMARY.json 的具名执行计数、完整历史表、worker claims、API/页面回执及独审；仅 regular 文件，不计 pytest current symlink。交付只新增本文与证据包；完整远端 SHA、归档 SHA256、本地/远端差异及旧 WIP 哈希核验见 `/workspace/pa-natural-use-delivery-final-20261013.json`。

最终证据包：`docs/evidence/pa-natural-use-20261013/pa-natural-use-evidence-20261013.tar.gz`，SHA256 `6a35d5293b1ebd6cc1ff3df5953464b5d70b64a976b4f04b916155b5f2717e39`；9264 个 regular 成员、222941314 字节逐项回读 size/SHA256 通过。
