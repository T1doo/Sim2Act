# 离线 CSV 列绑定草案候选证据

冻结基线 `122b2e6f25402e5d693da05c945727b7cbf4ceeb`；最终源码 `2e66fb0b7ba58a978d777ad19ac5d68033d5f73a`，独立分支 `dev/offline-column-patch-20261008`。交付为待独立审查候选，不合回 dev、不发布、不宣布最终验收。第二审查人由父线程后续安排；`review.json` 明确独立 reviewer **NOT_PERFORMED**，不能把同作者只读复核或独立答案冒认独审。

[方案与合同解释](../../F2/ColumnBindingPatchPlan.md) · [用户复现指南](../../F2/ColumnBindingPatchQuickstart.md)

同一应用/求和节点的新 schema 列绑定定义 → 不可变草案图/补丁 → 人工核对精确 patch_fingerprint 的显式工程确认 → 实际受影响只读检查 → 当前授权下持久回读。原 canonical candidate、输入 schema、数据/来源绑定、ActionSpec、布局、旧预览/内部版本/实例不覆盖。新定义与检查复用原 DeliveryGraph 账本/项目锁/来源与人工锁及 authorized_read/data.aggregate_csv，不新增表/Grant/身份/任意执行器。

合成 CSV SHA-256 `d5851306dd3ce833d82bced0abef12728f3e64e1ef1266ee8a9fef209a59619f`；独立 csv.DictReader + Decimal 核对两行，amount=30、quantity=15。手工冻结应更新集 ACTION/ARTIFACT/VIEW/CHECK/MANIFEST（9 个），应保持集 GOAL/SOURCE/REQUIREMENT（4 个）。`*-independent-answer.json` 保留完整新图、保持对象、真实输出/来源/版本：漏更新 0/9，无必要修改 0/4；旧 amount 预览冷读不变。各用例还独立比较全部数据库表完整行（仅 delivery_graph_requests 允许追加），没有声称导出了全部业务表原始行。

最终源码实际 359 个唯一用例，17 个文件：

| 实际环境 | PASS | SKIP | FAIL/ERROR | pytest 时间 |
| --- | ---: | ---: | ---: | ---: |
| Linux Python 3.12.14 / SQLite 工程夹具 | 355 | 4 个 PG 专用角色测试 | 0/0 | 206.89s |
| Linux Python 3.12.14 / PostgreSQL 17.9 | 359 | 0 | 0/0 | 389.42s |

`test-summary.json` 从两份实际 JUnit 派生逐用例分母/skip 名称，不累加两个环境当作 718 个不同用例。`*-provenance.json` 记录源码 SHA、17 文件清单、变更源/测试文件的前后哈希；两边 source_unchanged=true。Ruff 全 src/scripts/tests 和 mypy 48 个源码文件通过。保留 Starlette testclient 弃用警告及 PG 原 preview-extraction Pydantic alias 警告，未换依赖掩盖它们。旧全量 1591（1564 PASS/27 SKIP）不用于证明本改动。

范围包含：新定义/API/精确版本/冷 Store 重放、原键异参/严格 schema/非法 bool/未知字段、用户与应用撤权、来源变更及协调重 hash、人工锁冲突、锁循环后旧版本失效、新草案仍可读、PROJECT 未知依赖 fail closed、并发原键、协调重签检查后实际重建拒绝伪 PASS、容量超限在接受前拒绝而原键仍可恢复。原交付图核心、回执/来源类型、独立服务合同、原 CSV 预览/提取/注册提取、内部生命周期/业务使用、Report Manifest/页面、严格契约语义一并定向重验。

实际 loopback HTTP/product JS：新页面 **20 项**，原 CSV/Report 各 **29 项**；每个环境都执行。`*-column-ui.json` 与 `*-legacy-graph-0/1.json` 保留实际请求、加载源码哈希和 oracle。丢失接受回执保留原键/精确参数、先回读后接受结果；确认复选框在回读后清掉；版本错、协调重签来源、篡改保持对象、项目 ABA、身份与撤权会清当前图/草案/结果证据。JSDOM 30.1.2、Node 24.19.0；普通产品没有 Node 依赖。导航测试禁用周期刷新，不冒认后台轮询/原生浏览器/像素验证。

失败保留：初始新 API 22 PASS/2 FAIL 是两处测试预期错（原 LOCK_CONFLICT 的 HTTP 400；异参被拒不应使原请求重放失效）；首轮三个 DOM 用例在 JSDOM close 后仍有异步请求/事件，原始 driver 日志保留，复用既有生命周期 drain 修复且原 29 个断言/等待上限/90 秒 subprocess 限制不降低。第一次 PG 59 PASS/3 FAIL：一处新测试快照排序错，另两原 DOM 用例与改源重叠，不能算冻结验证，原日志保留。`test-inventory.json` 也记录无效 collection 路径纠正。`pre-capacity-03cdd44/` 是较早源码的 353 PASS/4 SKIP、PG357 PASS；仅作为历史，不借它证明最终容量/来源绑定修正。

保持 DRAFT_PATCH/NOT_RUN → CHECKED_CANDIDATE/有限检查 PASS，semantic UNKNOWN、owner PENDING、正式发布关闭。真实模型请求 0、业务写入 0，不是任务 gold、人工签收、通用局部修改或完整 P-B。这个绑定覆盖层不生成 canonical Release，也不切换原实例。工程容量每应用 50 定义/50 检查，原记录不删除；超限明确拒绝。PROJECT/SEMANTIC/MODEL_CANDIDATE 的未知依赖不在固定检查器内伪造完成。

Windows900/Edge240/Node150 标准、workflow、锁依赖和原 Python UI 断言文件与基线逐字节相同，见 `review.json`；Windows/受保护 Edge 本轮 NOT_RUN，不触发 CI/dispatch/rerun。既有源码边界与未验收事项不提升。

隔离 PostgreSQL 容器为官方 17.9 镜像，`--network none`，不绑定 TCP 端口，使用自有私有 /tmp Unix socket，无真实账号/模型凭据设置。各 PG 测试独立 test_* schema/临时测试角色；结束实际查询剩余 schema=0、role=0（`pg-before-stop.json`）。`cleanup.json` 记录容器/自有镜像引用、14 个自有临时路径及测试 SQLite/PG/Node/npm资源清理，均无残留。首次正常 image rm 与容器自动删除存在先后窗口而拒绝，确认容器已删除后再次正常 rm 成功，没有 force。锁定依赖的开发 .venv 保留供持续开发。

最终普通 push 前重取远端基线及核祖先；候选远端 HEAD、工作树和文件清单由交付回执记录，不强推、不接回 dev/main。源码与最终证据 commit 分开；父线程可从上述源码 SHA 审查实现，证据 commit 不改 src/tests。
