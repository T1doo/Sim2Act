# 自然应用交付图入口：WIP 非作者预审

范围：root 唯一仓库写入者提交前的两生产文件 diff，以及新的 Python actual-HTTP/JSDOM 桥。此审查未运行产品、HTTP、Worker、模型、SQL、数据库、pytest/collect 或网络；没有仓库/旧 sealed 目录写入。CJS 尚待稳定稿，未对其行为或实际资格预写 PASS。

结论：**未发现两处生产改动的确定 P1/P2；Python 终态元数据 oracle 有一个应在实际资格前收窄的 P2 证据缺口。** 不是后端执行能力缺失，也不需要扩新矩阵或修改权限。

## 生产接线

`app.js` 自然 MODEL_SPEC_CHECKLIST 分支在 await openInternal 后重新核 app generation、项目、identity token 与调用方 selectionCurrent，然后仅对 `pa-natural-spec-app.v1` 调用 openDeliveryGraph，修复了原先跳过唯一图入口的 return。调用没有传递开页临时 selectionCurrent，避免 naturalFirstGuide / openGoalApplication 的 projects→apps handoff 后该函数永久 false。steady graph 仍由 deliveryContext/epoch/identity/project/activeApp/appSelectionGeneration 约束；clearApp、身份清理和项目切换会清图并更新 app generation。后续每次 graph API 仍须原 backend 授权/当前版本核验；本改动不提交 derive 或运行。

`manual-locks.js` 仅在原 CSV aggregate / bounded Report 显示规则外增加严格自然 namespace，CSV/Report 原规则未放宽。后端 `manual_locks.context` 已接受同 namespace，PA/PB 共同经过 delivery_graph_apps.load_family→自然 origin/current permission 验证。复用原 LockInput、CAS、canonical lock journal、manual pair/seal 和 LOCK_CONFLICT 门，不新增 API、executor、Grant、Principal 或发布能力。columnPatch、projectColumn、csvDag 仍有各自 executor/family guard，自然应用不满足。

现有 deliveryGraphSeal 已验证自然 graph 的 manifest/default ref、source versions、context hash 和 graph hash；naturalLogicReadGraph 就复用该函数。自然 graph 的 build 明确 dependency_edges=[]，外部 source version 与稳定 ID 逻辑与现有 UI seal 对齐，未见需要 backend 放宽。第一次 app 打开只显示入口；用户仍须明确 derive，锁/解锁后依 needs_derive 重新派生。first-guide 兼容性本次仅静态确认；新 case 只 PA actual，不声称又实际跑 PB 或整个 first-guide 长链。

## Python oracle 的具体缺口及同 case 修法

现桥已确认 fresh 无 graph/anchor/lock、无 AppRun/typed；generation 为既有 parallel fixture 的3次 Mock；实际页面只能出现7 POST，精确3 derive、lock/unlock2、locked preview400与unlocked preview201；所有业务表、Grant/Principal、旧 Release/实例均保持，page无Worker/模型/下载。生产哈希前后固定。这个范围合理，不需重跑上一20分钟完整链。

但终态目前把五张 graph metadata 表整体列为 allowed，对新增 metadata 只核旧行保留及最终一条 lock rev2/false。它不能排除锁冲突400额外写入 journal、其它 app/project metadata 或多余/缺失历史；因此当前 oracle **不能支撑“拒绝精确零写及完整锁历史”**，尽管它能支撑非 metadata 业务表最终无变化。

只需在现 case 加严格终态/回执比对：新增 journal 的 header 集合是3个 derive 单账、2个 canonical lock 单账、2组 manual_edit_lock+seal、1组成功 natural preview+seal，共11行；app/principal/key 必须对应页面原 POST；每行 snapshot/request 指纹正确，manual/preview 原件和 seal 完全一致，锁冲突 request_key 不得留下 journal。3个 anchor 只属于此 app、revision1/2/3，state唯一且指末anchor/snapshot，source versions/header 集合与第一次 anchor 一致；最终lock只属于目标节点、revision2/false，两次canonical/manual历史仍可核。严禁把 allowed 表的任意增量当作接受。这不新增产品动作或测试场景，只收窄已执行7 POST 的 oracle。

CJS 到稿后应再核：真实 app 进入且默认无graph，不通过 fixture 或直接API先derive；图与手工锁控件可见、CSV专控不可见；每次 lock/unlock 重新读 state、明确 ack、derive，锁冲突不触发 CHECK或版本；另一项目导航清图，返回后重新打开有当前上下文。现 Python 已禁止 checks/version/commit/use-runs POST。无需为这次接线增加恢复/下载/多版本/永久取消窗口矩阵。

## 当前读取字节

- `src/sim2act/web/app.js`：125060 bytes，SHA256 `70cd470333fee58d76ab12232f4184e96be236291ac07071991fda48659139c0`。
- `src/sim2act/web/manual-locks.js`：6177 bytes，SHA256 `a03a9638f6c0ce9dc78ee05ddf14d109ec92e2222ed054bfeed5ed08bc95034b`。
- `tests/test_natural_graph_controls_ui.py`：6319 bytes，SHA256 `d6a02f1cd46cb5ae64ada630cd38703855b381b263ed1a145b32b1a487e9a891`。

WIP 不是冻结资格；root 收窄 Python 元数据 oracle 并采纳 CJS 后，可继续静态冻结及唯一 PA actual 定向。此报告不背书之后未读改动或实际运行结果。新目录未封存。
