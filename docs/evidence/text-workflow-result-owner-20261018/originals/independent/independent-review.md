# 四步文本结果/人工验收独立有限 WIP 审查

审查人：非产品作者 `/root/next_visible_gap_readonly`。仓库起点为 275455c68099a879099e7a9a513ebf8d4a323c7b；父级为唯一源码写入者。此报告及合成 SQLite 数据只写于仓库外。本报告针对尚未冻结 WIP，不能代替最终精确 SHA 资格。

## 发现与修正状态

1. **P1：新增四步账本可由旧自然规范端点原 key / 停止分支访问并写入。** 原 owner_acceptance.py `natural_submit` 用通用 natural_scope；scoped_run_submit 在 context 前返回 old key 或执行 CANCEL/REVOKE。原 natural_read 同样在家族检查前读共享自然账本元数据。新 text_workflow_owner.scope 的严格家族门无法保护旧入口。原文件 SHA256 `3b1ac086b6ac05f1d73e69589ef71915c138b93bd835b33a40506794325fa564` 保存在 owner_acceptance_before_fix.py。

   `reproduce_original_p1.py` 在真实隔离 SQLite、真实 owner.natural_append/natural_submit/scoped_run_submit 上重现：old key 返回四步记录；旧自然 submit 追加 CANCELLED；natural_context 调用 0。结果见 original-p1-result.json。此夹具只验证存储和控制流，没有真实 Worker、完整执行证据或业务 typed result（0 行），不称产品验收。第一次脚本在 Limits() 缺少六个必填字段处初始化失败；随后补入固定 Limits 并使用新命名数据库重跑合格，未改产品源码。

2. **P2：第一版修正只信 Release 的 namespace 标量，可被单字段污染重新放行 old key。** 第一版补丁 owner_acceptance SHA256 `81c193d53067224107265c188b3a2a1e1dd3803d62fe274447a91f93da4ae744` 已保存原字节。`reproduce_namespace_only_p2.py` 仅将已知合成 Release namespace 改为自然规范，再调用相同 old key，返回四步记录、natural_context 0 次；finally 恢复原字段。原结果见 namespace-only-p2-result.json。此项是受控数据污染下的早期家族门验证，不冒充合法客户端可修改 Release。

   父级当前修正新增专用 natural_review_scope，保留 generic natural_scope，旧 natural_read/natural_submit 在 ledger/old-key/stop 前使用该门；同时核对既有 pa_spec_apps.RUN_META 双 seal 的严格 RunScopeInput 标识。正常四步家族三项（old key、stop、read metadata）均 UNSUPPORTED_CAPABILITY，15 条 SQL 无 natural_owner 表查询，owner 行不变、natural_context 0 次。单 namespace 污染另以 VERSION_CONFLICT 拒绝，同样未查询 owner 表、行不变、0 context，合成 Release 已恢复。

   当前短回归绑定 owner_acceptance SHA256 `7efd87cf634601a80c5132aecbdcbdf8b464000a1f4f036269c9b81fb8b74f69`；原始 JSON/SQL：fixed-scope-result-7efd87cf6346.json 与 fixed-namespace-result-7efd87cf6346.json。P1/P2 在该 WIP 的有限控制流修正已复查收敛，原发现和失败不能写成从未发生，尚需冻结版本确认与正常自然规范路径实际回归。

## 其它后端核查

- text_workflow_owner.scope 在 old-key 与 metadata stop 前验证拥有的 iid/rid、Run/AppRun/Release 所属关系、四步 namespace、独立四步 RUN_META 双 seal、精确标识和 internal:+AppRun.id。没有依赖材料授权，因此撤权后的本人停止入口可以保留。
- context 在 Run/Goal/result/owner payload 前调用 flow.job_scope_gate。随后用原 flow.verify_job(require_success=True) 校验独立 ACCEPTED、当前授权、精确 Goal、四步 Operation/intent/receipt、typed result 和零模型账本。
- PARTIAL / emit_report=false 不能通过 require_success。当前 iid revision、release、data_version 必须匹配选中成功 Run；任何非终态 AppRun 拒绝签收。新 Run 另有 run_id，读取其空账本为 PENDING，不复制旧接受。
- read 先执行完整当前 context，再读取 owner payload；Goal/head、权限、版本或当前结果失效时只返回 metadata，content_access=false；无新 context 或 record 泄漏。final_gate 在同一锁定事务追加后重复完整 context，并检查批准期限；异常事务回滚。
- 复用 shared natural 表没有新增 schema/executor/Principal/Grant。api.py 仅注册适配器两行；全局 API middleware 已设置 no-store。
- corrections/logic 没发现另一条共享 owner payload 旁路：natural_spec_corrections.preview/load_review/gate 先 natural_authority，要求自然规范专属 job_scope_gate 真值，四步家族返回 false；natural_logic_patches.checked/版本链亦先 scope+authority。metadata stop 分支不读取 shared owner payload。无需扩成相邻故障矩阵。

## 非作者前端源码核查

当前 internal.js SHA256 `b3dbb2c8b6dea775616e7089dcd0320f79afb9e8b9af0e00eee1d6e34433b26d`、owner-review.js `f0d89d54d9aa86a1a7e3b6945015cb6245ea58b95ab6360414c2389b940aa166`、use.js `e048edaf6d0ad2a417a9f04d4cb95eb7f8c19b48eb7b4d2fdf6d2c2cc6e1d28d` 已保存原字节；均 Node --check PASS。

- 目录文字准确区分成功 Run 人工验收、PARTIAL 无成果、UNKNOWN 与 PENDING，没有开放模型/发布承诺。
- 四步结果入口绑定该 typed version 的实际 Run；owner run 下拉切换先 showInternalRun，再读取该 Run 人工状态。切换 instance/project/identity/workspace、Run 和编辑/读取代次均进入原 fence，异步 hash 后重复 current。
- textWorkflowOwnerContract 绑定精确 Run/AppRun/Release、instance revision/data_version、typed fingerprint、输出/材料 SHA256，以及四个实收 receipt hash；先验证再以 textContent 渲染两组完整引用和报告，不执行材料 HTML。
- ownerPerRun 对旧 CSV view 的 spec:true fallback 保留；旧自然规范仍走 spec-owner-review，字面文本仍走旧 instance owner-review；新增 workflow 才走 text-owner-review。四步不进入自然规范 correction 入口。未发现新增 P1/P2 前端源码问题。
- 以上前端结论仅静态非作者审查和语法检查，尚无本审查人的真实 HTTP / Worker / JSDOM 正常链或原生浏览器资格。产品作者正在另行做实际 HTTP 页面资格，不在此冒认。

## 限制与原始证据

本报告没有执行真实模型、Windows/native browser、PG、远端 CI、部署、长测试矩阵或完整产品验收。所有原始短脚本、合成 DB、结果 JSON 与源字节快照保留在本目录；source-manifest.json 是最初捕获，wip-review-current-manifest.json 是本次后端修正与已采纳 UI 的精确输入。后续冻结后应核对这些输入与最终 Git blob，并仅补必要改变及正常自然规范兼容回归。
