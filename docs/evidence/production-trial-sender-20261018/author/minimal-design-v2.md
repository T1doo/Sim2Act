# 未安装sender控制器：原marker、InternModel捕获及durable结算（设计v2）

父级已有限独审通过94fa765de11e1e3cc42dac9070a28ec9c2b47647，无确定P1/P2；其12节点仅SQLite争抢与两新进程只读，不是崩溃发送恢复。root仍唯一仓库writer，HEAD/remote一致clean约23GB。v1的响应→journal原子桥保留为本片接收半段；v2按父级明确要求补同一sender调用的marker→send窗口。v1不覆盖、不回写，设计hash各保留。

## 最小原计划功能与默认拒绝

新增未安装production_trial_sender控制器，复用现有Worker身份、InternModel.request_serialized_captured、现configured_provider的隔离synthetic adapter、原strict_json/normalize_usage/model identity与原journal。只有明确test_only SQLite + Worker.s.mode=mock/live_enabled=false/token空 + exact MockTransport绑定可以实际运行离线演练；外部transport、生产store或LIVE配置在预留前拒绝。Worker.once、API、HTTP source/issuer/sender selector均不注册。旧production_preflight/resolve_account默认拒绝、旧synthetic Permit/账本/归档标签不改，不加executor、Grant、表/DDL/权限或真实凭据。

现configured_provider仅在原worker设置保持mock/live=false时，用其已有固定synthetic占位及确切MockTransport构造InternModel；不加载Settings.from_env、不配置token/env/文件、不连接真实网络或模型。该占位不是真实凭据，内部adapter设置不等于有效LIVE安装。普通生产入口仍不可执行；构造SourceVerificationResult(ALLOW)不是来源事实或发送许可。

## 输入与状态

dispatch_offline只收现Worker、原完整contract/approval key、完整ReservationIdentity、原wire bytes、内部合成SourceVerificationResult和expected_revision。无新caller ledger/cursor、FeeAuthority/Permit、credential、URL/model选择或可执行回调参数。Worker已有的MockTransport仅受信离线fixture提供，handler由测试固定，不接HTTP caller。所有返回恒UNINSTALLED/live=false/dispatch=false/real-source=false；返回journal receipt不被用作send许可。

1 原journal.reserve提交原槽；原完整key重复立即只读返回，连原marker未写的pending也不自动续发。
2 原journal.record_attempt在当前上下文核验后提交不可逆marker。再次进入coordinator只能读历史，不把duplicate marker当send许可。
3 现InternModel wire_guard中，在新事务加载可信ledger/account，核原identity/wire、唯一已marker且未settled原槽、真实当前Run/批准/phase/Grant/worker/版本/fence/lease、同source binding，再返回有限deadline给同一个固定MockTransport请求。精确POST/endpoint/body检查保持，未建立可缓存LIVE Permit。
4 对实际返回CapturedResponse或DomainError保留的bounded body，从原bytes重新解析（忽略parsed对象/caller tokens/hash），派生raw SHA/bytes、canonical ASCII几何、returned-model及known/partial/null usage。未知/拒绝/坏体或错model不获得接受；费用事实保留、不补零。新namespace私有capture双镜像绑定完整原reservation，保存bounded原body的base64或oversize/empty omission，绝不公共事件输出正文/headers/token。
5 journal仅抽私有同事务_apply_in_transaction，原public wrappers接口不变。owner/scope/wire/marker及Run身份标量先核，capture双镜像后同事务原journal.settle四镜像CAS；冲突六行全部rollback。迟到取消/过期/撤权仍保已接收body/usage，accepted=false/halt。旧已settled却缺capture不回填证明。完全同capture重复仅原历史，不改body/版本/marker；不能UNKNOWN转KNOWN或造新Attempt。

## marker→send窗口的精确语义

marker commit后、wire_guard前取消：实际guard拒绝，MockTransport handler=0；原槽/marker保留，UNKNOWN/halt，不退款或重新发。guard事务结束与外部IO之间不能由DB保证原子；取消在guard之后到达时，允许观察到一次合成handler调用，随后收到body也只保事实、拒接受。明确报告该窗口，不声称取消能撤销已经可能开始的发送。

进程在marker后、adapter进入前退出，或合成handler已返回body但归档前退出：新进程从原key只读原marked/pending历史，不重新调用adapter，不推定未发送/费用0，不退款。因为没提交received事实，不凭缺失archive发起重试或回填known。与旧12只读重开不同，这是本sender两个实际退出窗口的新资格。

## 最小验收（拟7节点，最多8，不扩旧矩阵）

A 正常合成200在现InternModel+exact MockTransport实际一次，原wire逐字核对；body派生usage/双归档与journal同commit；完全原key重复零handler、改body/Outcome不替历史。公开receipt不带正文。
B 非fixture生产store/非Mock或LIVE设置/自造来源对象的边界拒绝，预留前零写零handler；只新入口必要门，不重跑旧19身份矩阵。
C marker提交到guard前实际cancel，零handler，原槽不退且UNKNOWN/halt。
D guard后/合成handler入口控制cancel，记录可能已发一次；known body保留但拒接受。不是防止该窗口的宣称，不重跑六种旧lease/fence并发。
E/F 两个真实子进程分别marker后adapter前、实际合成接收后归档前退出；父级新进程再dispatch原key，只读原marked/pending，handler不增加/不refund。故意退出码与测试PASS分开留证。
G capture已写后的原journal CAS冲突，全TX六行rollback，零孤立archive；同原key恢复仍未知/不send。
如需要第8节点，仅限partial/UNKNOWN body从bytes派生已知prompt及缺失null，不扩response错误矩阵。原19/12节点不重跑或加进分母；source/cold完整链、PG/Windows/CI/真实来源账户费用语义均保留未验。

run级guard阻止真实HTTPTransport与Settings.from_env；InternModel方法只容许确切当前fixture provider+MockTransport，记录adapter次数与真实网络0，不能把“InternModel方法未调用”的旧哨兵表述移植。本片会实际调用现adapter到MockTransport；不是实际模型。子进程同样guard。命令/JUnit/streams、退出窗口计数/marker/capture/journal状态、inputs/helpers前后与源码冻结、权限表不变均保留，独审正常新dev推送。不安装LIVE，无需等真实账户才能写这片代码。
