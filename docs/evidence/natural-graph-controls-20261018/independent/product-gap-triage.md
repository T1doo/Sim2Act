# 下一产品价值：自然应用交付图与人工锁入口

基线：`4a5fa568d2aefcbe59ef2f14c5a58414073bbe0b`。root 保持唯一仓库写入者。本轮只读源码/原 V5/既有测试；没有产品、HTTP、Worker、模型、SQL、数据库、pytest/collect 或网络操作；没有写旧 sealed 目录。

**优先完成这一个真实主路径断点，不再安排已通过完整页面的同义重测。**

1. 自然 P-A/P-B 新应用无法从实际页面派生修改所需的交付图。`src/sim2act/web/app.js:629` 的 MODEL_SPEC_CHECKLIST 分支在 `:636` await openInternal 后直接 return；唯一 `openDeliveryGraph` 调用在 `:639`，全 web 未找到其它自然家族 derive 入口。`internal.js:1372` 的 naturalLogicReadGraph 只 GET 现有 graph；局部逻辑面板却要求用户先从交付图明确派生。没有预派生 graph 的 fresh 应用会在 `delivery_graph_apps.py:214` state 以缺 anchor 的 VERSION_CONFLICT 停止，用户无法开始修改。前轮完整 PB 页面在 `tests/test_pb_first_logic_current_page_ui.py:355` 用 Python fixture POST 预派生，证明的是已有图上的逻辑链，不能证明新页面入口存在。这是功能断点，非单纯资格缺失。
2. 同一个入口内，自然家族人工锁功能也被前端隐藏。`manual-locks.js:5` 仅 CSV aggregate / bounded Report 显示；后端 `manual_locks.py:38` context 已在先授权的 load_family 后明确接受 `pa-natural-spec-app.v1`（P-A/P-B 共用 namespace）。真实用户无法设置或解除自然图人工锁，尽管 `tests/test_natural_logic_patches.py:129` 已有 API 设置锁、重派生、预览 LOCK_CONFLICT 的能力。两项应合为同一小交付，不新造执行器/API/权限。

对应原规格：`docs/sources/V5/平台产品设计.md:58` 三工作区真实操作；`:429` §9.3 保留稳定对象、影响分析、锁冲突与发布前检查；`docs/sources/V5/分阶段开发计划.md:99` F2-T07，`:343` AT13。只接通真实入口不等于整个 R0、完整 AT13/14/15 或真实模型验收。

## 可复用的当前能力

- `delivery_graph_apps.py:88` load_family 先锁所属项目、校 app/project，再经 `apps.py:404` validate_frozen_candidate / `pa_spec_apps.verify_origin` 核来源，逐项核当前声明的工具/资源权限交集（`:108`）。自然家族限定的 authorization fingerprint 在 `:136`；没有读取未授权私有正文的放宽建议。
- `delivery_graph_apps.py:390` build/`:455` natural_candidate 适配，已有 stable IDs/source versions、dependency_edges=[]、当前锁与 APP 范围 UNKNOWN；`:571` derive 先完整校候选/当前版本再写 metadata。P-A 与 P-B 自然候选都经过该 namespace 和原来源证明路径。此为静态能力确认，非本轮实际请求资格。
- `delivery-graph.js:10` openDeliveryGraph / `:28` submitDeliveryGraph；通用 deliveryGraphSeal 已与 `internal.js:1372` naturalLogicReadGraph 共用，前轮完整 PA/PB 资格中的该 seal 已使用自然 graph。未发现需要修改后端家族边界来接通的证据。
- `manual_locks.py:101` submit/原 strict DTO、CAS、双账回执；`natural_logic_patches.py:186` calculate→core.plan_change，`delivery_graph.py:536` LOCK_CONFLICT 保留原对象。可直接复用 manualRead/manualSubmit，不能弱化 current auth/版本/锁门。
- `csv-dag.js:25`、`project-columns.js:6`、`delivery-graph.js:33` 的 CSV 控件各自有独立 family guard；自然入口接通后应继续隐藏 CSV 专用功能。

## 最小实现与定向验收建议

生产优先只接通现有页面：在自然 MODEL_SPEC_CHECKLIST 分支 await openInternal 后，重新核 current identity/project/app-selection/selectionCurrent，再显式 openDeliveryGraph；只对严格自然 namespace 开放 manualOpen。打开应用只显示入口，不自动 derive、设置锁、运行模型或创建新授权。

新定向从没有 delivery graph 的 fresh 自然应用开始，实际页面选应用/实例 → 显式 derive → 读当前 graph/lock state → 锁一个 READ 节点 → 显式重派生 → 局部逻辑 preview 实际 LOCK_CONFLICT，完整业务/模型/旧历史不变 → 读锁/解除 → 再重派生 → preview 成功。此处结束；无需重跑刚通过的 CHECK/版本提交/THIRD/cold 20分钟长链。至少实际覆盖 PA/PB 两种来源的入口路由，或清楚区分其中一个 actual 页面与另一个只静态/合成资格。原请求、回执、实际资产与零业务变更证据足够，不另造恢复/下载矩阵。

导航要点：`clearApp app.js:568` 已清 delivery/engineering 并增加 app generation；新调用不能在 openInternal await 后依据过期 a 打开旧图。`deliveryCurrent delivery-graph.js:6` 与 engineeringCurrent 均依赖 selectionCurrent；自然 first-guide 从 projects→apps，以及 openSavedInternalUse 的开页临时 fence 在 finally 解除时，delivery 与 engineering 的 fence 生命周期必须一致，不能给 delivery 留下永久 false 的临时函数。每次新的异步读取/crypto 应在 paint 前复核当前选择，保持身份/项目切换隔离；无需顺带改造旧全局控制器或扩大故障矩阵。锁/解锁后依既有 needs_derive 提示重新派生，不把旧 anchor 当当前证明。

## 未选路径与限制

自然生成/语义/Windows 的剩余实用性门需要实际授权条件，当前不能以更多 Mock 页面替代。资源 24h 授权到期后缺少续期入口是另一可见限制（api.py 当前只有资源创建/授权列表/revoke），但修复会涉及重新授权/Grant 政策，不能在本轮“不新增权限”范围顺手实现。现有本地记录、自然逐次 Goal、新输入、历史结果、v1/v2 下载与局部逻辑执行已存在，不能重造后计为新增产品。

结论仅是有界静态 triage 与修复建议；未预写实现或测试 PASS。本新目录保持未封存，供随后非作者 WIP/冻结审查使用。
