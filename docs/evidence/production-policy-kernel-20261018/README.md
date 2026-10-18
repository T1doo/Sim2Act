# 未安装 policy 内核的有界资格与独审原件

基线 `842a5b46d52131581edcbfa235ef067cc44b809b`；生产冻结 `c62bfb90d23234c6ce56c78bf6c441d6ca1a7703`；取消 oracle 补强后的测试冻结 `20a43aba27e6276046cd9ae25ac090f02bff89ba`。普通分支 `dev/production-policy-kernel-20261018`。实现及限制见 [F2 记录](../../F2/ProductionPolicyKernel20261018.md)。

新增内核复用真实 Run/approval/phase/lease/fence 检查，独立验证来源结果，并实现不可变的预留、attempt 标记、结算和同账户 cursor。它没有被 API/Worker 安装：所有 transition 固定 live/dispatch/real-source=false，旧 resolver 仍默认拒绝。合成来源结果、wire、usage 与 reservation AttemptID 均为离线输入，不证明实际账户、免费权益、生产 Attempt 或模型语义。

## 实际执行

| 冻结 | 唯一节点 / 执行 | 结果 | JUnit / 外层耗时 |
| --- | --- | --- | --- |
| 生产冻结首轮 | 19 / 19 | 19 PASS，0 FAIL | 51.382s / 54.792128842s |
| 取消 oracle 补强 | 1（承接同名节点）/ 1 | 1 PASS，0 FAIL | 3.145s / 5.68968525s |
| 合计 | 19 / 20 | 20 PASS，0 FAIL | 分轮保留 |

最终资格是首轮 18 个未改变节点与补强取消节点，**没有声称最终测试 SHA 整套重跑**。首轮含 7 个新 policy 节点及 12 个直接受上下文提取影响的原节点。取消补强仅修改一个测试函数，135 个生产输入全部相同；其余节点顶层 AST 未改。原首轮取消记录仍保留。

- 首轮：[精确命令与退出码](first-run/execution.json)、[JUnit](first-run/junit.xml)、[stdout](first-run/pytest.stdout)、[stderr](first-run/pytest.stderr)、[runner](first-run/runner.py)、[冻结源码](first-run/frozen-source/src/sim2act/production_trial_policy.py)、[冻结测试](first-run/frozen-source/tests/test_production_trial_policy.py)。
- 补强：[精确命令与退出码](cancel-followup/execution.json)、[JUnit](cancel-followup/junit.xml)、[stdout](cancel-followup/pytest.stdout)、[stderr](cancel-followup/pytest.stderr)、[跨冻结桥](cancel-followup/cross-freeze-bridge.json)、[补强测试](cancel-followup/frozen-source/tests/test_production_trial_policy.py)、[取消后的 attempted/usage 回执](cancel-followup/actual-tmp/test_cancel_after_reservation_0/cancel-after-reservation.json)。
- 输入与辅助脚本无漂移：[首轮 before](first-run/inputs-before.json)、[after](first-run/inputs-after.json)、[helpers before](first-run/helpers-before.json)、[after](first-run/helpers-after.json)；[补强 before](cancel-followup/inputs-before.json)、[after](cancel-followup/inputs-after.json)、[helpers before](cancel-followup/helpers-before.json)、[after](cancel-followup/helpers-after.json)。各轮 701 个输入，含 135 个生产输入。
- 离线 guard：[首轮实现](first-run/offline_policy_guard.py)及[记录](first-run/offline-guard.json)，[补强记录](cancel-followup/offline-guard.json)。HTTPTransport、Settings.from_env、InternModel 请求哨兵 attempts=[]；没有模型、Worker.once 或 provider 请求。
- 只读性：[首轮闭合](first-run/closure.json)、[补强闭合](cancel-followup/closure.json)。46 + 5 个操作窗口，各比较全 55 表严格行相等，保存 2805 对逐表指纹；fixture 创建与模拟 SQL 修改在窗口之外。原件只导出行数/指纹及断言，未导出全行；没有凭指纹冒称独立重建数据库。
- 典型回执：[不可执行 transition](first-run/actual-tmp/test_positive_policy_transitio0/non-executable-policy-transition.json)、[身份拒绝](first-run/actual-tmp/test_exact_contract_account_qu0/identity-refusals.json)、[UNKNOWN 不退款/不重发](first-run/actual-tmp/test_unknown_and_missing_usage0/unknown-nonrefundable-no-resend.json)。
- 静态检查：[首轮 Ruff](first-run/ruff-freeze.txt)、[补强 Ruff](cancel-followup/ruff.txt)。

