# 新文本应用自有目标与逐项owner声明：只读设计审查

日期2026-10-12，独审`/root/text_logic_review`。起始仓库`/workspace/Sim2Act`，分支`dev/text-logic-owner-20261012`，HEAD `233ba9618ba462aad19e1ca16f085cd0d7242632`；首次检查worktree干净。root唯一产品/src/tests写入者；本阶段仅写本次/tmp，没有运行测试、Worker、HTTP、Node或模型。

结论：拟议最小设计可实现。现有owner的context、PREPARE/DECIDE/STOP、原key只读恢复及不可变256记录链可以复用；必须新增可信新家族base与独立自有GoalCard绑定，不能仅放按钮或读取旧源/目标GoalCard。本报告是设计可实现性审查，不签实现或测试PASS。

已读`owner_acceptance.py`、`goals.py`、新文本逻辑及Release索引、native GoalCard表、owner-review.js和相关旧测试定义；对照V5 F2-T01/T08及本轮有限文本无旧内容合同。

## 最小设计与必要缺口

1. **自有目标独立关联，不改旧执行候选。** 新模块应由已经严格核验的newlogic task marker选择分支，并冻结owner/project/app/candidate/runtime/resource/hash/logic/current budget。在该家族只创建新的native GoalCard；不接受外部GoalCard ID，不自动复制旧source或初始target的标题/目标/条目/接受声明。已有candidate.manifest.goal_ref保持logic provenance，不能为owner目标改candidate、旧Release或原对象。可在owner contract显式标记`goal_source=APP_OWN_MANUAL`，避免把人工新目标称为提取来源。

2. **事务与权限helper不能直接照搬。** `goals.create_card`、`revise_card`各自开tx；`snapshot`固定用项目runtime。新head/version、绑定主记录和双seal、请求回执必须在同项目锁/同一c事务写入，任一失败全回滚，不能调用嵌套tx后留下孤立GoalCard。写前先核user+fresh runtime当前target授权/bytes/hash及独立logic/budget。若使用project runtime作为native GoalCard额外权限要求，必须明示并保持一致；不能无意将其变成新应用运行的第三权限域，更不能补Grant。

3. **先定位owned app/head再读完整内容。** 新API先在SQL/metadata层确认owner/project/app，锁project后才load candidate、绑定及本次自有card版本。resource_refs先严格等于新manifest target一份，再读取该target，不能先循环请求refs读取旧材料。自有card loader先核native head的id/project/version/fingerprint与已封绑定；不能用`goals.load_card`遍历50份历史或走原生成Run取source_goal。原源/目标GoalCard不是备用来源。

4. **单一自有card、明确CAS及单调修订。** 首次创建要求当前无自有绑定，返回新card ID；另key不能为同app再静默生成第二张card。修订从已封关联派生自己的card ID，不接受调用者替换ID；精确expected candidate/head version+fingerprint/当前binding fingerprint+consent同时比较。同key换body冲突，原key GET只读查账，不补写、不自动POST重发。每次scope修改也产生新native版本和新绑定，即使GoalCard content字节未变。所有旧native版本和绑定回执保留。

5. **generic native编辑必须失效，不能绕过。** 现普通GoalCard更新入口能独立改变head。若保留该入口，新owner loader应在head与sealed binding不一致时拒绝并将旧签收STALE，不自动追认新版本。通过新自有修订入口重新声明才产生新binding。A→B→A内容复原仍必须有新version/绑定身份，不能恢复旧ACCEPT。

6. **完整条目及容量。** 当前`Decide.choices`上限81；五个列表各16共80项，加goal/title/applicability/固定technical scope最少84，若材料范围另作一项85。新家族应允许<=100且运行时核完整ordered IDs恰好一致；旧家族仍按它自己的冻结项列表拒绝多余/遗漏项。完整title、goal、known、assumptions、unresolved、constraints、acceptance_checks、resource_refs都必须保存在contract；title/每个原条目/scope/固定技术范围须成为可逐项声明的criteria。constraints和acceptance_checks至少1个非空非纯空白条目，title/goal/applicability亦非空trimmed，规定scope长度与UTF-8可编码边界。不能只验证列表长度而允许空白硬条件。

7. **精确指纹比较。** 新GoalCard snapshot、binding/body/seals以及owner fresh contract用规范fingerprint，不能用Python字典值相等掩盖0==false/1==true/int==float。现owner的`fresh != p['contract']`/`==`比较有多处；本新家族至少必须严格序列化指纹比较。context应含完整新card+scope、native head version/fp、own-binding身份/版本/fp、app/runtime/target/logic身份、固定technical scope及当前limits，确保标题、scope或纯版本变化也STALE。

