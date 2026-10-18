# 服务端账户来源 loader/verifier 设计独审

结论：设计v1与随后父级实现收敛可继续。当前没有确定设计P1/P2，也没有因缺真实账户而阻碍离线合同与接线编码的依赖。当前HEAD核为 `9df8a2ecca3e2e9905200398aa7c7a4d53b891a0`，首次检查工作区clean；本报告不代表实现或资格通过。

本片确实补现有 sender 直接接受内部 SourceVerificationResult 的边界：新入口不收source对象，固定从owned服务端raw四角色读取并重新派生；它不是另一个可自选registry/ALLOW包装。既有 production_evidence.resolve_account 仍NoReturn，production_preflight 仍先原批准再缺源拒绝；旧policy、journal public接口和手工合成路径不应放宽。固定test_only SQLite元数据是测试来源，绝非官方权益producer。

原V5阶段计划94–95行F2-T02/T03及111行要求真实P-A/P-B与新资料冷会话；本片不关闭这些整链门。产品设计249–253行区分真实托管调用与离线工程样例，331–343行要求发前预算、完整响应和未知用量不填零；本片原key不重发、迟到usage保留及无免费事实宣称与这些条文一致。没有provider协议时冻结角色合同而不伪造producer，是范围内可交付软件。

## 实现时必须保持的边界

1. exact Store、SQLite/test_only、同caller活动事务且connection.engine为原store；原contract/user/project/runtime、canonical account和独立scalar requestFP锚通过后才能读private pair。四角色各自完整重复绑定，严格extra/duplicate-key/bounds/base64/raw SHA验证。identity须有显式确认事实；entitlement、强制paid_cap=0且禁止收费fallback、当前revocation都须明确。未知不得推true，boolean/issuer/hash/seal不得升格生产权威。
2. 完整原key重复只按原owner/scope/wire/identity返回既有历史；当前源缺失、撤销或过期不产生续发、回填或退款。尤其新入口不能在历史shortcut前因loader来源失效硬抛而破坏原历史语义；不同worker仍只能原历史。
3. source的缺失/不支持/损坏及明确否定返回严格typed UNKNOWN/DENY；真正owner、Store、DB、CAS异常不得通过宽泛catch伪装来源未知。新mutation最终仍由原policy fresh拒绝。接收事务先原owned slot/Run标量门，再重读当前source；UNKNOWN/DENY交原settle保body/known usage/marker但拒accepted并halt，不能因来源失效把已接收事实丢掉。
4. reserve/record_attempt各在原同一c里load后调用原_apply_in_transaction；guard同TX重读；receive同TX重读并capture+四镜像结算。禁止新开事务读source或把首次快照缓存到IO后。固定内部模块调用，无callback/selector输入。当前Store.tx在SQLite使用BEGIN IMMEDIATE，本片在此串行边界验证；_load含FOR UPDATE，若源pair被放在不同读取位置，不据此签收未来PG锁序或来源writer并发。
5. 保留captured Store/engine/settings/transport/worker与exact MockTransport再次guard；新source模式不能引回已修mutable worker.store问题。来源撤销在guard后仍可能已有一次IO，只保late事实并拒接受，不能声称DB可撤回已开始发送。

父级补充的收敛已逐项接受以上三处主要风险：源失效与权限异常分类、原key只读历史、每原事务内固定loader重读。9节点可按原拟定范围覆盖，无需重跑旧19/12/8矩阵；合成marker后status撤销是新来源接线资格，必须与旧取消窗口区分。正常600秒前观察但未过期可用，不能移植旧candidate诊断的30秒工程限制。

## 范围

仅静态读设计/Git/源码，没有产品、pytest/collect、SQL、数据库、HTTP/网络、Worker或模型执行，无仓库写入。本目录为全新未seal独审目录，后续实现与实际原件需另行有限复核。旧sealed目录全部保持不写。真实来源、LIVE许可/安装、真实费用语义、完整generation/source/cold链、PG、Windows/native和CI均未验。
