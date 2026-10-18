# P-A完整阶段证据与原业务提交桥（未安装设计v1）

基线4bb3c26f5f67511795771c9187537aee4e852590已由父级有限接受。root唯一仓库writer，其余代理completed；实际HEAD/remote同SHA、clean、上游0/0，main6f688不变，余23GB。只读核对后冻结本设计，再独审实施；此时仓库未修改，没有产品/pytest/模型执行。新普通开发分支待设计审后从该SHA建立，不改main、强推、部署、凭据、权限或费用。

## 原方案与最小实际价值

V5分阶段计划F2-T02（目标→规划/清单→编译验证→应用）、T04/T05（同一可信运行器/动作入口）、T08（Release/实例数据分离）及AT09/11是本片定位。最小正向选P-A同一原批准的generate3→source2→cold2：原Goal A生成应用，原应用/Release/实例读取A形成成功任务，再以B及完整Goal显式冷运行，实际结果与原归档均可回读；人工验收仍PENDING。账户费用source和业务source分开，不用新loader的ALLOW证明业务成功。

P-B的提取Recipe与同trial业务source证据还需另一个最小桥及实际冷链，本片新绑定暂不接受PBTrialContract，不修改旧P-B分支、不冒称AT10或整体F2通过。先取得一条使用新持久链的完整业务路径，优于增加仅做准入诊断的外围模块。若范围再扩P-B，必须另冻结实测，不能凭共享内核继承成功。

## 实际断点（已读源码）

1. Worker.reserve在原事务中创建Core Attempt/预算reservation/原wire指纹，再调用pa_trial_dispatch.reserved；旧reserved写natural_trial_budget并归档请求。
2. goal_applications.process与natural_spec_runtime.advance_model都调用现pa_trial_dispatch.request_captured，其原controller guard分别核生成/节点当前身份与业务状态，现InternModel实际捕获body，再回原parse/verify/提交。
3. 新production_trial_sender遇到已有journal原key一律只读。因此不能在Worker.reserved先写journal槽，再以dispatch_from_source_offline“续发”，这会误把历史当许可；也不能把旧预算复制到新journal。
4. natural_live_admission._generation_accounted、_pb_origin及natural_source_archives._source_prefix仍固定消费旧synthetic预算；GA三Attempt的canonical归档与NS两Attempt的完整body/Operation必须同新capture raw/canonical分别重核，不能只给stage看一个新账本receipt。
5. source/journal/capture的accounting接受先于业务解析；它恒business_accepted=false。真实的候选、模型节点、Operation/AppRun和结果仍只能由原业务验证提交。

## 固定、未安装的Worker绑定

在现pa_trial_dispatch内加精确冻结JournalTrialBinding（名称可收敛），仅contract、approval_key、opaque account_id及自动完整contractFP/固定UNINSTALLED版本；只接受原P-A TrialContract/TrialContractV2，不收registry、source结果、凭据、URL或callback。validate/_binding硬限制exact Worker/Settings/Store、test_only SQLite、mock/livefalse/token空、exact MockTransport、原model/caps及canonical quota，重核原_approved及固定source.load_offline。旧PATrialBinding默认分支与production_preflight/resolve_account、字面软件anchor/pin均保持；新绑定不装API/settings/CLI，不伪装原qualified association，已标记natural_trial_runs关联的Run不能借新绑定绕其资格门。

新Worker仅由离线fixture明确构造，使用现Worker和原业务控制器，不新造executor/Grant/动作/结果写入器。生成和每个source/cold仍需原材料/完整Goal、原key、独立阶段review/明确approve、Run/runtime/version/fence/worker/有限lease/Run期限/当前权限。不能由HTTP请求选择此会计后端或传内部信任对象。

## 原Core Attempt与一次新发送

新绑定的Worker.preflight在Core预留前核当前批准、source、原stage/Run/Goal与剩余状态；wait_unreserved读取同canonical账户新journal cursor，沿用原60秒间隔/stop/Run300/原expiry和heartbeat，绝不对已预留/unknown槽等待后重发。

Worker.reserve仍只创建原Core Attempt/reservations（同一aid/实际wire/原envelope），在该原事务保存现请求body归档及新绑定版本，不创建旧synthetic trial槽，也不提前创建新journal槽。Core是原执行预算，新journal是同一actual Attempt的原trial/cursor约束，两者不是两次模型请求；旧natural_trial_budget本trial记录必须为0。

现request_captured的新绑定分支，先以原owner/Run/Attempt STARTED、modeMOCK、绑定版本、wire/原envelope及请求归档构造完整ReservationIdentity，再进入同一新sender共享核心。只有这一次调用可以新reserve→mark→原adapter；已有journal key只读并阻止重新取得CapturedResponse来重放业务，不从历史archive自动补发/续发。若Core提交后尚未进入journal即失败，原STARTED/reservation保留、原controller拒绝自动重试，不因缺journal/capture推断免费、未发或退额。

sender内部复用现request_captured已有的controller guard与provider（精确InternModel/同一MockTransport/现固定synthetic占位），不另造发送器；原业务guard在实际wire guard内运行，之后再做固定source/journal最终guard，deadline取二者最小。这是现受信控制器闭包的原调用，不新增可由HTTP/调用者指定的loader、guard、provider/channel或callback注册。source loader仍固定模块，同原c重读；保留原公开offline入口签名。Worker/store/engine/settings/transport/绑定在整次交换固定，原guard前后重核；迟到事实只回原captured Store，Worker变更不能让事实或业务提交写入别Store。