8. **人声明与执行GoalSpec分清。** 当前AppRun冻结GoalSpec恒为`Internal fixed Release result run`，owner.context只证明此app/Release/Instance下真实成功的新输入Worker（非Release样本输入），不是新自有GoalCard版本驱动的执行。建议本轮最小边界：在当前自有GoalCard下显式人工评审既有成功新输入结果；修订后旧签收STALE、另PREPARE才重新评审，不能声称该Run在新GoalCard版本下执行或已闭合完整F2-T01执行契约。若要求修订后必须新跑Worker，则enqueue要冻结own-goal binding ID/fp，owner.context校验匹配；只比时间或仅owner.base加载当前card不足。此政策应在合同和界面明确。

9. **精确instance声明，STOP/恢复保持可用。** 自有目标可关联app，但ACCEPTED/REJECTED仅属于明确Release/Instance/revision/data_version/所选真实Run及criteria的人工声明，不能显示成整个app/项目自动接受。复用现有失败/UNKNOWN/样本输入/未完成Run拒绝、全项reason、CAS、PREPARE TTL和256记录stop reserve。独立logic或target撤权/expiry/budget冲突、native head/绑定/app/Release/instance/evidence/grants变化均使当前声明STALE；历史DECIDE回执可原key读metadata但不能复活。STOP先owner-instance元数据+ledger seal，不依赖当前内容/旧来源，仍应可CANCEL/REVOKE。

10. **界面不能自动给出接受。** 新自有目标完整表单从空白/自有已封版本起步，目标材料只读展示当前target；不得沿用全局已选旧GoalCard或source/target卡填表。把完整范围和固定literal技术范围放在新owner项里，每项ACCEPT/REJECT及非空reason必须人工选择；semantic UNKNOWN/formal false始终独立显示。保存/修订/GET恢复及owner读写都绑定现有identity/project/app/instance/workspace及单调编辑代次；未知接受保留原key，只读恢复，不越代接管草稿。测试只正常可见使用链，不进入已取消的精确候选安装竞态probe。

11. **软件指纹兼容边界。** `text_logic_reuse.implementation`目前从所有src *.py（排除config）计算；新增`app_owner_goals.py`或修改owner代码即改变既有独立logic的软件fp。原233版持久授权可能因此fail closed，即使literal算子未改。本轮不能偷偷重签或迁移它们。应明确只对当前软件创建的授权对象验本新功能、旧源码升级NOT_RUN；若要兼容旧持久logic必须另有明确版本/兼容设计，不能靠测试重新mint掩盖。

## 冻结后最低必要验证

| 覆盖 | 必须实际证明 |
| --- | --- |
| 主链 | 当前软件成功新logic app→旧source撤权/删除或保留撤权→新自有完整GoalCard+范围→内部Release/Instance/未见term普通Worker→逐项PREPARE/ACCEPT与REJECT→冷API/可见JSDOM读回；无旧card/来源继承 |
| 完整条目 | title和五类条目、scope/固定技术范围/材料范围都在契约；最大列表长度可完整决定<=100；缺、重复、换序、额外项、空reason、空白硬条件/范围拒绝无写入；不能默认全ACCEPT |
| 来源和ID | 旧source/target/别app/owner/project card ID或外部card字段拒绝；refs不是唯一新target拒绝且不读取旧资源；fresh authority/marker/current budget都重验 |
| Goal CAS/ABA | 首次无绑定CAS、同key/body单效果、换body冲突；修订新immutable native版本+双seal；scope-only、title、原字段、generic native更新、A→B→A都使旧声明STALE；不得自动复活 |
| 决策精确性 | 只有实际成功、未见输入、当前Release/Instance自己的Worker证据可PREPARE；失败/UNKNOWN/原样本/别instance或未完成Run拒绝；本轮按第8项声明的evidence政策执行 |
| 当前权限与版本 | logic/target/user/fresh runtime撤销/expiry、budget收紧、app/runtime/release/instance/data/evidence/grants变动均拒绝DECIDE或显示STALE；旧来源撤权/删除本身不触发旧private读 |
| 不可变账本 | 保留256链/CAS/停止预留；新目标绑定或owner主记录/seal任一污染、规范JSON类型污染拒绝；旧记录/原app/Release/GoalCard保持ID和fp；源/目标owner ACCEPT不继承 |
| 原子故障与恢复 | head/version/binding双seal/回执的各写入故障全部回滚；新版本冲突无部分卡；PREPARE/DECIDE丢回复原key GET无POST；撤权/失效后metadata STOP/旧key历史仍可用且无内容泄漏 |
| 全段SQL屏障 | 复用并扩展SourcePrivate屏障保护原source和target GoalCard版本snapshot、生成轨迹、原Run/Release/approval/操作/typed/资源内容hash，从新目标创建到owner恢复/STOP的整个API+普通Worker+冷页面不求值旧private单元；源row保留撤权例同样需要 |
| 正常可见页面 | 真实TestClient HTTP HTML/CSS/JS与IPC JSDOM；完整目标编辑、scope预览/明确新建/修订、全项人工选择和reason、新Worker证据、ACCEPT/REJECT/STALE/停止/原key恢复；完整stderr/exit/SQL/资产proof，冻结前后逐文件fp一致 |
| 旧家族回归 | 仅直接相关旧generated-text owner、native GoalCard、newlogic/runtime/Release及普通worker API/IPC回归；不跑socket/native/旧取消case，测试模拟声明明确SIMULATED，不代签真实人 |

