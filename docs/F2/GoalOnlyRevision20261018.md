# 保留 CSV 列的 Goal 局部修订（2026-10-18）

基线 `be9e8a6d55e6f2c3c0b4e153f75d7545d8519f6b`。原产品 §9.1–9.4 与 F2-T07 要求以稳定节点、类型依赖和基线版本求影响，保留无关对象，锁冲突拒绝，未知依赖保守重验；不能让生成器自行定义应变/保留集。

## 实现前范围与验收合同

当前 `csv_goal_revisions.calculate` 强制下一 Goal 同时选择不同列；已采用版本的 `csv_column_revisions.calculate` 也如此。现有 Goal 编辑、完整不可变版本、DeliveryGraph、preview/check 双 seal、隔离原 Worker、版本批准、同实例 CAS 和逐 Run owner 入口都已存在。本片只放开“同一 GoalCard 明确保存下一版本，保留明确选定原列”，复用以上原合同和页面；不新增编辑器、工具、执行器、权限或发布途径。

- 只支持现有生成的单节点 CSV 求和家族；新 Goal 的材料引用及快照必须与原规定相同。初次仍要求 original+1；续修仍限已采用 Goal 或明确下一版本，保留原8版上限。新目标不被解释为自动更改计算。
- 新 Goal 内容改变且列相同：明确修改节点仅 GOAL；ACTION/成果/检查/包装按原图影响及 APP 未知依赖重验。列也改变时保留原 GOAL+ACTION 请求；仅列改变的原续修不变。同 Goal 内容与列均未改变时拒绝无操作。
- 沿用已有规格修订：新版本固定本次明确选定列（初版原本允许多列时，这个输入约束收窄须在精确快照中可见），manifest/action/binding revision 继续按原机制递增；保留稳定 ID、工具引用、输出 schema、来源、权限和限额。原 canonical draft、旧 Release、实例历史结果和原 owner 声明不重写。
- 新 Goal 内容不是已满足的证明。即使新旧计算都为30，机器 PASS 仍为结构/精确求和，语义 UNKNOWN，新 Run owner PENDING；不得继承旧 ACCEPTED。
- 页面使用原两个列下拉：明确选相同列表示保留，文案和检查确认说明可只修订 Goal。仍分别确认 CHECK、内部 Release 和采用，无额外自动 POST；忙碌/原键/迟到选择/拒绝证明边界沿用，不增故障矩阵。

最小实际窗口：合成 amount=10/20 的原成果与显式合成 owner ACCEPTED；页面保存同卡新 Goal（amount不变、增加验收条目）、明确 amount→amount、单一 preview（双击不重复）、独立 NoModel CHECK、精确内部版本及 CAS，原实例新 Run 仍30但冻结新 Goal/验收且 owner PENDING。旧结果与原 ACCEPTED 记录字节保留；原 owner 合同只针对当前实例最新结果，切换后旧声明当前状态应为 STALE，不能为展示历史而放松此门。另在已采用版本保存下一 Goal并以同列接受续修 preview，核 GOAL-only影响请求及稳定定义；不为第二preview重复完整旧链。补无操作拒绝及既有不同列历史重算兼容的有限 API 核验。完整55表快照、精确 Worker 对象/claim、HTTP/执行字节和原始失败分别留存。

不执行真实模型、语义解释/真人验收、正式发布/部署、Windows/原生浏览器、PG或远端 CI；真实来源及可强制零费缺项继续保留。此前Git认证拒绝不重试，旧封存原件及私有留出集不读取或改写。

## 实际结论及原始失败

- 首次执行 **1PASS＋1FAIL/163.89秒**，外层173.199529秒。API兼容例通过：新代码允许既有不同列 preview/原键重算，拒绝同内容同列初次无操作；该例仅保存执行断言和 DTO，未另导出其55表快照，不冒充改码前软件/账本资格。
- 页面实际完成 Goal v2、amount→amount、隔离 CHECK、独立 Release、原实例 CAS 和新业务 Run。三个明确 NoModel Worker 各领取一次（旧业务/CHECK/新业务，均 fence1、SUCCEEDED）；95条原始 HTTP 保留。新结果仍30、result_version2、新 owner PENDING；旧 ACCEPTED 原行保留，派生状态为 STALE。主体/Grant/资源/原草案全等，旧 Release/typed/AppRun/contract/owner/seal 原行保留。
- **FAIL 是 Python oracle 查错 DTO**：测试在通用 `run_contracts.snapshot` 中寻找完整验收条目，原 F1 GoalSpec 只是投影。完整 Goal 已位于既有 `internal_run_bindings.snapshot.csv_goal`，与实际201 preview 的 context、GoalCard v2 保存快照和指纹完全相等；独立纯 JSON 核验 SHA-256 为 `11fbe8735f5e208eb57bb0dee443eb237a220c54629aebd44fbdee6141dabb2e`。没有因此修改产品门或扩大执行能力。
- 原 Python 断言后清理自建 Node，**首轮 page-proof 未生成，检查数量不补称恢复**。未来测试修正绑定字段并加入完整等值断言；CJS增加即时检查原件和显式 continuation。修正后的完整夹具整例 **NOT_RERUN**，四产品文件执行后未改。
- **同原数据库/同三个 Run 的剩余页面续验 1PASS/107.78秒**，外层109.673827秒。9项检查、49页面请求（47GET＋1PUT＋1POST）、27资产、1次冷启动。冷读已采用 v2 的30/PENDING、原声明 STALE/历史 ACCEPTED；同 Goal 同列按钮拒绝，真实 API409无操作前后55表全等；页面明确保存 Goal v3，已采用 parent 的同列 preview 接受，GOAL 为唯一显式 changes，APP重验、稳定 ID及固定 amount 保留。续验0Worker/模型，包含真实 Goal PUT及preview POST，不是全表只读：仅 `goal_cards`、`goal_card_versions`、`delivery_graph_requests` 改变，其余52表全等，两个追加表原行保留。noop hook另有context GET和409 POST，分开计量。

有限独审仅针对上述源码及原件，未新跑锁场景、完整旧矩阵、第二 CHECK/采用、原生平台或真实语义。新 Goal v3 只是 preview，不称已发布/已采用。现有人工锁、PROJECT未知依赖拒绝及其它修改形态的兼容性为源码范围结论。

原件根目录 `/workspace/goal-only-revision-20261018`；首次与续验的命令/时长、完整 HTTP、Worker/claim、55表 JSON 和执行源副本分开保存，详见[原件索引](../evidence/goal-only-revision-20261018/README.md)。修正测试不改变旧失败，前片视图/导出等证据不被重签。
