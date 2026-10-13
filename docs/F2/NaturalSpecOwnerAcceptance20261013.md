# 自然规范成果：本次 Goal 与精确结果的人工验收（2026-10-13）

从已接受 `e21f389fe463474bb659a1c86c48c31640a2f901` 创建 `dev/natural-spec-owner-acceptance-20261013`，root 是唯一产品写入者。依据 `docs/分阶段开发计划.md` 的 F2-T01、T02、T03、T06、T09，以及 `docs/sources/V5/平台产品设计.md` §11：自动引用定位只证明出处，语义成果需要固定人工量表。本切片提供实际审阅与声明入口；测试中的选择是合成人工判断，不能当真实用户语义验收。

## 有限合同与实际用户路径

仅支持已经成功保存的自然规范 P-A / P-B 成果，一个明确选择的 Run，实例最新结果版本。页面显示本次实际 Goal、原文、引用、条件、例外、关联与未决项；用户冻结预览，逐项选择接受或要求修正并填写理由，再明确勾选人工判断。服务端记录 `ACCEPTED` / `REJECTED`，支持取消预览和撤销声明。要求修正不自动调用模型或改写成果。

`owner.natural-spec.v1` 使用 `/api/internal/instances/{iid}/runs/{rid}/spec-owner-review` 与 `-requests`。PREPARE 冻结完整上下文指纹，15 分钟有效；DECIDE 绑定具体 review ID、指纹、顺序、每项选择与理由。最多 100 个标准、每 Run 256 条声明。另建 `natural_owner_records` / `natural_owner_seals`，按 Run 分区、顺序与原请求 key 唯一，只追加；原文字 owner 表及合同不改。其他材料的声明正文不会因当前 Run 的权限而被读出。

新结果、新 Goal 版本或当前 Release / 授权变化，使旧当前声明 STALE，旧回执保留。新 Run 从 PENDING 开始，不继承旧接受。机器成果中的 owner PENDING、semantic UNKNOWN / semantic_goal_acceptance NOT_RUN 保持原样；人工声明分开呈现，正式发布关闭。

## 权限、版本与提交门

先核本人项目、实例与 Run 的标量关联，再核本次材料权限；独立 ACCEPTED 的 iid/aid 必须与路由相符。成果指针的 SPEC_COMMITTED、已验证 SAVE effect、AppRun.output.resource_id、typed.data.result.resource_id 四处必须一致，先授权成果 READ，再读完整 Run、实际 Worker 证明、typed 成果或人工声明正文。

合同绑定本次 Goal 的精确版本和指纹、材料、保存 Release 与有效计划、Run / AppRun、实例版本、结果版本、typed 和 output 指纹、实际操作证明、grant 快照。提交末再核材料/成果权限、Goal、typed 指纹/版本/Release、实例版本、Run 成功且无取消、grant 与预览期限；任何失败回滚声明及 seal，不留下部分写入。停止控制只需本人元数据，可在材料或成果撤权后执行。

未知网络回执只以原 key GET 恢复。初次 POST 的明确拒绝仅在服务端证明本人精确意图原 key 不存在且事务已回滚、状态/错误类别正确时清除原 scope 的 pending。已有 key、失败 GET、500、网络丢失或绑定不符不能作为未受理证明。页面冻结 token/连接/项目/实例/Run、请求对象及读写代次；迟到响应不会换入其他 Run，预览摘要等待期间切换也不会提交旧意图。完整 payload 指纹及当前合同比对防止展示标准与服务端冻结标准不同。

## 已保留的失败与验证范围

首轮实际 HTTP 发现不存在的 `goal_cards.owner_id` 引用，1 FAIL；修为当前本人项目下的 Goal head。另一个早期 FAIL 是快照夹具错误地要求新增人工账本也不变化。中间两个明确中断轮次保留 Return 2、源映射、SQLite 与 XML；每轮只有 4 个具名通过，XML 的 unnamed 中断节点不算 PASS。

产品最终冻结 `c156b85654021d29703d61939b8bdd78cef97a65`，功能 core `922fba6c15751df08b7f7e862123e868265ebe6f`。75 Python 文件资格 pin `eb1bb6c9b4cfbbd7cd78e6632aa63dd6a457ec5bdaf0fe8d397aa25d019a7cfc`，原 anchor、CHANGED 边界与 config 排除不变。之后 `4dd028bb0f76eff725174dcb7a2a95db3d74a793` 只修测试屏障与实际 400 预期，产品字节不变。

