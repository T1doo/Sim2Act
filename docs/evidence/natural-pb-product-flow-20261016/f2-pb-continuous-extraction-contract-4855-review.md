# 成功成果到 P-B 应用连续流程：只读合同核查

基线 HEAD：`4855d5250fd576bb04f81faad22ca6a4ccdfcbdd`，2026-10-16；开始核查时工作区干净，可用磁盘约 27GiB。本审查者不修改仓库，不运行模型、Worker 或旧恢复矩阵。当前未见适用的本地 AGENTS.md/SKILL.md。

## 已有能力及实际产品缺口

`web/internal.js:specResult`（约 510 行）对成功成果展示“从此成功任务提取应用（P-B）”。仅原始自然 PA 候选（namespace `pa-natural-spec-app.v1`、origin goal、无 spec_task）可显示入口；实际 rid 从该成果 record.run_id/result_version 在所选实例 runs 中精确找到，不能取最新 Run 或只读页面摘要冒充来源。

`openNaturalTaskExtraction`（约 574 行）已有完整来源核查、可编辑的有限 recipe、目标 Goal 选择、独立审阅/ack/保存/原 key 恢复/打开应用。已有步骤图编辑不是缺口，不应另造重复编辑器或提取 API。

实际缺口：当前目标下拉仅列已有的其他 Goal，用户需要离开另行准备新 TXT/MD 和 Goal；保存后仅能打开已保存 app，后续 Release、实例与目录使用缺少连续步骤提示。原内部控制器和统一目录已能承接保存后的自然 PB 应用。

## 原后端合同不得削弱

- `pb_natural_specs.py:source_gate`：先 own_project 与 scoped scalar Run principal/project/runtime 分类；仅原始自然 PA 且非抽取链；成功状态、独立 committed artifact 指针、保存操作/event/output/typed 一致；重新 authorize 来源成果 READ 后才进入受保护的完整来源内容。来源授权不是新 PB runtime 的自动授权。
- `_source`/`source`：完整 verify_job、recipe、Release/Run/AppRun/binding/typed/output/receipt/audit fingerprints；source proof 是精确成功版本，不是渲染过的历史结果文本。现有同事务 proof 复用仍重验 authorities，不扩大缓存范围。
- `review`：原 proof/recipe 指纹相同；目标是不同的自有当前 Goal、不同 resource_id 与不同 hash，恰好一个受权 TXT/MD；名称非空至多 100；新候选来自有限 recipe 与新绑定，不复制旧答案；预算来自原候选限额。审阅只读，edited_recipe_execution NOT_RUN，sample_scope SUCCESSFUL_SOURCE_ONLY，runtime 仍 MODEL_EXECUTION_REQUIRED，语义 UNKNOWN/owner PENDING。
- `_extract`：project 事务锁中重新 review 与精确 review_fingerprint；原 request_key 和整个 body 一致才幂等回读；按原有限容量与现有协议创建 runtime/精确 READ+项目 SAVE、app、origin marker 和双封存；末尾 load_draft/verify 重验来源/目标/授权/版本，失败原子回滚。无需新 executor、Grant 类型或权限模式。
- `GET .../extractions/by-key/{key}`：先 source_gate，再按 owner/source/key 定位；没有原回执为 OUTCOME_UNKNOWN，不许可重发；读取已保存 app 时再 load_draft/review/verify。来源或目标撤权/改变不能由只读 metadata 或 UI 选择绕过。

## 原前端保存与未知回执合同

`naturalTaskRequests` 是页面内 Map，scope 为 token/project/source Run。它不是跨冷页 durable browser storage，交付不能宣称冷重载后自动恢复该提取意图。

`action(true)` 在首个 await 前设置 s.busy，并保存整个不可变意图的 body/review。pending 或忙时禁止再确认；发一次 extractions POST 后必须原 key GET。POST 丢失、回执污染、导航导致尚未核实，均保留 pending，仅 `action(false)` 原 key GET；不创建另一个 key、不重发。

`recover` 不凭 POST 201 立即成功：核完整 scope/key/request/request_fingerprint/review/候选/原 app/runtime，再 GET app 比较项目、name、candidate、fingerprint 和 PB marker，最后才设置 s.saved 并删除原 pending。迟到导航回调不继续 GET、不清 pending、不绘制旧保存成功。

`naturalTaskCurrent` 核精确 panel、engineering view、实例对象、实例选择代际、连接和 workspace。编辑单调 edit 代际使“改后撤销”也不能采纳旧 review。新流程仍须让新材料准备按钮受 s.busy/pending 约束，不能在 unknown 中另起目标、调用自然 PA 生成或自动 Run。

