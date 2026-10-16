# 应用内准备本次材料与 Goal：只读合同核查

基线 HEAD：`5d6afe2fd23f6fbc059d5243323a071030e5f36d`。开查工作区干净；仓库/父目录未发现额外 AGENTS.md 或 SKILL.md。本报告无仓库改动，无模型、Worker、恢复矩阵或新测试运行；旧多历史心跳锁失败没有解决或补回的结论。

## 精确材料合同

P-A/P-B 原 per-use 两族共同经 `pb_natural_uses.review -> pa_spec_apps.target -> pa_material_bindings.target` 及 `natural_specs.bounded_source`。

- 最终保存内容为 TXT/MD、非空白、有效 UTF-8，UTF-8 编码不超过 2048 字节，Python `splitlines()` 不超过 40 行。
- 内容 SHA256 必须等于授权资源实际 hash，禁止改写旧文本或凭名称/显示摘要建立绑定。
- 禁止所有 Unicode General Category C（控制、格式、代理、私用、未指派），只有 LF/CR/TAB 例外。BOM U+FEFF、零宽连接符、方向控制符等也会被拒绝。不要静默去 BOM 或清字符改变材料。
- 现有通用资源入口允许 32768 字节，TXT/MD 导入保留 BOM；这不是自然材料合同。应用内准备应检查最终 textarea 保存文本，保留通用 CSV/JSON 路径原限制。TXT/MD 现有 textarea 会规范化换行，回显/计数/保存/hash 应以最终文本为准。
- Python splitlines 支持 Unicode U+2028/U+2029；尾换行不制造额外末空行。若 JS 做提示，不要简单 `split("\n").length` 冒充精确后端判定。服务端仍最终核验。

`Store.resource` / `POST /api/projects/{pid}/resources` 原合同会为当前 user 和项目 runtime 保存原项目资源并授原 resource.read/data.aggregate_csv 域权限；不是授予自然应用实例读取权。应用材料 read Grant 仍由原 per-use approve 在用户确认准确材料/Goal/预算后按原策略处理；准备入口不应直接新增实例 Grant、Principal 或 Release。

## 精确 Goal 合同

`goals.GoalCardInput`：title 1–200、goal 1–4000；known/assumptions/unresolved/constraints/acceptance_checks 各最多 16 项，每项 1–1000；通用 resource_refs 最多 8 且不能重复。自然 per-use target 要求当前 Goal 的 resource_refs **恰好只含本次一个材料 ID**，snapshot 的 resource_id/hash/format 与当前授权资源一致，当前 version/fingerprint 精确匹配。

自然两族没有 `text_workflows.compile_candidate` 那条额外的 6000 字节总 Goal、constraints/acceptance_checks 非空、unresolved<=15 限制，不应借相邻家族误限。可以引导完整填写目标、硬条件和验收，但应区分 UI 建议与既有后端必须项。

Goal 保存是不可变草案版本，不执行应用、不确认语义、不发布。原 POST 返回 id/version/fingerprint；PUT 需原 expected_version。列表只有 metadata；打开当前 Goal 会重读所有保留历史的授权资源。因此仅在用户选定/保存后读取具体 Goal，不为挑选自动展开全部卡片。

## 共享表单/controller 的集成风险

- `app.js:saveResourceMaterial` 已有 `resourceSaveRequests` 按 identity/project 锁定保存未知意图，无回执不重 POST，仅 GET 列表核对。复用这层控制，不能再加一个旁路 POST。accepted 后导航失效应保留原 receipt，不迟到填新实例。
- 通用 `resourceContext` 没有 app/instance/workspace；应用内自动采用新材料必须另有 preparation fence，不能把这个通用 current 当作实例上下文保护。
- 原 `goal-card-form.onsubmit` 成功后 `showGoalCard -> clearGoalCard -> clearApp` 会拆掉应用实例和 per-use panel。应用内不能直接重用其跳转收尾。宜抽共享保存/精确读取 helper，项目页继续原跳转，应用内仅刷新当前 panel 并显式选择已核 Goal。
- 原 Goal 创建 POST 无 request_key，旧 handler 也没有 unknown 锁。新增应用内创建流程必须 saving/unknown 防双击、丢回执不自动重建；GET 列表供人工核对，不能仅凭 title/相同内容认定原 POST 回执。
- 不克隆带相同 DOM id 的共享表单。可共享字段构建/validation/save helper；若移动原 node，必须在清理时恢复位置，并避免旧 activeGoalCard 把新目标保存成对旧卡 PUT。
- background refresh 不应清草稿、重设本次材料/Goal、自动运行或自动保存；新材料/Goal 的修改应清旧 review、ack 和 proof。

## 最小安全接入

1. 在已授权打开的自然实例 per-use 区加明确“准备本次材料/Goal”入口；不改变目录 metadata-only 发现。
2. 复用现有本地文本读取与保存 helper，限本次 TXT/MD 范围，先惰性预览最终内容，显式“保存到当前项目”；保存材料与保存 Goal 各是独立确认，均不调用模型/提交 Run。
3. 精确新材料 receipt 可用后，让用户编写自己的完整 Goal，resource_refs 固定为该材料 ID。保存后 fresh GET 核对 Goal id/project/version/fingerprint/snapshot；在同一仍 current 的实例内更新选项。
4. 自动采用已确认保存 receipt 属 UI 选择便利；仍必须清空 per-use ack，用户重新点击原精确绑定预览、阅读并确认，最后走原 pa-use/pb-use-runs。无自动 preview/Run/应用 grant。
5. preparation fence 在首次 await/FileReader 前固定 token、identityConnectionGeneration、project、app、instance object+instanceGeneration、Release、workspaceSelectionGeneration、panel/edit generation；每次 await/read/hash 后核 current。身份/项目/实例/应用/工作区 ABA 均拒绝迟到回调接管。已接受保存可留痕，但不能填入新身份或新实例。
6. submit/unknown 状态与原 pbUsePending/engineeringPending 冲突时按原合同禁止新的运行意图；不要清空原 Run request_key 或 durable localStorage/Web Lock 记录以允许准备/提交。

## 有界验证建议

新验证以受影响的准备链为主：各一条 PA/PB 真实 HTTP/JSDOM 从应用内保存 TXT/MD、保存唯一材料 Goal、回到原 per-use 精确预览；明确保存动作数量和零自动 Run/模型请求。静态检查及合成 UI 覆盖 2048字节/40行/BOM/类别C、保存双击/未知回执不重POST、身份/项目/实例/工作区迟到隔离、旧review/ack清除。复用既有 importer/Goal 正常路径回归，不重 Worker 重启/取消矩阵；若后端/Worker未变，既有运行证据按精确字节边界引用，不冒充本轮新执行。
