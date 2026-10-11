# F2-T07：有限项目列修改与受影响应用重验

本切片从 `3e890e329332d434e8f3aa245cb15f905bb41455` 接续，独立分支为 `dev/project-column-revalidation-20261011`。依据原 [V5 §9](../sources/V5/平台产品设计.md)、[F2-T07 / AT13–15 / AT26](../分阶段开发计划.md)；实际结果见 [本轮证据](../evidence/project-column-revalidation-20261011/README.md)。原 `column_patches.scope` 对 PROJECT/语义依赖的拒绝继续有效，这是产品范围校验。

## 有限合同

- 全项目至多 16 个已有 canonical 单求和 CSV 草案，每个已有可信交付图。全部成员先经过现有候选、来源、权限和图锚验证，不能过滤未知成员后声称项目完整。
- 以目标应用唯一 CSV 材料 ID 定义应变应用集：该材料上全部固定单求和草案。每个应变应用只生成既有 sum 节点的列绑定 overlay，ID 保留、受影响下游 revision 加一。不同材料的应用为保留集，全部节点、内容和人工锁保持。
- 只容许服务端原固定 CSV 的精确 APP 语义免责声明；任何新增 UNKNOWN、PROJECT、SEMANTIC、MODEL_CANDIDATE 或非固定 CSV 成员拒绝。该声明不证明语义依赖完整。受影响应用有人工锁时拒绝；不同材料应用的人工锁可保留。
- 对象层修改集与扩验集分别记录，扩验不意味着全项目改写。资源内容、canonical AppManifest、旧历史、实例数据、Principal/Grant、内部版本和正式发布指针不修改。
- 保存的是整组不可变内部草案候选和验证回执。`finite_revalidation_completed=true` 只表示此有限 CSV 合同已重验；`semantic_status=UNKNOWN`、`owner_acceptance=PENDING`、`canonical_patch_executed=false`、正式发布关闭。不是全部 F2-T07/R0/P-A/P-B/人工语义验收。

## 实际执行与事务

预览冻结项目/主体、全部成员候选/图/授权/来源版本、原始人工锁登记（含修订）、具体旧列/新列及预算。精确指纹确认后，一次项目事务为每个应变应用保存旧列和新列两份原 CSV DAG 计划、Run、contract、event 与独立 seal；每 Run 使用原三步读取→求和→确定性格式输出和既有 worker，不新增执行器。任何后序成员接受失败，整个事务回滚。

worker 工具预算每应用 6 次（两个 Run 各 3 次），项目最多 96 次；模型预算 0，每个 Run 的原平台预算另行冻结。每项任务冻结 `accepted_at/deadline`，不能修改 Run 创建时刻延长期限。实际 worker 步骤使用原授权、取消、租约 fencing、期限和独立精确求和检查。

整组最终提交再次核所有 Run 的完整成功回执/版本/fence/结果、实际旧列/新列独立来源/行数/Fraction 求和及 worker 输出一致性，并重验全部成员/权限/锁/来源/预算。失败、取消、版本竞争、撤权、迟到或过期均没有检查通过的项目候选。保存 receipt+seal 后、事务提交前再核项目和截止边界；历史失败 Run/事件保留。

## 页面与恢复

在已有 CSV 草案的交付图区域打开“项目内共享 CSV 的局部列修改”。先读取已派生图，再选择旧列/新列并保存预览；核对全部应变/保留对象和预算，明确确认排队。运行由原后台 worker 推进。只读恢复得到全部实际结果后，再明确确认保存整组候选。

页面显示原请求键，冷页可填同一键恢复。预览、排队或最终提交的未知结果冻结原意图完整参数；恢复只 GET 原键与 definition，不 POST 重发。恢复必须与首次提交的旧列/新列、候选/图和指纹一致，迟到响应不能更新新身份/项目上下文。明确首次 POST 的事务拒绝可以改正输入；POST 成功后读回失败继续保留未知意图。

接口位于 `/api/projects/{pid}/apps/{aid}/project-column-patches`：POST 预览；GET `/{key}/definition` 和 `/{key}`；POST `/{key}/runs` 和 `/{key}/finalize`。后两步使用原预览键、精确 patch fingerprint 与 `CONFIRM_EXACT_FINITE_PROJECT_COLUMN_PATCH`。每步重新检查当前授权，GET 不派发任务、不保存检查。

## 验证边界

仅合成 SQLite、真实注册本地工具/worker、进程内 HTTP 与离线 JSDOM。测试页面使用 IPC 转发到 TestClient，无原生浏览器、loopback 服务或真实网络页面访问。未知依赖/损坏回执/末尾撤权等故障注入分别留档。PostgreSQL、Windows、原生视觉、真实旧源码升级、真实模型、完整 P-A/P-B 与人工语义/owner 验收均为 NOT_RUN；未重试历史被拒浏览器路径。