## 有限独审及完整性

[最终结论](review/final-review.md)与[结构化结果](review/final-verification.json)有限通过，当前无确定 P1/P2。先审[设计](review/design-review.md)，保留 [WIP P2](review/implementation-review-draft.md)及[修正核对](review/implementation-review-fix.md)。恢复 prefix/相邻 RPM 问题在冻结前修复；撤权精确码与负例隔离也在冻结前修正，没有运行修前源码并倒签资格。

独审只执行纯文件/Git 核验；[首轮 audit](review/audit-first-qualification.py)及[stdout](review/audit-first-qualification.stdout)、[补强 audit](review/audit-followup-qualification.py)及[stdout](review/audit-followup-qualification.stdout)均一次 exit0。20 个物理 fixture DB 仅 stat，没有打开、SQL 或重算内容，没有额外产品/pytest/网络执行。独审未背书之后的推送。

[selection.json](selection.json)逐项列出 75 个逐字复制路径、1372355 bytes、原绝对路径及 SHA；不含本 README、[raw-selection.json](raw-selection.json)和 selection 自身。首轮 37 路径、补强 20 路径、独审 18 路径，均包括各自 manifest；复制数据库数为 0。

| 原封存清单 | SHA256 |
| --- | --- |
| [首轮](first-run/sealed-manifest.json) | `92928b53e06c1b4fc12c0b8cdb584f314a1b4cbaa587a73643dfc6460c91fe79` |
| [补强](cancel-followup/sealed-manifest.json) | `f73291ab1749d7e98d90ec08f93bdf4745010e35a48636ad84330ef2ead803c8` |
| [独审](review/sealed-manifest.json) | `56763603e193ff73a51e9ff5230667d9c34b4a9bef21459d3c3437bf3279d374` |

归档时首个复制 helper 将独审 manifest 的 list 误作 dict，在复制之前报 AttributeError；修正解析后一次完成 SHA/size 核对。失败脚本、工具输出转录元数据及修正命令 stdout/stderr 保存在外部 `/workspace/production-policy-kernel-final-delivery-20261018`；首次 stderr 未单独捕获，不冒称原始 stderr。这是证据打包失败，不是产品或测试失败，未为此重跑测试，也未修改任何封存目录。

## 未覆盖和执行依赖

内核没有 durable controller、数据库 CAS/全局并发 RPM 或真实来源 producer；调用者未来须原子持久化可信 ledger+cursor 并重核当前权限，不能接受 HTTP caller 任选旧状态。JSON roundtrip 仅证明序列化。内部 accepted 不等于业务、人工验收或免费授权。

真实模型/账户/费用/人工语义、完整 UI/P-A/P-B 链、Windows/native、PostgreSQL、远端 CI 均未执行；旧永久取消窗口和恢复矩阵未重开。实际执行仍需合法真实来源、精确软件资格、持久 controller 与受审 sender。没有新增 issuer/source selector、有效 LIVE Permit、Grant、executor、凭据或付费请求。当前合同仍绑定旧 endpoint/model；其他合法渠道须新合同与独审，不能拼接官方截图或把 30 秒工程阈值当 provider 续签要求。旧满盘未落盘独审仍未补回。
