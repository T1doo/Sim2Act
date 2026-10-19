# 原 Generate 租约与自然 Source 同调用证明

完整 P-B 结论仍为 **NOT_ACCEPTED**。本轮实际完成原 Source、提取/幂等重放、正文归档与目录分类的有限合成前缀；Cold 显式提交和同 key 防重复已执行，但原 Worker 首个本地读取步骤的最终 finite-lease 守卫拒绝，Cold无模型Attempt/无结果，未到同Run人工验收合同。没有延长原lease/Run/合同期限或补写账本以通过。

本轮产品源码基准为 `9fbcb6a4e682a09f916b4561795f000c609aea10`，Cold测试合同修正为 `84fde1b6a5724c57ce0fa68b868ff82e445ed1d8`，二者src逐字相同。普通开发分支 `dev/production-trial-stages-20261018`，远端接续基准为 `5bd438812a9914fac827014336a5ba38b63d08dc`。原授权的 `8fc70cc4` 和前序产品 `2b290038` 均在祖先链内。当前不是原七槽完整pytest通过，也不等于真实产品/语义签收。

F2-T05 统一目录和自然逐次使用入口已在祖先实现，用户步骤与原HTTP/JSDOM范围见[入口方案](../../F2/NaturalApplicationEntry20261016.md)。本轮从5bd到9fb的`src/sim2act/web`无字节差异，接续处理原P-B生产控制器Mock链的lease/证明耗时问题，不把这些新后端门当作新的目录导航、原生浏览器或语义认证。既有入口的分阶段失败与旧满盘证据缺口仍保留。

## 具体修复

Generate 复用既有 `Worker._heartbeat_lease`，以原实际提交的数值租约为界做有限 SQLite BUSY/LOCKED 重试；同一个 metadata Lock 发布实际续租和首个永久错误，前台只在事务外续租，原逐槽等待与生产 sender 检查同一状态。没有新的 executor、Grant 或权限快照。原 Store.guard、worker/fence/CAS、源证明、合同、30 秒租约、300 秒 Run 截止和七槽均保留。

自然 Source 在 test-only SQLite 的 QUEUED/RUNNING/SUCCEEDED 绑定中，使用同一次 `load_binding → read_release → validate_frozen_candidate → verify_origin` 已完成的局部来源证明，减少同调用的第二遍验证。原 connection、driver transaction、线程、写 epoch、draft、完整 Limits、前后 fresh authority 必须相同；特殊来源分支仍排除，不缓存 bound/StageAuthority，不跨事务或 `state_write` 重用证明。其他数据库或非 test-only 不启用此局部来源路径。

16996 原完整链另捕获 Generate 等待后的具体边界：reserve事务持writer26.478秒，进入时距最后实际lease尚约25.585秒，后续原finite-lease证明拒绝。cac56在原配额等待返回后、预留业务事务前再调用既有受守卫续租；只增原created_at数值以保留相同截止计算。此等待后续租会影响相同PG Generate路径，PG未执行；没有降低Source/Cold资格。

cac56实际Generate3已完成，但Source首次reserve持writer31.484秒（5710SQL、前台CPU30.989秒），超过刚提交的30秒实际lease，Source0Mock/仍RUNNING。4813只把原P-B natural reservation的既有_journal_reads起点从preflight前移至入口Store.guard之前；原资格、guard/association/frozen/preflight/reservation_check调用顺序和写入前终点原样保留。没有新cache或合并Limits，所有命中仍fresh权限，写入仍失效。测试按动态guard计数检查同token和读写边界，不固定递归次数。

4813实际Generate3+Source1；Source收包后VERIFIED事务36.969秒/11228SQL越过原lease，具体拒绝在settle_verified→check_commit，_journal_chain与最后commit_guard未执行。原619B响应和known100/900/1000 usage保留，实际Attempt为REJECTED_KNOWN、Source仍RUNNING；不能称FAILED或已到Source2。只读剖析显示范围查询及SQL构造较重。41643264仅复用2个不可变SQL结构模板，显式逐次绑定rid，不保存ID/结果/Grant/connection，原3次SELECT和owner→expected→own_project→projection顺序保留。7组旧/新函数返回、实际SQL及参数严格相等，原投影负例通过。

