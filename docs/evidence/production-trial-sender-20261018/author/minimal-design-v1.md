# 已接收响应到持久journal的原子归档与结算桥：最小设计v1

基线94fa765de11e1e3cc42dac9070a28ec9c2b47647；源码冻结12958af924fad425fa619adccd1841fb8f8228a8。本地远端一致、clean、约23GB，root唯一仓库写入者；父级独审94fa进行中，本设计不开始产品代码写入。旧19/12节点执行范围原样保留，不重跑或刷分母。source/cold完整链、PG/Windows/CI/真实费用仍未验。

## 实际缺口与下一片

生产policy.Outcome当前允许调用方分别填response_sha256、response_ascii_bytes和tokens；journal.settle将其持久化，但没有从同一原接收字节派生，也没有原始body+该结算同事务的证明。已交付journal是reservation身份，不是实际生产Attempt；仍不升级该陈述。

现InternModel.request_serialized_captured已返回CapturedResponse(body,parsed)，错误路径附bounded _received_body/_received_body_complete。旧pa_trial_dispatch及natural_source_archives已把MockTransport捕获接原synthetic账本，且确切绑定MOCK/test_only。本片不重复这个sender、不松它们的门或标签，而把已接收body事实接入新的未安装durable journal。真实source/费用producer的事实不能捏造，但这项离线接线可立即编写，不必等真实账户。

新增独立production_trial_capture模块；journal仅提取私有同事务_apply_in_transaction，原public方法仍自行Store.tx并委托同一逻辑。无新executor/Grant/表/DDL/权限、API/Worker/importer/source/sender注册、可消费LIVE Permit、凭据或真实IO。旧resolver仍默认拒绝；新receipt恒UNINSTALLED/live=false/dispatch=false/real-source=false。

## 内部输入合同

仅Store、原user/完整contract/approval key、完整ReservationIdentity、原wire bytes、内部合成SourceVerificationResult、expected_revision和精确不可变CapturedBody数据：body bytes（最多现adapter131072）、body_complete bool、http_status int|None、transport outcome有限枚举。明确合成离线provenance。不得传callback/transport/provider selector/凭据、ledger/cursor、caller usage/hash/模型通过bool。构造数据不证明真实provider来源。

永远忽略外来parsed对象，从body bytes复用strict_json、normalize_usage、returned_model_identity及原response_archive几何规则派生Outcome和归档metadata。保留原body SHA/byte count，与canonical ASCII SHA/byte count分开；只有完整200、合法返回model、完整known usage且原上界满足才可进入当前policy接受检查。HTTP拒绝、partial/未知、坏JSON、错model等不取得接受权限；可以从完整可解析接收片段保留实际已知usage分量，缺失保null，绝不填0或退款。本片复用已有解析规则，不扩一般错误矩阵。

body归档写已有delivery_graph_requests的新uninstalled capture namespace双镜像，request绑定完整原reservation身份/原wire及journal scope；response含raw字节的base64（仅0<raw<=32768，超限/空只保bounded digest+omission）、complete/extent/status、canonical metadata及派生Outcome。没有provider header/密钥，没有公共事件正文。只保存接收到的bounded body事实，不冒HTTP包或真实生产Attempt来源。

## 事务与历史

按原project→account→ledger→原Run锁序，在读取private body之前核自有scope/完整原identity/wire；核实际Run的principal/project/runtime标量仍绑定，但允许cancel/version/fence/lease已失效后的事实入账。原槽必须已marker，不能用一段body回填未标记slot。controller持有锁后归档双镜像，再同一事务调用原journal结算；revision不符/任何CAS/半镜像失败整TX回滚，body和ledger/cursor一起提交。

原结算已存在而capture不存在时拒绝回填旧证明。新capture必须对应当前未结算原marker；既有capture仅完整原body/complete/status/Outcome一致才返回原历史，duplicate=true/changed=false，不改revision、不改body、不marker、不授send。改body或身份拒绝；无新capture→新Attempt/retry/UNKNOWN转KNOWN通道。

迟到正确body在取消/撤权/expiry后仍可保留接收事实与usage，原policy只降accepted=false/halt。UNKNOWN保持原槽/账户时间与null，不自动重发。该桥不声称外部provider与DB原子，也不把marker等同实际发送。

## 建议最小验收（最多6个新定向节点）

1. 完整合成body→从同一bytes派生raw/canonical/usage→归档与journal同commit；原完全重复只读、同Attempt换body拒绝。归档始终非LIVE。
2. 原槽缺marker不得写capture或结算；错scope/wire在private body读前拒绝，零污染（只新边界，不重跑旧身份矩阵）。
3. marker后实际cancel，再接收完整known body：raw归档/usage保存，accepted=false/halt，保原槽与quota。只新capture时序，不重跑六个旧取消/fence/lease序。
4. partial/UNKNOWN body的已知prompt与缺失null均从原字节派生；新进程只读原归档/原key历史，零重发、不退款，不回填KNOWN。
5. 两独立连接同时提交完全同capture，一次归档及结算，另一只读历史；不新增通用并发故障矩阵。
6. 归档已写后制造原journal CAS旧指纹冲突，实际6行同事务全回滚；零孤立body/半更新账本。

合成body、固定内部source，HTTP/Settings.from_env/InternModel请求哨兵全禁；实际pytest命令、JUnit/stdout/stderr、inputs/helper before-after、源码冻结、archive/ledger指纹/revision与权限表不变原件保留。没有真实模型、账户、费用、Windows/PG/远端CI或业务语义签收。真实sender可继续另片离线编写接线；本片完成的是接收端到durable账本的实际行为，不是假装该sender已实现。

待父级94fa独审反馈及本最小设计核对后，正常新dev分支实施、有限独审、推送；本片没有必须先取得真实账户的编码阻塞。
