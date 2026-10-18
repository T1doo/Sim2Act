# f5 主路径只读优先级核对

观察 HEAD：`f5d6cedb26fe549ad274951892a219c0b34b32b9`；最初工作树干净。
本任务只读取产品文档、源码、测试定义和已经封存的证据。未运行产品测试，
未修改仓库或旧原件；本报告是新的外部文件。父级后来通知 f5 独审有限通过。

## 结论

**第一优先为 fresh 执行原 P-B continuous 正例，关闭当前源码的资格缺口。**
不是重新实现 P-B，也不是增加新的恢复/故障矩阵。当前没有从只读核对中发现
必须先新造执行器、Grant 或模型授权才能完成这条正常产品主链的证据。

原方案 F2-T03、F2-T05 与 AT-10 分别位于
`docs/分阶段开发计划.md:95`、`:97`、`:358`；产品 P-B 与两路径独立计分要求在
`docs/平台产品设计.md:117–127`。P-A valid 新近成功不能代签 P-B。

## 已存在能力，不能重复列为“缺失”

| 路径 | 实际源码 | 已有工程证明与边界 |
| --- | --- | --- |
| 统一目录选择 P-A/P-B | `web/use.js:59–64` | `docs/evidence/natural-application-entry-20261016/README.md:16` 已分别通过 P-A/P-B v1→v2；当前 f5 的完整此路径资格未由本次只读工作重新取得。 |
| 明确新材料和自己的 Goal | `web/internal.js:1112–1139` | 同一 entry 原 CJS `tests/natural_application_entry.cjs:64–87` 明确选择、精确预览、确认及单次提交；不是新功能缺口。 |
| 同 Run 结果与逐项人工声明 | `owner_acceptance.py:676–729`；`natural_application_entry.cjs:53–58,93–98` | entry 旧 P-B 正例实际逐项 ACCEPT、冷页 GET 保留；`test_natural_spec_owner_ui.py:9–10` 也有 P-B reject/decision-lost。合成声明不等于真实语义验收。新 PA valid 仅 PENDING 入口边界，见其 README:12。 |
| 成功任务→编辑图→新 P-B→Release/实例→统一入口新材料 | `web/internal.js:714–780`、`:1109–1166` | 原 e039 continuous 正例 63 checks、68 手势，已通过；新 P-B 首次 v1、没有人工 DECIDE。这些范围在 `NaturalPBProductFlow20261016.md:16` 和证据 README:17–21 明确。 |
| 两次依赖调整与新材料运行 | `natural_logic_patches.py:92–115`；`web/internal.js:1179–1195` | R0→R1→R2、P-B 完整子项及普通 P-A/P-B per-use 均有旧源实测；`NaturalLogicSecondRevision20261014.md` 记 64 唯一 PASS，不能称其缺失。仅 requirements→qualifiers 有限依赖、最多两次调整。 |
| 项目范围保守重验 | `project_natural_revalidation.py:113–165` | 只支持完整项目 1–2 个六步双模型自然 app；全部 CHECK 也固定 BLOCKED_UNKNOWN/NOT_ACCEPTED。`ProjectNaturalRevalidation20261014.md:7–15` 和后续 74 唯一 PASS 明确这一有限范围。不可改标为完整项目依赖闭包。 |

以上源码路径均相对 `src/sim2act/`，测试与文档路径相对仓库根。

## 明确优先级与授权内最小动作

### 1. 当前 P-B continuous 正常路径资格（最高）

直接复用原节点
`tests/test_pb_natural_product_flow.py::test_successful_source_to_pb_directory_and_new_material`。
它在 `:19–41` 只预置真实成功来源；页面自行保存目标 TXT/MD 和完整 Goal，
编辑有限图、明确提取、原 key 恢复、内部 Release/实例、目录返回，再明确保存
另一材料/Goal并运行。Python `:112–121` 用正常 cold Worker+MockTransport；
`:156–162` 精确要求新 P-B 只有 v1 且 owner journal 未写。