两次cProfile的SQL均6277，Limits3/4各自独立；不同并行条件下新profile总threadCPU34.512秒、旧24.072秒，不能称总体节时，不能挑选warm局部外推满足30秒。源码只消除语句结构重建，是否满足原租约需新的隔离整链实际终态。首次未提交编辑中的括号语法Ruff失败及相同编辑检查复现的raw输出保存在support/unfrozen-template-syntax，未混入冻结SHA门。

416整链实际4Mock（Generate3+Source1），Source收包事务30.180243秒/12800SQL/前台CPU30.047281秒，末尾原commit_guard拒绝已过lease；Source仍RUNNING，未到第二Source、提取或Cold。失败点比4813更后、SQL多1572句，不能将30.180与36.969秒当同量benchmark。a3ee再仅固定Store.own_project的SQL结构，以两个独立有类型bindparam和每次新参数字典读取当前project/principal；原owner谓词、完整返回、PERMISSION_DENIED及调用位置保留。lock_project/authorize未改，无owner/Grant/结果缓存。8组实际旧/新SQL与参数、完整行或拒绝一致，包含真实owner更新后的即时拒绝及savepoint回滚恢复。此公共查询影响PG路径，PG未执行。

a3ee带外部计时plugin的整链仍FAIL：外393.642秒/pytest361.42秒，4Mock（Generate3+Source1）；Source收包事务35.718073秒/11228SQL/前台CPU34.524475秒，被原finite-lease证明拒绝，Source仍RUNNING。实际4条Attempt完整行、两Run及原frozen合同只读导出，原DB哈希未变。不是Source2、提取或Cold成功。本轮保留该失败后，只再运行一次同源码标准pytest对照：唯一执行条件变化为去掉外部`-p lease_timing_plugin`，其余原测试、fixture、tripwire、七槽、1RPM、30秒lease、Run300及外1800秒界限保留；输出目录单列。此条件差异已事前记录，不将无plugin结果反推为旧失败根因。

a3ee标准对照同样FAIL：外609.975秒/pytest580.23秒，5Mock（Generate3+Source2）。实际Source第一Attempt VERIFIED、第二REJECTED_KNOWN，最后runtime1022 commit_guard拒绝finite lease；Source仍RUNNING，提取/Cold未执行。最后actual lease1792420543.817289、NS_REJECTED事件1792420546.375957、原Run300截止1792420570.058993；不是Run300先过期。该条件没有外部事务span，具体比较时刻/持锁时长/CPU/SQL未知；不能借上一链补数，也不能把plugin作为必要原因。两个完整响应和各自known usage保存。SUCCEEDED结构helper仍未执行，不伪造状态。

9fbcb6a4进一步只固定authorize内资源membership和Grant两个SQL结构，仍逐次执行当前参数/行读取；原owner检查、resource.read递归、项目artifact分支、principal→runtime顺序、全量Grant排序/FOR UPDATE、逐项实时time与revoked any、错误码和成功authority登记保持。没有缓存权限、结果或now、没有合并身份或下推expiry/revoked筛选。5项短门实测通过，其中新测试17组原/新查询完整行、SQL与参数相等；只改一个实际匹配identity Grant后立即拒绝且captured proof重核拒绝，回滚恢复。PG公共路径有同样SQL结构改动，PG未执行。旧416剖析的635次authorize/9.960累计秒只是选取窄优化的既有线索，不是9fb实测性能或节时保证。

9fb标准链实际Source SUCCEEDED、两Attempt VERIFIED，并完成原提取/同key重放不新增发送、原始正文/规范hash、四个归档拒绝、Release/Instance和目录NATURAL_PB断言；外554.364秒/pytest541.94秒，5Mock。测试在Cold review构造处误读提取回执的`fingerprint`而KeyError，整项仍FAIL，Cold未提交。84f只修测试：Cold新client读取实际应用详情，核真实`fingerprint`等于原提取回执`candidate_fingerprint`后绑定，不改产品或制造指纹。

