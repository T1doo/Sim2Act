# E19 已认证内部工程入口

原 F2-T05/T08/T09 的已有服务集成：应用页打开获授权草案后进入“内部工程入口 · 只读运行”，核查→回读精确冻结快照/检查/到期/指纹→人工勾选确认→保存内部 Release→创建独立实例→提交持久 AppRun→读取状态、结果版本/历史，暂停/继续/取消和重新打开。正式发布/部署仍关闭；不是通用生成、业务 writer 或完整 AT22/F2 签收。

API 统一沿用 Bearer 认证、同源限制、严格重复键 JSON/禁止额外字段及当前 user/project/app 授权，交给原 lifecycle/app_jobs 服务，worker 仍走可信 resource.read/data.aggregate_csv 及独立 oracle；无模型请求、任意代码、外部目的地、新身份或 Grant。批准不能由客户端提交或编辑 snapshot、schema、namespace、权限；prepare 只接收期望草案 fingerprint 和核查输入，GET 返回已持久冻结内容，commit 只接受精确 fingerprint，当前来源/授权版本/到期重验，重复确认同一批准只返回原 Release。

| 路径（均 /api/internal） | 行为 |
| --- | --- |
| POST /apps/{aid}/release-approvals | 当前草案 fingerprint + sample_input，独立检查后冻结内部批准 |
| GET /approvals/{aid}；POST /approvals/{aid}/commit | owner 回读精确快照；精确 fingerprint 确认，不开启正式发布 |
| GET /apps/{aid}/releases；GET /releases/{rid} | 当前授权下不可变内部版本读取；先按所属 app 筛选，避免无关失效版本阻断 |
| POST /releases/{rid}/instances | expected_release_fingerprint + request_key；相同 owner/Release/键的持久实例 PK 幂等，project 锁串行；不新增表 |
| GET /apps/{aid}/instances；GET /instances/{iid} | owner 当前权限；实例独立数据/历史，队列运行 ID 与结果版本回读 |
| POST /instances/{iid}/runs | expected_revision/release fingerprint/input/request_key；返回202已持久接受；既有 worker 队列执行 |
| GET /instances/{iid}/runs/{rid} | owner + 精确 instance/accepted binding/current grant；不跨实例读取缓存 |
| GET /instances/{iid}/runs/{rid}/control-status | owner + project/accepted binding/instance；仅 ID/status/version/cancel_intent/content_access=false，不返回输入、结果、错误、事件、资源或 snapshot。停止控制不恢复授权 |
| POST /instances/{iid}/runs/{rid}/commands | 既有 version CAS/pause/cancel/resume；停止允许撤权后 owner 操作，resume 仍需当前权限/无未知效果和取消意图 |

实例 idempotency 使用原表 PK 和 owner/Release/request_key 指纹，存储稳定性由原 project 锁和 DB 唯一 PK保证；实际运行仍为原 Run/Operation/lease/fencing/heartbeat。若原创建实例已切到另一个 Release，再重试原创建键保守冲突，不新建/重绑。现有表均由原显式迁移/Setup，API/worker 不建表；PG最小CRUD角色实际完成新入口全过程。

页面每个 app/token/project/instance/run 选择版本隔离返回；跨项目/实例切换及取消选择只改变页面，不取消后台已接受任务。重复点击 busy；POST回执丢失保留同键意图，用户显式恢复，不自动重发。已接受 ID 后读取失败可用历史重新打开。旧revision拒绝时保留旧意图；用户可显式读取当前实例历史后结束本页旧请求重试，然后另点新提交，不删除服务器历史/取消后台/自动新运行。撤权后清除受保护输出，显示 owner 最小控制状态以停止任务。

独立审查实际复现同app迟到创建回执抢回刚选择实例，也发现刷新回读后可能重开旧实例；创建POST及refresh await前后、刷新按钮均补 instanceGeneration 前置检查。真实 HTTP + jsdom 交错负例和独立最小DOM复验关闭。独立复验不是浏览器视觉，PG/CI由主开发另核。

受保护浏览器正常 CLI 首次 socket目录只读；官方 AGENT_BROWSER_SOCKET_DIR 指向本轮/tmp后，Chromium仍因系统SUID sandbox helper不正确而abort。没有采用--no-sandbox提示或修改系统策略。仅DOM/HTTP检查与手机CSS规则，不声称真实桌面/手机视觉通过。

[本轮证据](../evidence/F2-internal-entry-20261006/README.md)。[原 V5 阶段门](StageGateReview.md)仍保留：F1/Win11/完整两路径与任务族、通用DAG/局部修改、正式发布/数据writer/迁移、受控外部在途效果核对及真实浏览器。内部工程入口现可实际使用，不等于放行正式发布。

最终aaf07f49/[精确CI37419363378](https://github.com/T1doo/Sim2Act/actions/runs/37419363378)SUCCESS/PG372PASS0SKIP，API19项含最小CRUD角色、DOM/HTTP29项及独立复验归档。此入口不包括内部兼容升级/回退switch页面，也不启用正式部署。真实浏览器/手机视觉仍BLOCKED，首次本地AT05启动失败仍保留未定位，不改历史。


## E21后续真实浏览器验证（WindowsServer，非Win11）

[E21证据](../evidence/F2-protected-server-browser-20261006/README.md)：精确2ead9b6/CI37423790107 SUCCESS，正常保护的预装Edge、25真实检查PASS。上述内部最小认证/快照确认/实例/排队暂停取消/返回重开/worker结果与独立历史/跨owner-instance-history-control拒绝实际运行；desktop1366x900/mobile390x844 PNG人工查看，两布局可读且无横向溢出，长实例ID标题已修换行。CSP/sandbox/系统策略不放宽，renderer token实际AppContainer/restricted true/integrity0。

E19段的BLOCKED是当时Linux路径事实，本轮WindowsServer正常平台补上该最小流程视觉；Linux仍BLOCKED。仍无物理手机/Win11/其他browser/完整前端或正式发布签收；撤权stop UI及更多迟到响应未纳入本次25项。仅test_only合成SQLite浏览器fixture，原PG372PASS另外通过。三个真实失败及修复记录保留，不用先前DOM29冒充本轮浏览器。
