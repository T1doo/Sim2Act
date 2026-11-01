# 独立租约控制与最终提交屏障：实际闭环

最终应用源码：`5db5a71fe3cf73efe9a0201545a5427835ba09bb`，分支 `dev/cloud-g0-live-20261028`。没有修改 main、发布 Release、部署、运行新的 Windows CI 或使用用户电脑。

## 真实改变

新建合成 SQLite 工作区使用有版本的主库/控制库协议。30 秒仍是 worker 的滚动有效租约，不是整段操作的完成 SLA。心跳在独立控制库真实提交，绑定原 Run/owner/version/fence、固定绝对截止时间和进程单调时钟；不改历史 Run.lease_until、不复活过期 worker、不缓存 Graph 或授权 PASS。

Store.guard 将原业务事务绑定到私有原生提交范围。实际业务写集与协议回执处于同一主库事务，随后保留完整 G1。最后短暂持有控制写锁，执行原检查/回调、核对当前控制代际、取消/暂停、stop、双时钟、文件身份及实际物理连接，再调用实际 SQLite commit。主库确认提交与控制 ACK 失败分开记录，不能误报回滚或重放。既有数据不自动迁移；原签名 120 秒合同不改，其他 family 保留原路径。

完整自然任务消费者已改为同快照身份检查和鲜活控制租约；不可变证明使用原绝对 deadline。计数器严格验证新增标记及领取回执。新协议未进入原无 SQL 的私有 counter 快路，保留完整 checkpoint 路线。动态权限/撤权、版本、取消与 W5→G1 原子性没有删除。

取消/失联恢复先在实际主库 writer 下关闭旧控制代际，核对/ACK 或 ABORT 真实回执。已耗尽原绝对 deadline 且无未决操作的工作明确 FAILED/BUDGET_EXHAUSTED，不重新领取；取消/暂停同步 Run 与原接受的 AppRun。同步前重算完整绑定 snapshot hash、核 owner/instance/release/request 指针，且仅允许空输出和空 result_version，不覆写成果。

## 分版本验收，不能混签

| 场景/源码 | 实际结果 | 范围 |
| --- | --- | --- |
| 两笔大型 Cold，`66f1bc62354bf5fa996e6e21bcce4b0a59cf6f14` | 原 TrialCaps.lease_seconds=30、真实时钟；两笔 COMMITTED，最终 SUCCEEDED，24 ACKED；首个新进程正常查询 SUCCEEDED、全部业务/协议行指纹不变 | SQLite test_only；7 固定 Mock、0 live |
| Cold 1 | G0 42.572954s，writer 59.493538s，总 102.067327s | 完整 G0/G1、未扩大 lease |
| Cold 2 | G0 45.837719s，writer 64.917686s，总 110.756078s | 同一大输入、完整五写和回执原子提交 |
| 实际持锁 HTTP 取消，最终 `5db5a71fe3cf73efe9a0201545a5427835ba09bb` | BEGIN IMMEDIATE 冲突确认 writer；GET 0.022337s，取消 HTTP200 0.046739s；Cold 事务 ROLLED_BACK（G0 51.520568s、持锁 0.623566s）；默认恢复 CANCELLED，0 结果、0 重放；新进程查询一致、控制 CLOSED | 6 固定 Mock、0 live；不是延时 mock；合法中间态可为 RECONCILING 或 CANCEL_REQUESTED |
| 真实 Intern 小目标，`31edad3f734efd923ffc28a2af487802fff2b4c2` | 既有免费 intern-s2/原 endpoint，2 次真实调用、1701 tokens、5.548355s，SUCCEEDED/PASS_EXACT_READ_CONTRACT；正常关闭、首次同 origin 重开和同键无重放 | 单个合成文本逐字合同；不是大型 Cold/PG/任意自然目标 |
| 到期恢复，`31edad3f734efd923ffc28a2af487802fff2b4c2` | 实际失败 before-image，控制已 CLOSED/主库未收口的崩溃边界；FAILED/BUDGET_EXHAUSTED，保护表整体指纹不变，重复处理无重放 | 保留原时间戳；0 模型调用；后续 5db 只补停止态同步 |
| 安装后，最终 `5db5a71fe3cf73efe9a0201545a5427835ba09bb` | Linux CPython3.12 wheel：194 源资源逐字节核对、4 原生扩展实际导入且匹配 wheel；32 项相关回归；正常 CLI/真实回环 HTTP：CSV=30/v1、同键去重、SIGINT→STOPPED/clean/exit0、首次重开一致；隔离卸载仅移应用、工程不变 | 默认 0 模型；未在 wheel 二进制上重跑大型两笔 Cold；不是 Windows EXE |

`normal-66/`、`cancel-5db/`、`live-31/`、`installed-5db/` 保留各自源码身份。最终 5db 的两笔正常大型保存没有重跑，不能把 66 的时间签成 5db 新测量；其后修的是到期与停止恢复，已独审和实际反例验证。真实调用仅核环境 token 存在布尔并由既有适配器使用，没有打印/保存值、创建凭据、付费 fallback 或隐藏重试。

## 失败与修正保留

`failures/cancel-v1.*`：观察器误查不存在的 context stage，0 次取消请求；该次最终证明达到原 300 秒任务预算而保留 RUNNING。`external-probe-no-request.json` 的有界后续探测没有发现仍持锁的 writer，0 请求，未盲重跑。

这暴露真实到期恢复缺口，已修为明确 FAILED，已验证原响应、usage、已验证操作、typed 数据、绑定和协议回执不变。未把这个失败当成功，也未改变原期限。

`failures/cancel-v2.*`：真实请求已阻止保存，但合法返回 CANCEL_REQUESTED，旧测试过严要求 RECONCILING。修正观察器中间态断言，仍要求实际最终 CANCELLED、无成果、无重放；并补齐默认恢复的 AppRun 同步。最终 v3 完整通过。畸形 JSON、bool 冒充整数、绑定 snapshot 内容变异/旧 hash、过期旧 owner、stop/期限/控制文件失效、实际续租跨历史锚和取消/暂停均保留必要反例，无生产校验跳过。

## 实际边界

长写锁仍约一分钟，原 300 秒任务预算在大图上余量偏紧，并已有一次到期负例；本轮修复了租约生命周期和正确失败收口，没有宣称稳定性能 SLA 或所有大输入均可完成。新协议仅是显式 test_only 文件 SQLite 本地版，正式 PG 未验且当前没有 SIM2ACT_DATABASE_URL，也没有实际 principal/project/trial/approval/account 选择；没有补造。Windows 新 C/宿主未验，未运行第五次 CI，未使用 PC。

固定免费模型的小目标已真实通过，任意自然目标和整体语义验收仍不支持/未验，人工 owner_acceptance 仍 PENDING。旧 5af 限制候选保留。候选包不是完整产品 Release。

## 独审与工件

独立只读审查核过最终提交控制锁、实际 commit/outcome、回执 ACK/ABORT、文件身份/stop/双钟、末端清理和消费者。修复了审查发现的终态历史租约判断、停止前 owner/实例授权、RECONCILING 代际退役、counter 私有纯段 SQL/JSON 类型和恢复 snapshot 自报 hash 问题。审查结论只覆盖代码范围，不替代平台/模型/语义验收。

包、精确哈希和安装/退出/卸载范围见 [最终 Linux 限制候选](../../../deliverables/lease-controlled-local-20261101/README.md)。没有打包数据库、真实身份、令牌或私有配置。包内 BUILT_NOT_ACCEPTED 是构建时不可变记录；以上安装后验证另存，不篡改已测包。
