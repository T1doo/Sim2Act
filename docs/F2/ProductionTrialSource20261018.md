# 未安装账户来源：服务端 loader 与原始证据验证合同

2026-10-18，父级有限接受基线 `9df8a2ecca3e2e9905200398aa7c7a4d53b891a0` 后接续；root唯一仓库writer。新普通分支 `dev/production-trial-source-20261018`，源码/测试冻结 `ab838215af13c04281bbad441fd75b9a97839890`。新增source模块及九节点测试，旧生产只改sender固定接线；原policy/journal、production_preflight/resolve_account及所有API/Worker入口保持。

本片实现真正的服务端fixture读取、四角色原始证据派生与现journal/sender调用链，不是实际provider来源producer。当前未给定受信官方账户/费用来源接口，只冻结验证合同。所有结果恒UNINSTALLED、real_source_verified/live/dispatch=false；内部SourceVerificationResult(ALLOW)只表示合成数据合同成立，不证明真实免费，也不是Permit。

## 谁提供什么

| 原始证据角色 | 必须显式提供的事实 | 未来真实提供方，尚未注册 |
| --- | --- | --- |
| identity | 同一opaque账户及原provider/model/endpoint的身份确认 | 受审账户身份管理来源 |
| entitlement | 该账户当前合法免费权益 | 可核查条款及账户权益来源 |
| enforcement | 强制零收费、精确paid_cap=0、禁止收费fallback | 实际可执行的收费控制方 |
| status | 当前撤销状态、观察时间与有效期限 | 可核查当前状态来源 |

同一受审正式来源可以提供多个角色；未要求provider发明签章或30秒续签接口。当前四角色全部只由明确synthetic fixture提供，issuer固定为SIM2ACT_SYNTHETIC_FIXTURE_ONLY。公开定价、额度上限、paid_cap0、caller ALLOW、hash或双镜像均不能替代上述真实事实。

四角色各自绑定完整requirements指纹、账户、channel及observed_at/expires_at；严格schema、有限8192B原始JSON，缺失/未知事实为UNKNOWN，显式拒绝、撤销、过期或错绑定为DENY，均不可发送。零费用控制中的未知保留null。结果观察时间取四角色最晚、期限取最早且不超过原合同；600秒前观察但仍有效可通过合成合同，不移植旧候选诊断的30秒工程上限。

## 服务端固定接线

`production_trial_source.load_offline`只接受exact Store、test_only SQLite及原caller同一Connection/engine/活动事务。先核原user/contract、owned项目/runtime和canonical account，读取自有source的标量requestFP锚，再读该原trial的双镜像与有限base64原bytes。strict_json后解析四角色，再从实际bytes派生指纹；没有来源URL、原始证据、source/ALLOW对象或任意callback的HTTP输入。

独立namespace `uninstalled-production-trial-source.v1`复用delivery_graph_requests；产品没有writer/新表/DDL/Grant/权限。测试显式写固定fixture。两镜像和issuer仅验证合成格式/存储完整性，不是来源信任根，不防管理员同时重写可信行。缺源、格式未知或损坏为UNKNOWN；只有pair数据VERSION_CONFLICT转UNKNOWN，真正权限/DB/CAS异常传播。缺原件时内部evidence_fingerprint零值是不可用哨兵，raw_sha256为null，绝不当成已读来源证明。公开Resolution无原body/header/token。

新增 `dispatch_from_source_offline` 不收source/selector/callback。原sender主体抽私有共享函数，原 `dispatch_offline` 数据路径保留；原key先核owner/scope/完整identity并只读历史，源缺失/撤销也不重发，历史无需重新读取来源。新交换的reserve、mark、wire guard及settlement各在原事务连接重读固定loader，随后复用原journal/policy；不另造executor、发行者或发送器。

UNKNOWN/DENY使新预留事务回滚，持久预算零污染。guard后来源撤销仍可能已发一次，接收端先通过原owned slot/Run门，再读当前来源；已收body/known usage保留，原settle拒接受并halt，不退款、不补零、不重发。真正身份或DB错误不会被普通UNKNOWN吞掉。SQLite BEGIN IMMEDIATE只支持本片离线重读线性化，不据此声称PG锁顺序或外部IO原子。

## 首轮资格与修正

九唯一节点一次九PASS/零FAIL、ERROR、SKIP；JUnit38.319秒，外层43.323537305秒。707输入/138生产及runner/guard前后零漂移；旧705输入只有sender改变，其余704输入/136生产逐字不变。旧19/12/8矩阵未重跑、不累加。

正常实际raw→四次同原c来源读取→原journal/sender/InternModel→MockTransport→capture结算；六类来源拒绝（缺失、错账户、跨项目、过期、撤销、角色不一致）均全55表严格相同/handler0；另在同一不一致节点独立损坏一侧fingerprint，保持两requestFP锚，直接验证pair VERSION_CONFLICT→UNKNOWN及不修复。跨项目SQL观测先做正向校准，缺自有锚时不读外国payload，复制外国raw到本项目也拒绝。

正常节点还核四角色未知、禁止收费fallback、foreign issuer、伪造ALLOW及PRODUCTION标签不会升级为可用真实来源。正常原key在删除source后完全不调用loader、全55表不变；在途source撤销保存usage8但拒接受，重复也不发。边界节点确认生产默认拒绝及权限异常传播，并实际执行一次抽取后的旧数据入口作小兼容检查，未重跑旧八节点窗口矩阵。

共三次原Intern adapter/三次Mock handler：新source入口两次、旧数据入口兼容一次；真实provider/model0，没有新的子进程crash演练或Worker.once业务执行。父guard覆盖真实HTTP、socket、Settings.from_env及精确Intern方法，实际九条嵌套方法记录对应三次请求。九物理fixtureDB只在外部保留；作者记hash，独审仅stat，不复制DB。

事前静审发现原key历史将三项返回值解成四项的P1，首跑前已修；记录如实区分原工具行转录与已修片段，没有声称保存了未修整文件字节。首轮格式错误和一次patch上下文拒绝均在首跑前修正，原件/转录保留。正常节点最终故意删除source，不一致节点最终保留损坏的source指纹，不声称所有最终fixture有效。[原始资格、设计与有限独审](../evidence/production-trial-source-20261018/README.md)。

## 下一项与安装边界

V5 F2-T02/T03、AT09/10仍要求完整生成、已成功任务来源及新资料冷运行。这种业务source不同于本片账户费用source。当前 `_generation_accounted`、`_pb_origin`及`natural_source_archives._source_prefix`仍读旧synthetic预算和实际Attempt，新journal/capture尚未进入完整3+2+2阶段证明。该证据与业务提交桥可继续离线编写，复用现控制器、原审批/材料/Goal/版本/lease/fence与raw/canonical分别几何，不复制旧预算造第二份事实，不能凭单次通用协议通过声称已完成。

真实来源producer、收费控制事实、实际批准及受审安装仍是未来LIVE的独立条件。生产preflight/resolve_account继续默认拒绝；本片不安装source/issuer/sender、不选择真实凭据、不发送真实请求。完整阶段/UI、真实账户/费用/语义、PG、Windows/native和远端CI均未验。旧取消窗口不重开，旧满盘未落盘报告不补签，整体F2与生产LIVE不由本片验收。
