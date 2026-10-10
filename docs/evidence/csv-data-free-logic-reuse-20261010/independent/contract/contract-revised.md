# 无原材料内容的 CSV 逻辑复用安全合同（实现前冻结）

基线 fab14d542d7efe41d0b290e5b5baec433a1669a9 / 产品709e0978。范围仅已有注册CSV、已实际成功且完整核过的无条件 read→sum[→report]。本合同是限定工程切片，不签完整AT10/AT11、语义或发布。

1. 原Release/Run/Instance/CSV读取继续使用现有实时原数据权限、图基线及完整回执门。不修改这些门以实现逻辑复用；原材料撤权、删去/退休不可读后，它们仍拒绝，不回传历史私有结果。
2. 新的逻辑复用授权必须由当前project owner在原来源尚能通过完整readRelease/实际成功证明时显式确认。采用原internal_approvals和delivery_graph_requests账本的新有限kind；无新表、Principal、资源读取Grant、执行器或模型。未取得独立授权时一律拒绝。
3. 已因新增注册/源码/Grant修订失效且未事先授权的来源仍拒绝补发，不放宽旧证明门。最小路径是先在成功来源上确认逻辑授权，再注册新CSV。此后新注册的Grant不会修改已签逻辑授权，也无需重跑原任务；目标自己仍须derive当前图。
4. 明确授权范围为本owner、本project内已有且当前具备用户/app-runtime读取及aggregate权限的固定CSV草案；独立授权有效期固定24h（与现有Grant缺省一致），可显式不可逆撤销。确认文案明确：仅结构可在原材料不可读后继续使用；它不赋予原/新材料权限，需单独撤销逻辑授权才能停止这份逻辑复用。
5. 对外/可复用逻辑仅含服务端allowlist生成的两/三步家族、固定action/version/规范化端口和step ID、原成功来源冻结cap、软件实现版本承诺、owner/project/逻辑ID/expiry及工程状态。不得保留原列名/列集合、goal/name、自定义step ID、原CSV bytes/hash、input/output/receipt data、自由描述或caller代码。typed schema来自固定五字段schema，不能复制自定义schema。
6. 不可变private审计只保存原release/approval/run/app的opaque ID与原release/approval指纹承诺，引用原封存记录；不复制原资源内容或操作回执数据，对外只暴露无内容的审计引用。每次复用允许读取原Release snapshot及approval payload封存JSON仅作hash完整性和opaque identity/version joins，不能把其goal/列/描述解释成执行输入、返回或复制到新对象；原snapshot没有CSV bytes。必须用旧承诺核验实际JSON而非只信stored fingerprint。绝不SELECT原resource或Operation input/output数据，不调用原数据权限来替代逻辑权限。原审计记录被修改/丢失、共同改签逻辑结构或未知版本必须拒绝。此依赖是不可变来源审计，不是原材料字节依赖。
7. 授权immutable payload及独立双origin seal核对；独立strict loader每次无条件核expiry，current consumed/revoked状态或任一独立撤销receipt存在均否定复用；不调用原approval(allow_consumed=True)的过期例外。一边缺失/重签、撤销后的单边恢复不得重新授权。撤销后重复只返回原撤销回执；不支持恢复或静默补授权。数据库管理员全面删除/改写权限账本不是产品授予的能力，不宣称抵御全DB重写。
8. 绑定新的目标需显式确认完整逻辑ID/指纹、target app/candidate/graph/rid/hash/数值列及request_key。同key换目标/列拒绝。新计划只保存目标数据绑定和逻辑授权引用，不复制来源私有执行快照。
9. 新plan使用reserved logic-plan- prefix，origin双receipt+normal plan marker精确关联，前缀本身要求完整授权与origin，删除双origin及双marker不能降级普通计划。load/enqueue/worker每次重核逻辑current授权、owner/project、目标版本/真实bytes/hash/schema、目标用户/app-runtime权限、手动锁/预算。source cap不扩大；平台收紧预算拒绝。
10. 每个实际resource.read/data.aggregate_csv仅指向当前目标rid；FrozenRunContract.resources只有当前目标。成功回执、sink及typed记录通过原worker与原严格schema/原子提交合同；原材料无需可读或存在。禁止混接旧值、偷读旧资源、复制原输入/输出或以旧result替代新结果。
11. 逻辑计划依然显式执行，成功后另行确认新目标Release/Instance。目标的后续同列/新列实例必须仍经逻辑授权门，不能通过新key丢掉来源逻辑marker而绕过撤销：逻辑实例使用reserved logic-instance-plan- prefix和exact原logic origin引用，任何前缀无引用都拒绝；控制pause/cancel可在撤权后保持原只读owner控制边界。
12. 新逻辑不能从material-derived或logic-derived目标递归授权；只有原已成功闭合来源可签，避免无限解释链。现有材料转移路径不自动升级为数据无关授权。
13. UI必须有当前项目的无数据逻辑入口，冷恢复不打开原app或GET原Release/CSV。新授权/撤销/目标计划三个独立确认。project/identity/selection generation及所有await后的current门；合法迟到接受先保存已核回执，再守卫当前页面。UNKNOWN保存原完整body/key，known只GET；坏200/接受ID不得paint或缓存新plan。
14. 必要实测：两/三步先授权→后注册→新材料真实结果/新Release/Instance/冷新列；原材料user+runtime撤权及删除/不可读时原GET拒绝、逻辑+目标执行成功且工具只读目标；未先授权/已失效源补授权拒绝；独立逻辑撤销/expiry/跨owner/project/目标撤权/版本/预算/共同缺seal/前缀降级拒绝；enqueue到worker之间逻辑/目标撤权无typed写；UNKNOWN/迟到/读取丢失恢复及旧源码升级拒绝/不迁移。PG用真实隔离DB/页面，SQLite不能代替PG权限/并发。
15. 作者与独审先审合同、再精确最终源码。来源/源码每次冻结，源文件变更前停止本人测试并等独审停ACK；不把不同SHA合并成一次通过。保留全部失败/中止和各字节桥。
16. 早期四PG DOMidle10、Report idle6、resources-history Future10、HTTP200损坏回执恢复及整体性能观察OPEN保留；原生fixed11不覆盖新增功能、不得冒充全仓。PROJECT PENDING/BLOCKED_PARTIAL、overall NOT_ACCEPTED、semantic UNKNOWN、owner PENDING、正式发布关闭、LIVE/真实模型0。
