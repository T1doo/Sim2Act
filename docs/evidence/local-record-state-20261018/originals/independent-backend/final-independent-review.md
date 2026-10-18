# 本地记录与版本化状态：最终非作者有限独审

最终产品冻结：`d5eadc708ee2968bb574ec66e335c05451f66cf7`。基线：`5322dfd7f8c6686be29c9989d2f02fb6f54cfc28`；产品初冻：`a38c33f7496dca3da079d59bab16f13b5c283d1e`；新资格测试提交：`81ad223bf72fb6e15af03ef6aca87af70e9bf4f8`。本人始终只读仓库，不是产品或这些资格测试的作者；仅在本外部目录写报告、固定源码副本与自有SQLite探针。

## 有限结论

**通过有限源码独审：已知P1/P2均收敛，未发现尚存的明确P1/P2阻塞。** 新族具有真实typed CREATE和OPEN→DONE状态合同、独立record_id及revision、当前集合投影和不可变历史。它复用既有artifact.save_text@1、原项目写权限交集、JSON保存helper、正常Worker及既有Operation/typed表；没有新executor.ref、Principal、write Grant或数据库表。每事件2条既定derived resource.read Grant如实披露。DONE只代表业务状态，不等于自然语义人工验收。

范围是当前固定表单切片，不声称F2-T06全部完成。实现与原方案映射见 `design-review.md` 和仓库 `docs/F2/LocalRecordState20261018.md`；F2-T06在原计划 `docs/分阶段开发计划.md:98`，产品记录/typed表单/事务依据见 `docs/平台产品设计.md:99,103,158,195,207,383,452`。

## 源码、授权与事务复核

`local_record_apps.py:152` 双seal原请求严格校验；`:188–222` 新旧家族元数据门有独立INSTANCE/PREPARE/RELEASE_SEAL/RUN_SCOPE锚；`:436` owned iid、原创建pair、release fingerprint及项目runtime精确绑定。`:482` scope_job先核owned metadata和独立RUN_SCOPE；`:504` authorize_data只投影全部历史成果标识并当前授权，之后才读取typed/private内容。`:561` accepted_binding核精确原typed input、Confirm、preview/ACCEPTED pair、Run/AppRun身份、FrozenRunContract及0模型预算；原Goal/输入不能通过新key重建偷换。

`:600` projection逐事件独立核typed schema/版本、Run/AppRun、唯一VERIFIED save Operation/intent/local_effect/receipt、实际canonical JSON及hash、原preview事件、业务record revision/双链、COMMITTED事件和Run结果，拒绝成功集合不匹配及非成功effect残留。`:693` 原key GET成功必须唯一匹配同一Run/AppRun的真实已提交历史。`:783` 正常Worker将JSON资源、derived read Grant、Operation、typed追加、集合CAS和终态放在同一事务；开始和最终门限定原deadline/previewexpiry，最终重验当前授权、真实回读、fence、租约和停止状态。`:841` fail_job只读终结所需metadata；`:892` 控制保留活动租约，取消后不偷读正文。

旧共享App/Release/iid/Run/approval读写入口经api/app_jobs/db/goal_applications/internal_api/lifecycle前置门拒绝新族，不能原样放宽旧natural/CSV合同；direct lifecycle.commit_release_tx也有前置guard。UI有限复核覆盖专用目录入口、明确版本/实例选择、每次typed预览及另行确认、同Run/当前投影/历史分开显示、原key未知只GET、忙态防重复、账号connection/project/workspace/app/instance/read/edit多代隔离以及失败清除私有正文。完整UI资格由作者运行，本人只独立读源码及回读原始证据。

## 原发现原件及修复状态

`wip-source-review.md`保留P1原key成功只信状态、P2独立family锚缺口、P2 fail_job整行私有读取的发现及修复定位。修前未独立封存完整local_record_apps.py文件，未在未修字节上亲跑原P1；该证据限度明确保留，不能补写成当时已经动态复现。首次probe项目POST observer误写200而实际201的setup失败保存在`wip-recovery-probe/first-attempt/`；无Worker、无故障注入，不隐藏为通过。

## 本人实际执行与冻结桥

本人执行两次有界实际隔离短probe，每次1个正常NoModel Worker，0模型：第一份WIP `wip-recovery-probe/`用于修后P1证明；第二份候选a38 `frozen-probe/`中成功原key回读后，分别删除自有typed/Operation，原GET各409 VERSION_CONFLICT且无写，恢复known rows后全表精确一致。第二份还做3个metadata分类检查：iid当前release指针改旧仍由原INSTANCE锚拒绝；approval.kind改旧由PREPARE锚拒绝；移除PREPARE后由RELEASE_SEAL锚拒绝。probe内耗时1.809646s，完整命令退出0，原脚本、HTTP原文、stdout、result、132生产源码副本及运行后0变化均保留。

