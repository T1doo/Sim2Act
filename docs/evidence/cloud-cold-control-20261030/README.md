# 大型 Cold：运行中读取、原子回滚与本人取消

基线 `7099c45a1a5b28ed0c6a66e35b925cb979b4f230`。后端实现冻结于 `fa29b2ae69a73616cb2b432465421b6991964a15`；`0ff86449bf7c9bf5a3601494fff953cef3f98cdb` 仅将测量观察器限定到实际 Cold 材料绑定，后端字节相同。前端收口源码为 `f05b7e411d656bbe3757f67fbe55791e69713906`。各次真实命令、起止时间、退出码及字节摘要分别保留。

## 实现与语义

没有把 G0/G1 拆到事务外、复用旧 PASS 或缓存权限。完整 G0、原五项写入、完整 G1、最终 guard 与提交仍属同一原子事务。独立只读、至多 0.2 秒 SQLite busy 等待的 metadata 查询，只返回当前 owner/实例绑定的已提交 Run 状态；它不读取正文、不承诺完整内容可读，不替代原 scope_run 或任何提交校验。

当前本人明确取消且原版本、principal/project/runtime/worker/fence 全部匹配、租约有效时，仅给同 Store 的当前线程结算 epoch 一个中断提示。原控制命令仍走原鉴权、scope 与 CAS。已有 checkpoint 看见提示后抛独立 BaseException，使全交易回滚，并依次释放 SQL、续约与结算锁。该异常不进入将模型结果标为拒绝的 DomainError 分支。之后有界等待原命令完成；未完成则不改 Run 版本、不进行 error settlement，保留 RECEIVED/DISPATCHED 及有限租约，交给原 fenced recovery。提示读取失败不阻止原命令，只是不提供提前中断。普通 Store、PG、内存 SQLite 不启用此本地协作提示。

**这解决长校验期间的控制生命周期，不是 CPU 优化或短事务拆分。** 跨事务移动 SQL 依赖、动态撤权、版本检查或 callback 会改变原正确性边界，本轮未声称具备可安全复用的不可变计划。不中断时写锁仍覆盖整个原子区段；普通完整详情查询仍可能等待。新增 metadata 与取消入口提供受限安全替代。

## 原大型输入：实际 HTTP 取消

`cancel-run.json` / `cancel-result.json` / `cancel.log/xml`：2026-10-30 02:52:32–02:57:56 UTC，退出 0。复用 `test_pb_spec_production_controller` 原完整输入，无人工业务延时、无替换校验/写入函数。原流程固定 Mock，6 次请求、0 次真实模型；文件 SQLite、真实时钟，另起原 create_app 的 uvicorn，用标准库 loopback HTTP 并发请求。

| 边界 | 实测 |
| --- | --- |
| Cold G0 实际开始后发起观测 | 已运行 3.108 秒，超过 1000 次原 checkpoint |
| GET control-progress | HTTP 200，0.137391 秒，RUNNING，content_access=false |
| POST 原 commands/cancel | HTTP 200，0.136372 秒，RECONCILING |
| 被中断 epoch 关闭 | 总 4.107900 秒，完整 G0 未结束，无提交 |
| 最大观测 checkpoint 间隔（含关闭尾段） | 0.334690 秒 |
| 取消前已提交租约余量 | 116.861184 秒 |

原模型响应早已 RECEIVED、operation 已 DISPATCHED，故正确回执是 **RECONCILING**，不能冒称已取消确定外部副作用。断言核实该 RECEIVED 全行、既有五条 attempt、全部资源、typed data 和请求/响应归档逐行不变；无 NS_SETTLED/NS_REJECTED、无新成果。原 happy path 只允许其精确“最终必须 SUCCEEDED”断言在取消案例中分歧，随后做上述独立回滚检查，其他失败不被接受。

取消原件的 epochs 列表含两次上游 Source 小区段；它们不是 Cold。目标是 `target_run=run_0b49b01f422f479dad46af0174c5ae43` 的最后一个 G0 epoch。后续观察器按实际 Cold 绑定筛选，但原件未改写。该中断的 `settlement_lease_margin=115.889337` 是原预留区间截至观察时的名义余量，**不是取消后实际 Run 获得续租**。

## 原大型输入：不中断的完整保存链