## 建议最小接入

1. 在原提取 panel 内增加“准备新材料与 Goal”及连续步骤卡，不复制原 preview/ack/commit/by-key 控件。复用 `app.js:beginNaturalInputPreparation` 的原材料/Goal forms，增加独立 extraction-origin 分支和 current/return 回调；不能复用 per-use 的 returnNaturalPreparation 后误启动 source 实例运行，也不能伪装 firstCreation 并进入 PA generation。
2. 启动准备时先冻结精确来源 state、view、instance、source rid、source proof/recipe 指纹、edit 与页面代际；隐藏原内部 panel 时保持 s.panel 连接。取消/导航先还原原 forms，再废弃本次准备，保留后台已存资源/Goal与自然提取 pending。原 TXT/MD 2048字节/40行/Unicode C 边界、保存 explicit click、Goal 唯一 resource、未知保存锁全部复用。
3. 返回仅在原 source state/current/edit 仍有效时读取目标 Goal 的精确 version/fingerprint/唯一新材料，必要时重读原 extraction-options 核相同 source proof/recipe；恢复原表单并选择该 Goal，清旧 review/ack，随后仍须原审阅与原确认 click。任何源授权/版本失败停止；不将已有图或旧结果当新材料执行成功。
4. 保存成功后使用精确 s.saved app id/candidate 指纹，经原 showApp 读取到同 app 的 engineering view。为连续步骤卡仅保留精确受控跳转，不把已移除旧 s.panel 当后续 current；将 guide 绑定新 engineering view，捕获身份、连接、项目、workspace/app/instance 代际。临时 showApp selectionCurrent 只在整个读取完成且 shown/current/app/project 都相符后释放；沿用已验自然 PA 的交接时机。
5. 仅观察原 internal commit 成功的 Release id/fingerprint 与原 create instance 回执中 release_id/release_fingerprint 的精确一致性，推进步骤卡。不得从列表第一个/最新 Release 或任意 instance 推断完成。保存 app、Release、instance 分别点击，不自动执行。
6. 明确返回目录只 refreshApps 并重新进入 owned metadata 的自然 PB 行；不预取私有完整历史、不将目录当权限证明。用户打开选择已存实例，再通过现有 per-use 准备另一份材料/Goal、预览和确认 Run。每次都保留原 app/recipe/Release/source lineage 的权限/版本检查。

现有结果 extract onclick 比同段 review onclick 少了入口处 node.isConnected/engineeringCurrent/精确 instance/selection 守卫。普通原生 UI 隐藏/断开后不可点击，已有异步结果会被 naturalTaskCurrent 丢弃；建议本轮整合入口时与 review 保持同样的同步守卫，避免被程序化旧 handler 启动不必要的旧 scope GET。这是小范围入口加固，不建议扩为新故障矩阵。

## 建议最小验收及边界

- 一条实际 HTTP + SQLite + mock Worker 可见链：已成功原 PA 成果 → 提取入口 → 新材料/Goal → 原 review+ack+save → 精确 app/Release/instance → 目录 → 新材料/Goal → 原 per-use Run 与结果/同 Run owner 入口。保存时绑定的材料可尚未执行，随后目录材料产生该 PB 实例首次 v1；若如此必须精确标明，不宣称 PB v2/旧 PB 结果保留。
- 保存前后比较原来源 Run/AppRun/typed result/app/Release 对应字节，确认没有更改来源成功成果或旧历史。新 runtime wire 仅含本次新材料，不用旧答案。
- 受影响控制器轻 probe 覆盖 source/target/receipt 迟到、身份/项目/workspace/实例 ABA、重复 click、已接受保存回执丢失原 key GET且仅一 POST、未知时禁止新意图、共享表单还原；来源/目标当前撤权用实际 HTTP 拒绝证明。已有 `test_pb_natural_specs.py`、`test_pb_natural_spec_ui.py`、目录/内联准备测试可作为对应已存合同参考，旧完整 UI driver 的默认 internal-run-submit 路径并不证明新增目录/逐次新材料入口。
- 后端若不变，不以新增指南冒称修复旧心跳/租约失败；不跑真实模型/Windows/PG/CI 或旧恢复矩阵。根线程最终需记录实际执行节点及精确冻结字节，静审不是动态通过。

本阶段只完成合同/缺口核查和接入建议，尚无本轮实现可签收；等待根线程有限 diff 后独审。