没有第三次亲跑d5 Worker。a38→d5的唯一生产差异为同一文件：projection局部dict注解及原`require(old is not None...)`后冗余assert收窄；精确raw diff在`candidate-to-final.diff`，未放宽运行时门。`final-source-manifest.json`独立核对全部132个Git生产文件，d5冻结、当时HEAD、工作树及作者final-inputs-before均0差异。完整132含2个JSON软件锚；作者UI每例source输入132项的实际口径为130生产+2测试，不能误称132生产。本人将这130逐项桥接d5，另2生产JSON锚由完整Git桥覆盖。

## 作者最终资格原件回读（并非本人亲跑）

- 最终d5后端9项：`backend-d5eadc70.xml/log`，9PASS/46.150s，无失败/跳过；涵盖真实A/B/A→DONE、预览零业务写、严格typed、原key冷GET/精确重放、防重复、data_version/record_revision CAS、账号/项目/实例/旧family隔离、撤project-write/历史read前private SQL屏障、实际helper故障整体回滚。
- 最终d5实际HTTP/JSDOM 3项：`ui-d5eadc70.xml/log`，3PASS/50.029s。flow=62页面检查/56页面HTTP actions/54资产/3页面正常NoModel Worker；navigation=36/60/27、1 fixture Worker/0页面Worker；revocation=34/18/27、1 fixture Worker/0页面Worker/0页面POST，只有精确known Grant被fixture撤销、原Run与其他行不变。navigation的账号维度是同一账号断开重连，不能写成另一账号登录；后端另有真实foreign-account拒绝。
- 旧共享原批次`shared-d5eadc70.xml/log`完成CSV实例及text-owner两项后，完整旧PA生成页面长测未完成。父级核实自有pytest cmdline后SIGINT停止，`shared-bounded-stop.json`记录停止时409.132s；pytest整体412.405s（日志412.41s）。XML只有两个具名完成PASS及一个无name占位，不可据零failure冒称整个原四项通过。PA完整生成UI本轮NOT_VERIFIED；原后置CSVfullreport也未在该批执行。补跑直接natural-owner PA与CSVfullreport两项定向回归`shared-bounded-final.xml/log`已2PASS，XML152.052s（日志152.06s），没有重跑前两项。共16个唯一完成正例，分批9+3+2+2；另一个PA完整生成页面明确NOT_VERIFIED，不称全部尝试均完成或一次16项全绿。本人读取两个完成批次的原XML/log，并回读natural PA同Run ACCEPTED原证明、CSV fullreport两个不同SUCCEEDED Run及text-owner两个实际Run历史/权限证明。此缩小兼容范围覆盖本次主要旧共享入口，未发现必须保留完整旧PA生成UI长测才能收敛的源码风险。
- `mypy-corrected.log`实际为7源成功；旧3错误原件`mypy.log`保留。作者后端WIP首轮1PASS/8FAIL26.140s、修正轮7PASS/2FAIL34.316s原XML/log均保留，之后qualified9PASS42.891s及候选a38资格9PASS47.001s不冒充最终d5一次全绿；UI WIP2PASS38.380s及候选3PASS49.484s也保留。Ruff/Node/diff为父级报告，本人未亲跑，最终交付以父级原件为准。

本人另执行`audit_final_raw.py`读取作者原XML及raw JSON，完成557个断言（多数是文件/资产字节比较，不能冒称557产品case），结果`final-raw-evidence-audit.json`。重算3条实际JSON字节hash及集合/record链、真实save Operation/intent/effect/typed/Run、独立A DONE@2+B OPEN@1投影和6条派生read Grant；核三private-barrier场景blocked0/full_binding_reads0，核三UI before=after及全部108次served资产SHA。此为证据再计算，仍不是亲跑作者资格。

## 保留边界

没有运行真实模型、真实业务语义/场景、Windows/native浏览器或设备、原生PG、远端CI、部署。旧满盘环境独审报告未落盘缺口及取消窗口NOT_VERIFIED没有补回。报告不承担父级远端push/CI结论，精确远端及未提交/未推送差异由唯一写入者最终披露。

父级最终纯证据observer先因Path.glob包含pytest current符号链接误计重复scene失败，原first脚本与明确reproduction日志保留；first stderr没有单独重定向，不把再现日志当原日志。父级随后修正observer通过；本人独立audit始终排除current，只处理3个物理scene。该observer未改变生产或资格原件。最终作者summary/verification为父级执行，本人对上述原件的再计算通过独立记录在本目录。

本目录于封存时停止写入。后续远端153分支头核对、证据提交和push结果由父级最终披露，本独审不预先冒称其结果。