`complete-run.json` / `complete-result.json` / `complete.log/xml`：03:01:17–03:10:13 UTC，退出 0，原完整流程所有断言通过，7 次固定 Mock、0 次真实模型。重新构造 Store/client/Worker 进入 Cold，保留同 key 去重、来源、权限、完整双 guard、归档和成果历史断言。

| Cold 结算 | 完整原子区段 | 完整 G0 | 原预留 120 秒区间余量 | 最大观测 checkpoint 间隔 |
| --- | --- | --- | --- | --- |
| 第一次 | 94.928129 秒 | 38.166727 秒 | 25.069267 秒 | 1.013305 秒 |
| 第二次 | 96.171462 秒 | 42.974960 秒 | 23.826216 秒 | 0.457423 秒 |

完整区段减 G0 还包含写入、G1 和提交，不能当作精确纯 G1 profile。这里没有扩大既有 120 秒合同，**也没有证明原 30 秒目标通过**。观测间隔不构成所有输入上的硬响应保证；尚未单独实测 G1 尾部取消。两次提交成功不能推导控制修复造成 CPU 降幅，仍有机器负载/输入规模风险。

`reopen.json` 来自独立新 Python 进程，只读打开已关闭的同一 SQLite，核实 Cold 为 SUCCEEDED、唯一成果 v1、app output/typed data 与已保存 HTTP 结果相同、Cold 两次 attempt 均 VERIFIED；全过程数据库 SHA-256 不变。三条生成 attempt 按原模型归档协议保留 RECEIVED，上游 Source 与 Cold 四条 VERIFIED，未擅改历史状态。这是 SQL 持久化核对，不是重跑鉴权或 Windows 进程验收。`check-reopen.py` 可复核；初次辅助检查误要求全部七条 VERIFIED，发现上述真实协议后改为分别核生成与执行状态，未修改数据库或生产代码。

## 前端实际协议与独审

完整详情尚在等待时，已鉴权实例历史中的原 Run 立即有独立“读取后台状态 / 取消原任务”入口；新提交未确认回执不得借此变成已接受状态。只有明确读取当前 metadata 后才能按原版本取消。该控制不受完整详情的 busy 阻塞；确认取消前使旧详情响应失效。页面只保留一个取消入口，pause/resume 保留。身份、项目、实例、Run、连接和工作区变化均使旧请求失效，fallback 前也检查，避免新 token 请求旧 ID。metadata 及取消 ACK 不清原 key、不成为成果或导出资格。

取消 ACK 严格限原 envelope 三字段与 CANCEL_REQUESTED/RECONCILING/CANCELLED；丢 ACK、错误形状和其他状态均保持未知，需明确重读，不自动重发。原 owner control-status 作为不支持投影或投影绑定拒绝后的 fallback，仍完整重鉴权；错误 HTTP 200 内容不触发 fallback。

`reviewed-with-old-ui-fixture.log/xml`：23 项通过，1 项失败；唯一失败是 entry-fence 脚本寻找已移除的旧取消按钮。脚本改为显式读取后台状态再点击唯一取消入口，仍要求原 Run CANCELLED 且无结果。`entry-final.log/xml`：该真实 HTTP entry-fence、独立 busy 控制页面、原修正回执入口共 3 项通过。保留的前次 known-ui fixture 失败是其尚未实现新 GET route，已补 metadata 路由且未删原断言。UI 的 JSDOM 合成 HTTP 结果与真实 HTTP/SQLite entry-fence 分别标明，均不能叫原生像素/桌面通过。没有重复大图跑来掩盖失败。

独立只读 reviewer `/root/desktop_final_review` 已核后端与上述三处 UI 修正，无剩余审查阻塞，见 `readonly-review.json`。原生产资格规则未变，143 个实际文件逐核，新增 `_sqlite_run_control.py`，原 142 项无删除；新 pin `46d6ad7c151c1c38b64760b15ee7838d7a8b3bb0ddc9fe78615e23ef9c82d492`，原 `_qualified()` 实际通过。两个 Linux 原生模块身份与全部本轮 UI 字节见 `source-and-qualification.json`。

## 未验边界

全为云 Linux、明确 test_only 文件 SQLite、固定 Mock。未作真实 Intern 调用、正式 PG/live、Windows WebView2/EXE 或实际像素验收；未访问用户电脑；未启动第四次 CI，剩余 506 秒仍保留。main/Release/部署均未改。正式外部 live 输入缺项及先前证据限制未被这次本地成功覆盖。现有零费授权无变化，本轮无需新凭据、费用或安全权限。