为避免重复已有五槽，用本次结束原DB的只读backup作一次有界Cold接续。脚本先匹配原DB与ended导出hash、原SourceID，原typed合同/批准/expiry/current权限/软件、五槽accepted账本/账户cursor和Source两VERIFIED全部重核，原extract重放前后业务snapshot不变，旧两Source wire原文与归档再次相等。只重建原configured三项合成stand-in与有限Mock factory，不调用setup/initialize/prepare/新总批准，不改Grant/Run/时间/TTL/quota/ledger。原总批准expires_at保持1792422750.2994251（15:12:30.299425 UTC）。Cold业务段由84f原测试AST提取，只有3处新发送/readReport计数调整（新2/旧5分记），原Cold显式提交/同key/当前lease/1RPM/七槽/22归档/结果/PENDING断言保留。这是跨进程同合同接续，不能称84f单次完整pytest PASS；原pytest自动lease观察fixture未启用，原Source两条内存readReport未重建，只有Cold新报告。

该接续实际FAIL：外230.645秒、2113输入稳定、**0新Mock/0Cold Attempt**，原五槽前缀DB哈希未变。Cold Run `run_4ed4f78b22df49edbf752dac24b40b3d` 保持RUNNING、version/fence均1、cancel=false、无steps/无结果。原trace为runtime733 `_advance_local`→pa_spec_apps1371最后commit_guard→gate934综合身份/版本/取消/finite-lease谓词；已结束行lease1792422319.9024134，Run300截止1792422512.237031、合同截止1792422750.2994251，命令结束1792422341.512885尚未到后两项截止。没有收集事务span或精确谓词比较时刻，不能补称具体持锁、SQL/CPU或旧观察器closed证据。本次新client实际draft绑定、材料/Goal review、显式submit、同key cached重放及阶段批准已通过；Cold结果、owner合同、七槽accepted、22归档以及两条完成的Cold reservation报告均未到达。剩余是Cold首个本地读取证明的工程耗时/lease边界问题，不是访问审批阻塞。

## 有界因果证明和失败保留

1030 的定向测试实际复现：真实 BUSY 5 后旧 Generate beat 永久停止，writer 在原实际 lease 前约 14.38 秒释放，但没有再成功续租；随后原 guard 的实际比较超过原 lease，fence 保持 1，请求/Attempt 均为 1。这里只证明此放大机制，不识别旧 v7 的具体长持锁者，也不是完成 Generate/P-B。

首个 a340 验证实际 2F：一笔前台 heartbeat 事务耗时 47.628 秒，未到达调度边界，清理时 daemon 仍 alive；另一例 Grant 测试字段错误。无当时 CPU/SQL 细分，后来较快 span 不能重建该原因。后续缺 BUSY、writer 请求生命周期不足、fallback 序列化错误和受控 SIGINT 均保留，未改写为通过；原满盘丢失的旧独审报告没有补回。

完整链第一次在 77b 执行，4 Mock（Generate3+Source1），Source 同事务验证持 writer36.530秒、4436SQL，原 lease guard 拒绝。第二次在 fea6 执行，5 Mock（Generate3+Source2），Source 终态证明超过原 Run300，Run FAILED；错误观测晚于 Run 截止约2.566秒、仍早于实际 lease约5.670秒，不能说是失租。两轮均未到提取或 Cold。16996第三次完整链为1Generate Mock后FAILED（外144.037秒），Source未执行；原lease而非Run300过期，观察收尾闭合。不同版本的结果不相互替代。

## 已完成的窄验证