## 状态与边界

当前是设计审查，未执行测试，未签实现PASS。父纠正的计数采用373个git src/tests、另5个本地未提交egg-info=378本地；前轮32包含在41+2内，作者84PASS/1PGSKIP单列，不能累加成一次全绿，也不改旧raw/sealed证据。

本阶段没有工具或平台拒绝。没有测试、socket/native、真实模型/付费、凭据/权限变更、PG/Windows、CIForbidden、push、main/core/force操作或部署。此前精确安装竞态目标仍永久NOT_VERIFIED，不执行、实现或替代probe；既往范围误选及BrokenPipeUNKNOWN记录继续保留。真实人签收、完整P-A/P-B/F2-T01/T08业务闭合、语义和正式发布仍未验；本新目标仅显式人工声明工程链，semantic UNKNOWN、正式发布false。

## 父作者采纳后的执行目标规则（追加）

父作者已明确采纳第8项中更严格的新运行方案，故上文“仅在当前卡下人工复评既有结果”是曾审阅的较小备选，不是本轮采用合同。新logic已有自己的GoalCard时，RunInput必须显式提交精确`expected_owner_goal_binding_fingerprint`；enqueue与当前binding匹配后冻结自有card/version/fingerprint/binding/sequence。Worker准备与最终结果提交均核当前binding一致；创建或修订Goal之后，旧未绑定Run、旧卡版本Run及修改后排队Run不能成为当前Goal的签收证据。没有自有Goal的新logic仍保留原运行兼容路径。新Goal是人工目标和适用范围，实际literal执行的技术语义依然UNKNOWN，不声称自动完成目标业务含义。

必要边界：上述“必须当前”应用在enqueue、live Worker和owner.context所选证据；读取已完成历史的`load_binding`/`text_run_checks.verify_records`应校验其冻结ref及对应历史双seal、当前材料/logic授权，而不要求该ref等于当前head。否则同一实例先无Goal或旧Goal下成功，再建/修订Goal，即使新Run成功，实例读取也会被自己的旧技术历史阻断。2026-10-12追加只读看到作者已采用`verify_frozen_run`历史路径与`check_run`当前路径分离；源码仍未冻结，不能据此签实现PASS。

最低新增回归为：同一instance先无Goal成功→创建新Goal→带精确fp新Run成功→完整实例历史仍可GET→旧Run不可PREPARE；修订Goal→旧成功Run仍可技术GET、当前签收STALE→旧queued Run拒绝→新fp新Run可重新PREPARE。错、漏、别app、过期版本fp必须拒绝enqueue且0新Run；binding两seal及native版本必须核验。

当前只读另发现owner.base新家族契约未显式冻结当前platform limits；独立logic现有budget门仅在当前limits低于冻结cap时拒绝。因此预算变化但仍覆盖cap不会改变owner契约。若本轮要求当前budget变化也STALE，最小修复是在owner contract加入规范current limits/fingerprint；不宜直接纳入所有历史binding的anchor比较，以免无关预算变动令历史绑定和修订恢复不可读。此建议已发给父作者，留待冻结版本核验。

父作者另明确仅支持本轮当前软件创建的新logic对象；原233软件已mint authority因all-py软件指纹变化fail closed，旧源码升级NOT_RUN，不自动重签、迁移或声称兼容。旧证据README恢复233原bytes，373/378计数纠正只追加合同和新JSON，旧raw/sealed不改。作者告知初18项API/Worker通过属于作者结果；本独审本阶段执行数仍为0，没有独立测试PASS，也没有活动测试进程。
