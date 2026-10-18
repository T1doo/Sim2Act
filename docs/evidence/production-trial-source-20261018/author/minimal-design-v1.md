# 未安装的服务端账户来源 loader/verifier（设计v1）

基线9df8a2ecca3e2e9905200398aa7c7a4d53b891a0已由父级有限接受。root仍唯一仓库writer，旧reviewers均completed；本地/远端HEAD一致clean，main6f688不变，余23GB。新普通分支dev/production-trial-source-20261018。此设计冻结后先独审再实施；不重复旧19/12/8矩阵或旧取消窗口。

## 原方案位置与真实缺口

V5 F2-T02/T03与AT09/10仍要求生成、成功任务来源和新资料冷运行。现新policy/journal/sender只完成隔离单次交换；natural_live_admission._generation_accounted/_pb_origin及natural_source_archives._source_prefix仍读旧synthetic预算/实际Attempt，不能以新journal单次通过声称完整generate3/source2/cold2链已接通。完整阶段证据桥是后续可离线编码项，本片按父级明确优先补另一项“账户费用source”验证合同，两种source不混称。

production_evidence.resolve_account仍NoReturn默认拒绝；production_preflight不改、不安装新loader。当前没有给定可受信官方账户/免费权益/强制零收费来源协议，不能伪造provider接口或声称已有真实producer。本片只实现未安装的服务端读取及原始证据数据验证合同，唯一可运行来源是明确test_only SQLite的固定synthetic fixture。原始资料角色及其生产信任根必须未来另审；所有对象恒UNINSTALLED、real_source_verified/live/dispatch=false。

## 谁提供什么，以及什么不构成事实

原始bundle包含四个有类型、有限、必须齐全的证据角色，均有固定角色标识、固定synthetic issuer、原requirements指纹、同account/provider/model/endpoint和observed_at/expires_at：

1. identity：明确账户身份确认，不接受从quota label反推身份事实。
2. entitlement：明确该账户当前合法免费权益；未知不推断为true。
3. enforcement：明确强制零收费、paid_cap精确0、禁止收费fallback；免费额度/公开定价/上限截图不等于此事实。
4. status：明确当前撤销状态及有效期；缺失/未知拒绝，期限不延长原合同。

这些在本片均由测试固定fixture提供，绝非已核provider事实。生产时分别需要账户身份管理方、权益条款/账户权益来源、可执行收费控制方及当前状态来源的受审读通道和可信原件，允许同一正式来源提供多个角色，但不能由调用者布尔值、ALLOW、hash、双镜像或自述issuer替代。没有官方格式时只冻结角色/验证合同，不实现假真实producer，不要求provider发明签章或30秒续签接口。

raw bundle使用strict_json与冻结schema，有限base64原始bytes存于独立uninstalled-production-trial-source.v1元数据namespace；严格extra=forbid，无URL/transport/凭据/callback/ALLOW输入。四角色各自重复绑定，必须全部一致；从实际raw bytes重派生结果与SHA，忽略caller摘要。固定synthetic issuer只能在test_only SQLite下用，不是可选registry，不能给生产trusted标签。

没有生产writer/HTTP route：fixture测试直接在既有delivery_graph_requests写两镜像，产品只读。镜像与requestFP只验证存储完整性和scope，不证明出处，更不能抵抗管理员同时重写全部行。没有新表/DDL/Grant/权限或真实凭据。读取前核精确Store、SQLite/test_only、原contract/user/requirements、owner项目/runtime及canonical account，先核自有标量锚，再读该原trial的body，不扫描别项目/账户payload。调用者不提供原始证据、来源结果、任意来源key/selector或callback给新发送入口。

## Loader结果与失败语义

新production_trial_source模块按固定owner/project/trial/requirements/account从服务端读取，验证raw四角色、scope、当前时间及完整显式事实，输出Resolution及既有SourceVerificationResult数据：有效合成合同才能ALLOW；显式撤销/false或错误绑定/过期为DENY；缺源、未知事实、损坏/不支持格式为UNKNOWN（均不可发送）。observed_at取各角色最晚观察，expires_at取最早期限且不超过原合同；没有30秒provider规则。evidence_fingerprint仅对应已读原bytes，不被当成费用权威。公开Resolution无raw/body/header/token。

结果是当前读取快照，不是可缓存Permit。新sender入口dispatch_from_source_offline不接受source对象；固定调用该loader，再复用现单次sender核心。旧dispatch_offline签名和手工synthetic数据路径保留，不改生产默认resolver。为避免另造executor，只把原sender主体抽私有共享函数；新的固定source模式无可执行callback参数。

在reserve与record_attempt各自原事务内读取来源并调用原journal._apply_in_transaction；guard同一事务再读当前来源后调用原policy._fresh；接收事务在原owned slot/Run标量检查后再读来源。原keyduplicate仍只读历史，即使来源现缺失/撤销也不重发，不因loader失败修复/回填来源。前置UNKNOWN/DENY经原policy拒绝，整事务零预算污染。接收后来源失效则以当前DENY/UNKNOWN交原settle：保原body/known usage和marker，accepted=false/halt，不丢已发事实、不退款、不重发。真正owner/DB/CAS边界拒绝仍原样，不能用捕获异常绕过权限。

只固定新模块函数调用，所有IO/Store/settings/worker绑定仍由原sender exact guard约束，不传任意loader/callback。收发均只exact MockTransport，configured_provider已有synthetic内部占位不是真实凭据。生产source/issuer/sender注册、生产Attempt及业务阶段链本片均不安装。

## 最小新资格（拟9唯一节点，不叠加旧矩阵）

1. 正常服务端四角色raw→loader→原journal/sender→原capture结算，真实InternModel到MockTransport一次；原key重复不发。保600秒前观察但仍有效，证明不移植30秒假规则；原始SHA独立核，公开对象无raw，real/live/dispatch恒false。
2—7. 六个必要来源拒绝：缺源、错账号、跨项目绑定、过期、撤销、四角色不一致。经新发送入口，均预算/其他表零污染、handler0；错误镜像可在不一致节点内另核，不能通过重算seal制造来源事实。
8. 原marker后的actual Mock handler撤销服务端status：guard时可发一次，接收重新读当前撤销，body/usage保留但accepted=false/halt；duplicate只历史，不增加handler。这是新来源状态接线资格，不重复旧取消故障矩阵。
9. 非fixture Store/外部transport/LIVE入口门及真实resolver依然默认拒绝，零实际provider/env/凭据读取。UNKNOWN事实/foreign issuer/伪造ALLOW放在来源合同节点有界数据变体，不增加相邻状态矩阵。

全部只新离线合成数据与guard：实际adapter次数与Mock handler次数分开，真实网络/model0。冻结原始命令/JUnit/streams、输入/helpers beforeafter、必要表窗口及来源判定；源码静审后才首跑，修正与失败如实保留。Windows/native/PG/远端CI/真实来源费用语义及完整阶段链不补签。父级独审同意本最小合同后继续实现、有限独审及正常新dev推送，不等真实账户才写离线代码。