新sender共享_receive在原owned slot/Run标量门后，从同一次实际body派生usage/协议/raw SHA/bytes/canonical ASCII几何并重读source；capture两镜像+journal/cursor四镜像继续同事务。把相同bytes与原aid接到现pa_trial_dispatch请求/响应BodyArchive，必要NS body归档也在原接收事务复用现record_response；只在STARTED原owner/完整identity上新增，不对已完成历史补证明。归档必须使用captured Store与原c，不依赖回调后可变worker.store。原NS/GA稍后重复归档只能完全同字节幂等，不改原immutable archive。

仅本次实际收到且当前accounting有效，才把同一CapturedResponse交回原GA/NS解析器；收到UNKNOWN、来源已失效、取消、binding漂移或历史duplicate，都保已收事实并拒业务，不从公开receipt获得body/执行权。真实网络/模型0，现内部synthetic token不是真实凭据，也不等于LIVE安装。

## 原归档与业务提交

pa_trial_dispatch原_archive/_identity/check_commit/settle_verified/reject对新精确版本分支接新journal/capture，而不是往旧budget造影子slot。业务事务继续由goal_applications及natural_spec_runtime原parse_generation/parse_candidate/parse/prove_node/receipts/commit_guard提交Attempt、Operation、AppRun/结果；新settle_verified只重核原source/Run以及同aid/wire/body/known usage，不能把已结算journal duplicate当当前授权。

Journal.accepted保持会计含义；即使通用协议与用量成立，业务schema/引用/候选失败也不能生成结果、source阶段或cold批准。业务失败由原Attempt/Run/Operation状态保留，后继阶段必须同时证明业务成功。不得回写不可变Outcome或将accounting accepted改成语义签收。来源/取消/版本变化的原业务事务拒绝/回滚继续有效，已接收费用事实不退款、不补零。

## 阶段证据的固定桥，无第二份账本

_generation_accounted在原full owner/lineage门之后，根据三条实际服务端Attempt上精确新绑定版本选择固定新journal证明：strict test_only SQLite、原contract/approval/account/canonical quota、三slot与三actual aid一一对应、原wire/Run/runtime/版本/fence/worker、source payload、完整capture、actual Attempt RECEIVED、known usage/原generation raw canonical归档都须相符。raw SHA与canonical SHA各对其原bytes，不相互冒充；不复制新ledger成旧budget shape或持久派生账本。混合/不明版本、缺journal/capture/原Attempt、只会计成功无候选均拒绝，不fallback给旧后端。

Source/cold的原_stage_current/StageAuthority/approve_stage/原权限与recipe/app/Release/instance版本验证继续运行；只将其中原_generate accounting proof接上述固定桥。两个NS节点必须走原Operation VERIFIED及完整NS body归档/用量，最终结果由原verify_job/receipts重核。原阶段读取不是send许可，不扩source/cold执行窗口，也不把新synthetic源升级到真实费用事实。P-B新模式仍拒绝，旧PB来源解析器保持。

## 最小新增资格（拟三节点，必要时最多四）

A 新绑定的完整P-A动态正例，实际Worker+原InternModel→exact MockTransport，三Generate、两Source、两Cold，同trial七个新journal槽与七actual Attempts一一对应，old synthetic trial账本0。原A/B及完整Goal、显式两次stage consent、实际应用/Release/实例与同Run结果/当前人工PENDING可回读，结果内容按独立合成oracle分别核A/B，所有原tools/Operations真实走现代码。公开回执real/live/dispatch/business=false。

B 从本轮新鲜实际链取得有界只读证据窗口（不使用旧bundle/旧DB）：缺业务Attempt/只journal已接受、错误raw/canonical或错scope/aid不能形成原stage证明；拒绝窗口全表无污染、无新handler，不额外跑生成/取消/恢复长矩阵。每项fixture篡改与原操作窗口分开，不能把派生hash当真实来源事实。

C 一次实际合成200/known usage/通用协议成立但原业务schema错误，证明journal费用事实保留、原候选/Operation/结果不被接受、后继阶段不可运行、不自动重发。该节点是新accounting→business耦合边界，不重复此前source撤销/取消窗口。若新增第四项，仅限实际接收+原业务提交原子边界的必需反例，经审查明确，不能扩旧故障矩阵。

正常正例保原1RPM实际六个≥60秒间隔，不降原限制。单次首跑可有界900秒，长时间来自新完整链必需的原间隔，不人工等整点；每60秒内有进展说明。若使用显式合成时钟，只能另标时钟模拟资格、不能声称墙钟1RPM；不得隐式挪时间/放宽lease。此处先冻结实际时钟方案，静审性能风险后定首跑预算。原19/12/8/9矩阵不重跑、不累加，新链及失败原件完整保留。真实账户/费用/source producer/语义/模型、Windows/native、PG、远端CI、LIVE安装与PB新链仍NOTRUN。

## 写入范围与交付

优先修改现pa_trial_dispatch、Worker原Attempt绑定字段、production_trial_sender私有共享接线、natural_live_admission原accounting桥；若NS归档同事务需要只读现natural_source_archives的最小复用，不新造外围executor/Grant。新测试验证实际产品路径而非自制仿真执行器。设计审后从4bb建普通dev分支，必要静审→源码测试冻结→首轮有界资格→有限独审/原件封存→正常push，精确报告SHA/remote/dirty/ahead差异。真实来源缺失不阻止本片离线编码，但本片不能据此自动安装LIVE或签收真实权限。
