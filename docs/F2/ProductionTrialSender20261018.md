# 未安装 sender：原 adapter、持久 capture 与结算

2026-10-18，从父级已有限独审的 `94fa765de11e1e3cc42dac9070a28ec9c2b47647` 接续；普通开发分支 `dev/production-trial-sender-20261018`。源码及测试冻结在 `c6f946d4d5c90652dbc6ad9945499dc529cc8e4d`，此后的交付提交只补文档和原始证据。原 journal 的12节点及更早内核19节点未重跑，不列为本片新资格。

本片实际完成此前缺少的 marker→现 InternModel adapter→收到的 bytes→持久 capture/journal 接线。它仍是未安装的离线控制器：不注册到 API、Worker.once、source producer、sender selector 或 LIVE issuer，不新增 executor、Grant、表、凭据或权限。旧 production_preflight/resolve_account 默认拒绝保持。构造内部 SourceVerificationResult(ALLOW) 不是真实来源事实，journal receipt 也不是发送许可。

## 原路径的最小接线

`dispatch_offline` 在预留前及实际 wire guard 核 exact Worker/Settings/Store、test_only SQLite、原 mock/live=false/token空配置及 exact httpx.MockTransport；冻结原 Store/engine、Settings、transport、Worker 身份，不向迟到的替换 Store 写事实。原 wire 保持逐字，strict_json 只核既有五字段、intern-s2、非流式和原输出上限。

原 journal.reserve 提交槽，record_attempt 提交不可逆 may-have-sent marker。任何原完整 key 重入均只读历史，未标记的 pending 也不自动续发；新 Worker 只能看原身份历史。现 configured_provider 用既有固定 synthetic 占位和 MockTransport 构造 InternModel，内部 adapter 会使用其原合成 token/live 设置；普通 Worker.s 仍为 mock/live=false/token空。这不是有效 LIVE，也没有读取真实凭据或 Settings.from_env。

原 request_serialized_captured 的 wire guard 再核精确 POST/endpoint/body、原槽、当前 Run/批准/版本/lease/fence/权限和合成来源绑定，只返回本次 adapter 的有限 deadline。没有可缓存的发送许可。

实际接收 bytes 由原 strict_json、normalize_usage、returned_model_identity、parse_response 和 response_archive 重新派生，不采用 caller 的 parsed/tokens/hash。raw SHA/bytes 与 canonical ASCII SHA/bytes 分开保存；只对完整、有限、原 model 且符合通用协议的响应记 RECEIVED，其余记 UNKNOWN，同时保留已知 usage 分量和缺失 null。通用协议通过不等于业务或人工验收。

私有 `uninstalled-production-trial-capture.v1` 双镜像绑定完整 reservation；非空原体至多32768 bytes以base64保存，空体或超限明确 omission，原始 bounded body上限131072。公共 receipt 只有指纹、计数和 verdict，没有正文、header 或 token，恒 business_accepted/live/dispatch/real-source=false。现 adapter 对429/非200等可能只保空体或前缀，不能声称收齐错误正文。

可信 owned journal 标量锚、原身份/wire及当前 Run owner/project/runtime标量先于私有 body 读取。新 capture 两镜像和原 journal/cursor 四镜像在同一事务提交；CAS失败六行全部回滚到已提交 marker。旧已结算但缺capture时拒绝补证明；跨链 settlement、EMPTY及原body派生必须一致。原 journal 只抽私有 `_history_anchor` 和 `_apply_in_transaction`：原校验表达式及事务体 AST 保持，校验移入事务并增加事务断言；公有签名保持。

## 不可消除窗口与新资格

marker提交后、guard前实际取消，handler为0，原槽/marker仍保留并UNKNOWN/halt。guard结束与transport IO不能由数据库事务原子封锁；guard后取消的用例如实观察到一次合成handler，已知响应/usage仍保存，accepted=false/halt。没有声称取消能撤回已可能开始的发送。

两个真实发送进程分别在marker后adapter前和合成响应收到后归档前故意退出17/23；各由另一个全新恢复进程退出0。恢复只读原marked/pending，adapter/handler增量0，全55表前后严格相同。缺capture不证明未发送或费用0，UNKNOWN不自动重发、退款或补KNOWN。

冻结测试一次执行8唯一节点/8次/8PASS，JUnit41.715秒、外层46.022090623秒：正常原adapter/原wire/六镜像提交及重复、入口门、两个实际取消窗口、接收前缀后超时、capture后quota CAS失败、两个真实退出/恢复节点。EMPTY负例同时重算capture及journal的同一错误SHA与seal，保持跨链一致，独立验证空体派生拒绝。正常及EMPTY测试最后故意破坏新pair用于负例，不声称最终fixture全部有效。

705个输入/137生产及辅助脚本前后零漂移。原703个输入中只有journal提取改变；其余702输入/135生产逐字同基线。实际原Intern adapter调用6次、Mock handler5次、真实provider/model0；四个真实子进程含两次故意退出和两次恢复。父进程guard覆盖socket/HTTP/env，子进程覆盖HTTP/env/实际Intern方法，没有安装子进程socket哨兵。旧19/12矩阵未重跑，也不将其历史通过签到本次变更后的journal。

事前设计v1/v2/v3、四项静态P2发现及冻结前修复、格式/工具失败与实际执行原件分别保存；未动态运行有缺陷的WIP。独审只核冻结Git/AST/字节及现有原件，不另跑产品、网络或打开DB。[原件、有限独审和复制完整性](../evidence/production-trial-sender-20261018/README.md)。

真实来源producer、可信source事实与LIVE sender安装仍待后续独立实施/审查；完整生成/source/cold/UI链、真实账户/费用/模型/语义、PostgreSQL、Windows/native及远端CI均未执行。本片没有回跑旧恢复矩阵、补签旧取消窗口或补回旧满盘未落盘报告。双镜像不是密码签章，不能抵抗管理员整体改写可信DB；本片不据此签收整体F2或生产LIVE。
