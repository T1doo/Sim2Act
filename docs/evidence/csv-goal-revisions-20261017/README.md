# CSV Goal 修订：有界交付证据

接续远端基线 `dfab3bcd7bdac0037ae2dfa76e9d0a1394abbdc1`，普通开发分支 `dev/csv-goal-revision-20261017`。产品实现为 `b1b1b2159b850ac0a058e2a6cc1e86b275579f79`；测试加强为 `8bbbd1f3b6d2d9ee6671aca4729883385087da1f`，仅修改 `tests/csv_goal_revision.cjs`。126 个生产文件在两次验收间逐字不变。后续提交仅封存证据。

交付链是已有 GoalCard CSV 应用/实例 → 同卡 v2 → 明确旧列到新列 → 同 app/runtime 修订草案 → 原 NoModel Worker 实际隔离 CHECK → 单独确认新内部 Release → 原控制器明确 CAS 采用原实例 → 新 Run。合成材料的旧 `amount` 合计 30，新 `quantity` 合计 5；保留原 draft、generation 来源、稳定 ID、运行身份和旧结果，没有新增 executor、principal 或 Grant。完整 Goal v2 冻结于接受绑定，GoalSpec 冻结卡身份/目标/约束/未决项。新 Run 的人工声明 PENDING，不继承旧 Run 的合成 ACCEPTED；语义 UNKNOWN，未发布。

| 执行方与固定源码 | 实际结果 | JUnit 秒 | wall 秒 |
| --- | --- | ---: | ---: |
| 作者 `b1b1b215` 原批 | 16 PASS / 0 FAIL / 0 SKIP | 427.743 | 431.787 |
| 独立 `b1b1b215` 原批 | 16 PASS / 0 FAIL / 0 SKIP | 413.679 | 418.091 |
| 作者 `8bbbd1f3` 定向 deliver | 1 PASS | 86.550 | 94.479 |
| 独立 `8bbbd1f3` 定向 deliver | 1 PASS | 85.154 | 88.821 |

有效选择为 **16 个唯一节点，每方 17 次实际执行**：原批 15 项加加强后的 deliver 1 项。没有在 8bbb 或最终文档 HEAD 全量重跑 16 项。原批已经通过的目录过滤断言使用了 CHECK 创建前的列表，不能证明真实刷新后的过滤；原件及该缺口保留。加强验收通过可见项目选择触发新 `/instances` 回复，记录服务端真实 CHECK 角色行及页面实例 ID，证明两个业务实例可见、CHECK 不可见，再显式重开原实例继续同一批准/采用链。没有改产品代码或降低原验收。

新 12 项为 8 个 API 节点和 4 个整页场景（正常交付、实际 202 丢失、账号/项目/实例/工作区迟到隔离、已证明未受理后的明确重新准备）。覆盖同卡完整冻结、原来源不变、幂等接受、独立 CHECK 角色、防降级、错误旧列 FAILED 且无 Operation、原实例数据/权限/Goal/人工锁漂移拒绝、Goal v3 后历史可读而新执行拒绝，以及新结果人工 PENDING。另有 4 项已有回归：持久 AppRun 冷 Store/原 Worker、实例数据 CAS、旧人工声明不继承、原 CSV 使用入口的实际 HTTP 整页。

作者原 4 页为 66 条检查、300 条已回复 API 请求、104 条资产哈希；加强 deliver 为 19 条检查、92 条已回复请求、26 条资产。作者原 300 回复中有 1 条预期 409，其余 2xx；加强 92 条均 2xx。独立原批另有 11 条旁路 `/protocol/contracts` 的 `Evaluation asset unavailable` 400，加强批有 4 条；独立固定副本未附全部可重建的 evaluation 资产，400 原始回复完整保留，未声称全部 HTTP 成功，也未扩大本片处理该旁路。该问题不阻断已实跑的 CSV 修订链。

作者每批 600 个输入前后 SHA 一致；独立每批 606 个输入（126 src、471 tests、7 schema、pyproject、1 旧 gold）与 Git、独立副本及共享 checkout 前后均一致。作者输入清单另含两个 Node package 文件，范围与独立清单分别列明。页面资源均取自实际 ASGI 静态路由；Node/JSDOM 驱动实际 API 与 SQLite，Worker 明确注入 NoModel。SQL 正向对照和拒绝前正文读取断言在 API 测试中执行，没有另存逐 SQL trace sidecar。

可检查的原件：

- [作者分源选择、页面回复和新目录证明](raw/author-meta/author-admission.json)
- [作者原批报告](raw/author-meta/author-b1b1b215/report.json)、[加强报告](raw/author-meta/author-refined-deliver/report.json)
- [独立最终审查](raw/independent/csv-goal-revision-independent-8bbbd1f3-20261017/review.json)、[独立动态目录证明](raw/independent/csv-goal-revision-independent-8bbbd1f3-20261017/directory-proof.json)
- [独立原批审查及保留的原 oracle 缺口](raw/independent/csv-goal-revision-independent-b1b1b215-20261017/review.json)
- [全部原件路径、编码与解压后哈希](originals-manifest.json)、[包内 SHA256SUMS](SHA256SUMS)

包保留 **194 份原件**，其中 **38 份 SQLite 文件副本**，并非 38 个唯一病例；含双方各批完整正式 fixtures/HTTP/页面/交付原件、独立清单及校验文件、开发日志与仍存在的开发临时产物。开发期默认 pytest 临时目录并非完整历史 DB 留存；正式批均使用独立保留目录。SQLite 使用 gzip，原始字节哈希和存储哈希分别记录，逐份解压核对；未复制可重建源码副本、依赖目录或缓存。独立原目录已封存停止写入，原批与加强批分开保留。

没有执行真实模型、真实语义/场景验收、原生浏览器、Windows、PG、远端 CI、部署或真实用户数据库迁移。跨平台限额变化的历史兼容、连续多轮修订、材料替换和 LIVE 不在本片。此前旧环境满盘导致未落盘的独审报告仍是证据缺口，本包没有补回或代替它；也不据本片宣布整个 F2/R0 通过。推送后的实际远端 SHA、原分支/main 状态及未提交/未推送差异由最终交付核对单另行记录。