| 阶段 | 执行 SHA | 实际结果 |
| --- | --- | --- |
| transaction-spans | 77b54fcd | 2PASS；1Mock；实际 BUSY 后原 guard 在旧 lease 已过、新实际 lease 尚有效时成功；无重复发送，owned线程退出 |
| focused-boundaries | 77b54fcd | 9PASS；1Mock；原所有权/到期/有限重试/提交区间/永久错误发布，以及已有 Generate 收包后源撤销 |
| retained-origin-corrected-command | 15ace9a9 | 保留的实际 Mock3前缀副本上，共享helper断言PASS；0新发送，完整字段相等，真实Grant更新拒绝并回滚；不是活Run/PB验收 |
| aligned-final-focused | fea6fa56 | 3PASS；2Mock；实际 writer/BUSY/新租约、永久Grant拒绝、Generate收包后源撤销事实保存 |
| states-mypy | 16996e71 | 完整src113文件PASS；外151.490秒；2112输入前后不变 |
| states-ruff | 16996e71 | 7个变更文件PASS；外1.887秒；2112输入前后不变 |
| queued-completed-command | 16996e71 | FAIL；外159.165秒；QUEUED对照PASS，真实Worker只完成1Mock/1VERIFIED Attempt，Run仍RUNNING；SUCCEEDED helper未执行 |
| post-wait-grant | cac56db0 | 1PASS；外21.783秒；原等待后真实撤权，既有heartbeat拒绝并粘滞，0Attempt/0Mock，业务快照不变 |
| post-wait-ruff | cac56db0 | 7个变更文件PASS；外1.451秒；2112输入稳定 |
| post-wait-mypy | cac56db0 | 完整src113文件PASS；外51.331秒；2112输入稳定 |
| entry-scope-mypy | 4813e7a4 | 完整src113文件PASS；外99.929秒；2112输入稳定 |
| entry-scope-ruff | 4813e7a4 | 8个变更文件PASS；外4.321秒；2112输入稳定 |
| template-projection | 41643264 | 原投影负例及动态rid回切1PASS；外71.555秒；0Mock |
| template-parity-command | 41643264 | 7组完整返回/DBAPI SQL/参数严格相等；外31.133秒；0Mock/仅SELECT |
| template-mypy | 41643264 | 完整src113文件PASS；外122.878秒；2112输入稳定 |
| template-ruff | 41643264 | 9个变更文件PASS；外6.242秒；2112输入稳定 |
| owner-query-projection | a3eeaedd | 原投影及当前owner模板2PASS；外25.079秒；0Mock；2112输入稳定 |
| owner-query-boundaries | a3eeaedd | 固定source/实际software关闭及原等待后真实Grant撤销2PASS；外44.047秒；0Mock；2112输入稳定 |
| owner-query-mypy | a3eeaedd | 完整src113文件PASS；外41.401秒；2112输入稳定 |
| owner-query-ruff | a3eeaedd | 10个变更文件PASS；外0.850秒；2112输入稳定 |
| owner-query-pb-full-chain | a3eeaedd | FAIL；外393.642秒；4Mock=Generate3+Source1；原finite-lease拒绝，Source仍RUNNING |
| standard-pb-full-chain | a3eeaedd | FAIL；外609.975秒；5Mock=Generate3+Source2；第一Source VERIFIED、第二REJECTED_KNOWN；原finite-lease拒绝 |
| authority-query-focused | 9fbcb6a4 | 5PASS；外87.165秒；0Mock；2113输入稳定 |
| authority-query-mypy | 9fbcb6a4 | 完整src113文件PASS；外74.872秒；2113输入稳定 |
| authority-query-ruff | 9fbcb6a4 | 11个变更文件PASS；外1.923秒；2113输入稳定 |
| authority-standard-pb-full-chain | 9fbcb6a4 | FAIL于Cold前测试字段KeyError；外554.364秒；实际5Mock/Source SUCCEEDED/提取等前缀已通过 |
| completed-source-command | 9fbcb6a4 | 非冻结；0Mock且结构断言完成，但作者运行中编辑测试致一文件输入变化；不是冻结PASS |
| completed-source-frozen-command | 84fde1b6 | 0Mock结构检查PASS；外18.256秒；实际SUCCEEDED/两VERIFIED，完整binding等价/真实Grant撤销拒绝并回滚；2113稳定 |
| cold-test-fix-ruff | 84fde1b6 | 仅修正测试Ruff PASS；外0.746秒；2113稳定；产品与9fb完全相同，不重复mypy |
| original-cold-continuation-command | 84fde1b6 | FAIL；外230.645秒；0新Mock/Cold0Attempt；材料Goal显式提交/同key防重复通过，首本地read最终guard拒绝 |

16996 的 QUEUED 对照中，完整来源调用1次对原fallback2次，完整返回逐字段相同；同调用实际UPDATE匹配Grant后被VERSION_CONFLICT拒绝，事务回滚；完整Attempt行前后相同且为0。脚本原API取消副本中旧过期零Attempt Run，原claim将其正常归结CANCELLED，原API新建的新Run才执行；没有直接改Run状态、租约、时间戳或权限。保留原603数据库哈希不变。该脚本没有捕获Worker内部异常，因此退出原因UNKNOWN，不能根据与mypy重叠就断言CPU导致。

