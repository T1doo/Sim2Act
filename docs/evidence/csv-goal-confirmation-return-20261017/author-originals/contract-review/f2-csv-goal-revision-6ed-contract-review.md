# CSV Goal 修订重入确认：后端合同只读审查

基线 `6edb626c4203def2a735006e860dcbca807315df`。root唯一仓库写入者；本独审只读8份源码/测试，未执行测试、HTTP、Worker或模型，未改仓库。

**确认父审阻断成立，6ed不能据现有测试改签修复。** `csv-goal-revision.js:16`按owner保留Map中的entry；`:21–22`新建空proof/select，但`:142–148`仍以缓存preview/approval/adoption决定确认可用。离开后新controller因此能在未重现/重核冻结内容时重新勾选并发起尚未发送CHECK、Release commit、CAS commit。后端仍会重验权限/版本，不等于前端已取得充分、可见的本次知情确认。

## 后端已有读取链，不需新API

| GET | 真实合同 | 对重入的意义 |
| --- | --- | --- |
| `.../csv-goal-revisions/context` | `context:180`先source_gate(current_head)，当前instance/Release、Goal head、同材料snapshot、graph/authorization、numeric columns；返回完整principal/project/app/runtime、releaseid/fp、instance revision/data_version、Goal/version/fp、sourcehash、graph及grant信息 | 新CHECK/新准备必须相同当前scope，不能用历史receipt替代。采用修订Release后此接口按设计拒绝，不能作为已采用CAS的恢复前置 |
| `.../previews/{key}` | `load_preview:251`原key paired seal、完整冻结Goal/旧Release/material、重算有效candidate/impact/fp；默认`current=False` | 可以恢复原冻结内容，但不证明当前Goal/实例/graph仍能新CHECK。显示原baseline_input→input并禁改，不能用空selector默认值 |
| `.../checks/{key}` | 原preview与CHECK pair、真实Run归属；未成功返回状态，成功由checked重验独立实例v1结果及output/plan/check指纹 | 绑定原preview/check请求hash与确切run/check_instance；首次成功GET可能remember CHECKED proof，不宣称全库零DML；不新建Run、不重POST |
| `.../version-approvals/{key}` | 原preview和APPROVAL paired历史 | 仅恢复历史snapshot，**不检查批准当前expiry/consumed**。不能单凭该GET恢复未发送commit确认 |
| `/api/internal/approvals/{aid}` | owned release批准、完整payload hash、源权限/bytes、revision family/snapshot proof；未消费已过期拒绝，已消费允许历史读取 | 未发送Release commit前再读本接口，核同aid/fp/principal/project/draft/preview/check/Goal/input/expiry，展示完整snapshot并要求新ack；consumed应读原Release回执，不再POST |
| `/api/internal/releases/{rid}` / app Releases | `read_release`核授权及完整不可变源链 | commit未知可按精确approval_id查原Release，再读同id/fp/source。不能仅按“有同Goal新版本”确认接受 |
| `.../adoption-approvals/{key}` | 先source_gate，原adoption pair，再`inspect_switch_approval:1002` | 对未消费批准鲜明校实例/project/expiry300s、原revision/fromRelease、targetfp、data version/hash、grant、logic dependency、保留数据schema。最适合CAS前重新核冻结批准 |
| `/api/internal/instances/{iid}` | 当前owned instance/Release/typed history | CAS已成功但回执丢失时，switch审批已consumed，前一GET会409；应先用instance history证明是否**同一approval_id**已完成 |

`lifecycle.commit_release_tx:283`新写前后会`csv_revision.validate_snapshot(...current=True)`；旧同approval提交可返回既有Release。`commit_switch:1048`仍严格校当前revision/fromRelease/data/hash/grant/target/dependency并SQL compare-and-swap，事后再核history和consumption；无须为UI恢复改这些边界。

## 最小安全恢复模型

- Map只保存原key、冻结request bodies和接受/unknown历史；每个新controller另设未验证状态。所有新POST/ack先锁住，不能把entry历史对象等同本view已授权读取及已展示。
- 在当前view scope内按已有最高阶段GET重读父链和当前context；每个await后校applicationUse对象/身份连接代际/项目/实例/工作区代际/controller归属，另核当前instance release/revision/data-version与冻结signature。await hash后同样校current。离开并返回同一身份/项目/实例仍是新代际，迟到旧链不得继续GET、paint或解锁。
- 复原完整可见proof：原实例与冻结Goal全文/version/fp、旧列→新列、材料hash/影响范围、独立CHECK Run/结果、目标Release与批准expiry、CAS from→target/revision及保留结果说明。select值由已GET的冻结baseline/input设定并禁改。所有ack一律unchecked，不从旧view保留。
- 未发送CHECK：fresh context与原preview.context全等并显示原preview后才启用CHECK ack。未发送Release commit：fresh preview/check PASS/version-approval及当前generic approval、context相符后才启用Release ack。未发送CAS：target Release及fresh inspect_switch_approval相符后才启用CAS ack。
- 原key未知/accepted-read-error恢复必须是独立GET通道，不受新POST“已展示/勾ack”的门阻挡；可从steps[stage].body及原key/aid恢复父链。现handler先依赖preview/proof/release/adoption，而deny会删这些对象，修复时须防清缓存后recover点了直接return的死锁。禁止恢复缺证据后fallback新POST。
- 403撤权清私有proof/selector/ack并保留原key及unknown接受状态；409权限修订/Goal/graph/实例漂移或批准过期锁新写，不静默换key、不当作已证明未受理。只有原proposal_tx的完整NOT_ACCEPTED+ABSENT+TX_ROLLED_BACK证据可明确启新key；一般404/409不够。
- CAS未知应优先检查当前instance：精确iid/project/runtime、target id/fp、origRevision+1、保留data_version与history同a.id/from_release_id/target/revision匹配，才确认原CAS接受。只看target/revision/runtime不足以区别另一个approval完成同target切换。若未完成再GET未消费approval；若冲突/无法证实保留unknown，不再POST。
- 原baseline按钮会POST graph/derive；不要作为导航后的自动GET恢复器。恢复只GET已有资源，不能自动derive或创建任何新阶段。

## 修复冻结后最小验收建议

三个“尚未发送”位置各做离开/返回：preview后CHECK前、Release approval后commit前、CAS approval后commit前；返回时必须先重读、冻结proof非空且字段精确、ack清空、0新POST，再用户显式勾确认后才一POST。可用轻量full DOM合成API覆盖所有hold/403/409/过期/畸形scope与workspace/project/identity/instance ABA，配现有实际API/NoModel Worker完整模块回归。

另保留实际202丢CHECK、Release commit丢回执、CAS commit丢回执后的原key GET-only恢复；已accepted不得重发，unknown不得reset，迟到旧POST/GET只影响原durable intent且不显示到当前其他scope。GET checks的CHECKED sealing应单列，不能把恢复误报为全库不变。已存在的4个visible cases主要覆盖发送中导航及同view轮询，未覆盖本次三个未发送确认重入缺口。

本报告是修复前合同核查，不签修复结果。等待root给修复冻结SHA和实际回归后再有限独审。不扩模型/旧恢复矩阵；新功能仍暂停。

源码hash证明：`/tmp/f2-csv-goal-revision-6ed-contract-review.json`，SHA256 `dc5570cc462689e8e322d9fb04d8ff9142c818deaf196f8d30047ea2429bbe64`。
