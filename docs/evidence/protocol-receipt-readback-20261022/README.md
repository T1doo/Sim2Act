# 已接受核查的冷页只读找回

本片关闭原 F2-T09/AT05/18 的一个明确子项：页面内存清空后，从既有任务历史打开原 Source/Cold，点击 **“找回已接受核查回执（只读）”**，用已有持久记录找回原核查键与回执，再新鲜读取当前成果。不会提交核查、重新生成键或自动提取/运行/发布。

基线 `3492531b31d8fb6e1677dc627e6bf7cf920c9101`。最终冻结五份源码的测试结果 **14 PASS / 0 FAIL / 0 SKIP，4.75 秒**：12 个本片测试与两个既有控制器兼容测试。没有重复后台大套件、PG provisioning 或 CI。完整原文见 [final-pytest.log](final-pytest.log)，范围与预算见 [summary.json](summary.json)，源码见 [冻结清单](frozen-source-hashes.json)。

## 持久记录与运行边界

已有 `protocol_reviews` 行保存原 `ReviewInput`、公开回执字段及完整规范 payload，另有 `PROTOCOL_REVIEW` event 封印。新增项目/Run 下 `GET /api/projects/{pid}/protocol/runs/{rid}/review-receipt` 复用 `_pending`、`_validated_review`、固定合成 `_oracle`，重查当前 owner/项目/Run、授权、来源字节、结果和封印。路径项目必须与 Run 实际项目及主体一致；仅返回原请求与既有公开回执，不返回 gold/rubric/payload。

一个有效记录和一个匹配封印才返回 `FOUND`。多记录不取首/最新，直接拒绝歧义；缺行但有封印/成功状态、缺封印、内容损坏均拒绝。完全没有接受证据且仍待核查才为 `NOT_FOUND`，这**不证明请求从未发送或当前没有在途请求**。

新入口不调用 `review()` 或任何完成/恢复 writer，不新增表、migration、事件、localStorage、凭据或授权。三份正向数据库均与原封存库逐字节相同：[物理字节见证](positive-db-byte-witness.json)；每次 locator GET 前后比较全部 55 表 typed digest，并断言仅 SELECT/BEGIN，四份 sidecar 始终原字节。测试用 SQL 注入负例在 GET 前建立，不是 GET 修复或写入。

页面只读流程精确验证返回结构、原请求、回执与新鲜当前 Run。新鲜读取失败时保留原键并清空成果、提取/Cold 路线及可见回执，只能重读。`NOT_FOUND` 也清除旧 PASS 展示，保留旧内存键且关闭本只读恢复，不能据此生成新键；页内 UNKNOWN 与服务端不同 body/key 时拒绝覆盖。迟到响应在身份、项目、Run 或工作区切换后不得恢复键或内容。首次新核查仍是原先独立的显式确认流程，并非这个只读恢复入口。

这不是通用 UNKNOWN 恢复：没有持久接受证据时，冷页无法区分从未提交、提交未落库或仍在途，不据此重发。Source/extract V2 completion 的 event/journal 镜像、state-only recover 仅有 request fingerprint，合同不同，本片未接其冷页回执。旧完成/恢复入口、期限、授权和发送预算保持原样。独立 Source 完成不能被核查找回失败阻断。

## 实际验证

- **封存 Source/Cold**：直接复用 [Cold HTTP 已完成封存库](../protocol-cold-review-http-20261022/runtime/after.sqlite.gz)，先核旧 manifest 压缩字节 SHA，再载入四份既有 sidecar；没有生成新 Source/extract/Worker 或模型事实。[Source 原键回执](source-receipt.json)、[Cold 原键回执](cold-receipt.json)经认证 ASGI GET 取得，新 Store/API 实例重读逐字节一致。此为同 pytest 进程新连接，不称 OS 重启或真实 TCP。
- **拒绝用例**：缺 row、缺 seal、改 seal、改 payload、改 result_snapshot、多个 row、撤权；无认证/invalid bearer、错误项目、同 owner 的另一项目路径、extract phase 均关闭。没有测试另一已认证 owner token，不以 invalid bearer 代称跨 owner 实测。
- **新控制器**：[25 项 VM 检查](controller-result.json)从空 Map 找回真实序列化原件，发现/恢复仅 GET；测试原键冲突、严格类型/Unicode key、失败读取、旧 PASS→NOT_FOUND 和四类上下文迟到隔离。另一个纯 VM 假完成命令证明“独立 Source 完成不受失败核查读取阻断”；该一个 fake POST 不是实际业务 HTTP、MockProvider 或模型请求，已与只读流程零 POST 分列。
- **兼容**：[原核查控制器](review-compat.result.json)与[原完成控制器](completion-compat.result.json)逻辑测试通过；不重跑 Source/Cold 旧后台套件，也不把此前原生 Edge 结果签给新控件。

实际业务新增模型/MockProvider/Source/extract/Worker/acceptance/reservation/POST 均为零。外层墙钟上限 120 秒加 10 秒退出宽限，Node 子进程上限 30 秒；本轮实际 pytest 4.75 秒、exit 0。TestClient/Store 在 finally 关闭/dispose，无服务或自有常驻子进程启动；保留自有临时库作为证据，不操作未知进程。现存 Starlette/httpx 弃用 warning 原样保留，没有安装新 SDK/依赖。

## 独审和失败保全

[设计](DESIGN.md)先经独审再接运行路径；[独立回执](independent-review.md)保留限制与发现。首轮 **11 PASS / 1 FAIL，4.13 秒** 原件见 [first-failure/pytest.log](first-failure/pytest.log)：测试 VM helper 在清空上下文后直接读取 null；已修 helper，不改产品门迎合测试。独审另找到两项真实 P2：误把核查状态用于阻断独立完成，以及 `NOT_FOUND` 留旧 PASS 展示；均最小修正并由最终定向反例覆盖。

冻结源码运行后不变。未验仍包括新控件原生 DOM/Windows 像素、PG、OS 重启、真实 provider、G0 与真实任务语义；owner PENDING/未发布不变，本片不能称整个 F2-T09/AT05/18 完成。