已有 PASS 是 e039 历史资格；当前 f5 的 PA 完整页证据 README:39 明确未执行
完整 P-B。本轮不得拿旧 63 checks 当 f5 当前通过，但也不得把未重跑说成产品缺失。

最小动作：正常开发分支只给原节点补增量 RPC/HTTP/Worker 进度、失败 finally
证据和有限自有进程 watchdog，保留原业务 oracle、有限 wait、mock 请求槽与
Run deadline，fresh 跑这一个原节点。Python 当前 `:66` 阻塞 IPC loop 无外层
watchdog，`:170–180` 的 wire/保留证明多在断言成功后才落盘；补观测有具体依据。
发生失败仅定位实际最后 RPC/HTTP/Worker 阶段，再最小修复，不先扩邻近矩阵。

### 2. 同一冻结下 P-B 目录→新材料/Goal→同 Run 人工 ACCEPT（次级资格）

如需要在同一当前源码交付中明确包含人工声明，复用现有
`tests/test_natural_application_entry.py::test_saved_natural_app_visible_use_entry[pb-normal]`
一个节点，而不是复制新包装。它使用真实旧 v1、同 iid 新 v2、逐项显式 ACCEPT
及冷 GET；原定义在 `:21–39`，完整 oracle 在 CJS `:88–98`。它与 priority 1 的
continuous 首次 v1/PENDING 分母分开，不能把两个节点拼成“一次完整全绿大套件”。

无需重跑已覆盖 decision-lost/晚回调/重启/撤权故障整模块，除非主链实际失败
给出新的相关证据。真实模型、真实用户或语义验收均保持 NOT_RUN。

### 3. 真正可见的后续功能限制：P-B 提取未知回执的冷页原 key 入口

这是源码已明确的产品限制，非本次新确认 P1，也不优先打断第 1 项正常主链。
`web/internal.js:65` 的 `naturalTaskRequests` 只是 Map；`:765` 将冻结提取意图
只保存在该 Map；`:675–679` 恢复按钮只有 pending 时才可见/可用；`:709` 创建
恢复按钮但没有手工原 key 输入。冷页面重新执行脚本后 Map 为空，因此现 UI
没有让用户输入原提取 key 并恢复未知已受理提取的入口。没有声称已动态复现重复
提取，也不把旧“本页丢 201 后恢复通过”扩大成冷页恢复通过。

后端现成 `pb_natural_specs.py:505–520` 支持 scoped by-key GET，先 source gate，
完整核 draft/精确请求/review/保存物，未找到则 OUTCOME_UNKNOWN。
文档 `NaturalPBProductFlow20261016.md:7` 已承认本页内存不等于冷页发现。

若第 1 项通过后要继续交付可见功能，最小范围是显示可复制原 key，冷页在原
成功来源下手工输入 key，只调用现成 GET，完整核主体/项目/来源/请求指纹后
展示已存草案与明确打开入口；找不到仍 unknown，不自动换 key/POST，不把私有
材料正文或 token 持久化。先给出具体冻结合同，再做单个实际冷页 happy-path，
而不是恢复矩阵或新 executor/Grant。此限制也存在共享 per-use Map，但不要
顺手扩成所有流程的持久存储改造。

## 不应作为当前“下一功能”扩展

- 已有两次局部依赖开关及人工锁/未知依赖扩验已多轮证明，不为凑新产物再次包装。
- PROJECT UNKNOWN 保守拒绝是当前合同，不能靠增加通过标签或提高 max-members
  来宣称依赖完整；若以后扩展，需要真实独立依赖合同，超出本次最小下一步。
- LIVE 模型/真实场景/Windows/native/PG/远端 CI/部署未执行，不冒称通过。
- 永久取消的旧 P-B 安装窗口保持 NOT_VERIFIED，不重试、不改名、不换工具/环境；
  上述正常 continuous case 不包含该被取消操作。