最终作者矩阵先实跑 17 例：13 PASS、4 FAIL。三处失败是屏障把精确资源 ID 的 JSON_EXTRACT 也当完整正文阻挡；一处是 INVALID_INPUT 实际 400、夹具仅期待 409/422。保留全部 raw、XML、数据库后，只重验受影响 7 例（包括两个重叠和新增屏障校准），7 PASS。最新作者覆盖 18 unique PASS、20 次 PASS 执行，未解决 FAIL/ERROR/SKIP 为 0；不是“全部执行从未失败”。

屏障例外仅限两条完整固定 SQL 及资源 ID 路径，单独记录 scope_identifier_reads；SQLite 为提取标量仍会评价底层 JSON，不能声称零底层 JSON 读取。校准实际阻挡完整 Run.result、AppRun.output、typed.data、owner.payload 和其他 JSON 字段；撤权/过期及双成果指针污染例证明没有完整受保护正文进入应用读取路径。

作者三个实际 HTTP/JSDOM 页面场景（P-A 接受、P-B 要求修正、P-B 丢失决定回执）共 95 项检查、154 次可见有效手势，每场景加载 20 个实际源码资源。独立资格与旧文字 owner 回归 23 PASS（22 + 1），与作者节点不重叠。其旧 fa14 23 PASS 历史另存，不能代签最终产品。两者当前合计 41 unique PASS、43 次 PASS 执行；额外页面独审将在证据交付段记录。

为减少重复准备，空人工账本的 P-A/P-B SQLite 基线由实际正常 Worker 在 fa14 候选生成，保留精确源与 claim 证明；各场景逐字节复制成功历史，再用最终产品完整重新验证。没有改行、时钟、预算或 claim 上限；新结果失效例还用最终代码运行新的实际 Worker。基线并非最终版本重新生成成果的证明，也不以合成 transport 冒称真实模型。全部 452 执行文件的前后映射、不同源版本、未变化函数 AST 闭包及原失败保留。

Ruff PASS；mypy 仍为 status_report.py 三个、tools.py 两个既有错误（76 文件），新增 guard 注解错误已修，不称全项目类型检查绿。

NOT RUN：PG、Windows、原生浏览器、原生 UI 身份重连、真实/付费模型、真实人工语义验收、完整通用 P-A/P-B、旧源码升级、来源退休、远端 CI、部署。原浏览器拒绝路径未重试。main/core dev/旧 owner 未提交工作不改。

下一关键剩余能力是实际用户依据完整 Goal 与材料评估含义、完整性和修正后的新结果，以及更宽 P-B 逻辑的适用范围；本切片不代替这些验收。页面错输入/恢复、有限确定性 oracle、权限/来源独审可独立并行，仍由单一集成人员写产品。

## 独立页面故障探针与交付

最终测试闭包 `4dd028bb0f76eff725174dcb7a2a95db3d74a793` 的额外独审实际 3 PASS / 0 FAIL / ERROR / SKIP，8.44 秒，452 文件前后零差异：完整 payload 标准污染被拒；HTTP 500 即使带伪装的未受理证明仍保留原 pending、无重发；A 的明确 409 迟到时只清 A 的精确 pending，保留 B 状态与意图。这是实际当前 asset 的 JSDOM 控制器故障探针，使用当前进程内 HTTP PREPARE 获得完整封印状态；不是三条额外完整可见用户路径，也没有重跑 Worker。其他预备场景未执行。

最终合计 **44 unique PASS / 46 次 PASS 执行 / 0 未解决 FAIL / 0 ERROR / 0 SKIP**：作者 18 unique / 20 次、独立资格及旧 owner 23 / 23、独立控制器故障 3 / 3。唯一重叠是作者材料撤权/过期的两个复验；三个团队集合间不重叠。原六个实际失败、两轮中断、早期独立 collection exit 4 和旧源成功历史均保留，不能说所有执行均无失败。

归档包含原失败与终态 raw/XML/SQLite、Worker claim 记录、源文件映射及快照、资格与独审、固定两条 SQL scope 标量评价日志和正文阻挡校准。只归档 regular 文件，不重复计算 pytest symlink；未包含凭据或旧 owner WIP。交付提交只添加本文与证据；完整远端 SHA、归档 SHA256、clean/ahead/behind、保护引用和旧 WIP 哈希的最终核对见本任务交付 JSON。

证据归档：`docs/evidence/natural-spec-owner-acceptance-20261013/natural-spec-owner-evidence-20261013.tar.gz`，SHA256 `13c4ca5aa7a65d3e2f274b2a61a31166496ef331c89a151dad4c372caf64593e`；5615 个 regular 成员、160742455 字节逐项回读 size/SHA256 核验通过。