作者首次completed-source零发送检查尚运行就编辑Cold测试，是实际证据顺序错误；其result原样记录unchanged_inputs=false，唯一变化为该测试，after字节严格等于84f。原前后清单、漂移说明和非冻结0发送结果保留；提交后同一结构helper在84f重跑通过且2113输入稳定。产品源字节没有变，不把首次记录补写为稳定或门通过。

## 证据与限度

各阶段保留准确 command/result、stdout/stderr、JUnit、输入前后hash、合成数据库、有限Mock原文与失败观察。source-snapshots包含每个实际执行版本的src/tests/scripts/配置Git归档。输入清单最初2111项，添加来源测试后2112项（713个Git blob、1399个JS依赖hash），9fb新增窄权限测试后2113项（714个Git blob、1399个JS依赖hash）；外部runner/plugin/scripts另存，Python安装/主机未封闭冻结。状态脚本的hash在运行中首次观察，不能补称启动前已有hash。9fb初次未提交测试编辑Ruff I001及修正过程单列support/unfrozen-authority-import-sort；首次原输出只在工具历史，保留原字节和准确说明，没有补称冻结门失败。

计时、stack、SQL观察及原文落盘有自身开销，不能当作透明性能基准。完整链插件的SQL只监听第一Store成功语句，失败driver wait没有after事件、Cold engine SQL未监听；收尾快照不是独立join证据。无对应历史计时则保持Unknown。普通Generate的所有微小永久错误/发送竞态没有被本轮全面证明，PB生产sender有显式检查。

真实模型与真实账号探测均为0。固定生产账户来源仍缺少经审查来源，实际软件资格不匹配；没有改来源/资格锚点自授LIVE。Windows、PG、原生浏览器、真实语义/场景、用户人工接受、远端CI与部署均未执行或未验收。原Actions API403没有换凭据重试。本轮不扩旧相邻恢复矩阵，也不把不同Run/不同源码的槽拼成一次成功。

本轮实际新Mock证据合计51：44条独立transport原文记录、两条早期失败前缀中的6个实际收到Mock Attempt（没有另存transport计数）、QUEUED状态辅助执行1条；Cold接续新增0。该计数是失败/诊断/窄门/前缀的总量，不是接受数量。上轮5bd包中的14个P-B+3个ordinary Mock另行保留，不拼入本轮链。15个实际执行SHA的Git源码归档、所有中间失败、原始数据库/行导出、外部脚本与独审均纳入封包；选中输入不是Python/主机的封闭环境快照。

最终独审同样判定完整P-B **NOT_ACCEPTED**，72文件manifest SHA256为`7452e51a97b16aeab65f4a582240328bae5d73481d849ad16ffc30aae44b9e53`；报告SHA256为`9c328194957cd6d50044338488f6aa8938a228e6b64a7acafa6f64f8d4fbdb2e`。可读[最终报告](final-review.md)及[清单](review-manifest.json)，同一原件在包内`independent-reviews/84fd-final-terminal/`。独审只读源/原件/ended导出，没有独立执行产品、DB、模型、测试、PG、浏览器或网络。

完整原始包与每成员hash验证、准确输入身份/漂移分类、阶段结果及seal随本目录交付。最终推送SHA和远端/工作区差异由归档后的交付回执核对，本文不提前宣称push或CI成功。

可下载的[原始证据包](pb-lease-cause-raw.tar.gz)为78,958,506字节，1,412个原件加manifest/seal共1,414成员，逐成员校验通过。[封包回执](package-receipt.json)、[原件清单](RAW-MANIFEST.json)、[seal](RAW-SEAL.json)、[分阶段结果](phase-results.json)、[输入身份](input-identity.json)、[源码桥接](source-and-assertion-bridges.json)和[汇总](analysis.json)同时保留。

- 包SHA256：`dec945b94433667cb1bfc6f0faccdf6ab46ad423022f1290536fe1d14538473e`。
- 原件manifest SHA256：`378c480862210b599a38e7cff960785158651563d0779579748b5762e904df05`。
- 最终独审72文件manifest SHA256：`7452e51a97b16aeab65f4a582240328bae5d73481d849ad16ffc30aae44b9e53`。

本目录归档提交只变更docs，src/tests/scripts/配置与实际执行84f逐字比较；最终远端和未提交/未推送差异在交付回执再核。
