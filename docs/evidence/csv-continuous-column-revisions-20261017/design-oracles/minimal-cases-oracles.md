# 连续CSV修订：最小独立验收与原件

只读核查基线 `ce3fa86677cdaa58e076cc03e15a9b5414fd1e77`，开始时clean。未写仓库、未更改Grant/模型、未创建Run或执行测试。以下是root实现后的验收建议。

## 当前实现/夹具与新缺口

- `tests/test_csv_goal_revisions.py:baseline/ready/start/approve` 已有同app、原Goal v1→v2、原CSV材料及独立CHECK→Release→原实例CAS链；`ready(prior=True)`有真实v1=30及合成ACCEPTED，可作为连续链起点。
- `test_adopt_without_drift_new_worker_result_and_new_run_pending` 已核首次Goal2 quantity=5、business result_version2、新Run PENDING、原v1=30保留；随后Goal3阻断旧头新工作及移除marker后重签的拒绝。它未实际完成第二次修订。
- `tests/csv_goal_revision.cjs` 已有真实HTTP/JSDOM动作及完整request/status/body：三确认前 `confirmationReturn`、CHECK实际202丢失、CAS实际200丢失、双击、项目/实例/账号迟到、服务器证明未受理后才新key。应在**第二轮**quantity→amount重用这些检查，不再另跑全部首轮故障矩阵。
- 当前产品 `csv_goal_revisions.context`拒绝带SOURCE Release，`effective`硬编码revision1→2，`calculate`只准Goal=origin+1；UI采用后只显示说明并保留旧adopted intent。这些都属于当前单次合同，新连续实现应基于经过验证的直接parent及新的显式意图。不能只移除前端禁用。

## 独立oracle与四种版本必须分开

固定输入来自现fixture：`amount,quantity\n10,2\n20,3\n`。独立oracle使用stdlib csv+Decimal解析原始CSV，不调用产品aggregate/preview/check或产品fingerprint来计算期望数值。amount精确30、quantity精确5、count2、source hash为原CSV UTF8 SHA256。

建议唯一正例API链把四种版本列表写入原件：

| 阶段 | Goal head | 有效规格manifest/action revision | 原business instance revision | business typed result version | 绑定列 / sum |
|---|---:|---:|---:|---:|---|
| 原v1 | 1 | 1 | 1 | 1 | amount / 30 |
| 首次修订完成 | 2 | 2 | 2 | 2 | quantity / 5 |
| **同Goal2连续修订** | **2** | **3** | **3** | **3** | **amount / 30** |
| 明确保存Goal3后下一修订 | **3** | **4** | **4** | **4** | quantity / 5 |

Goal版本不是规格、实例或result版本；Goal3不能被误记成已经占用的规格3。CHECK在独立隔离实例的result_version仍1，不计入business实例结果序列。

amount=30再次出现不能单靠数字证明新执行：v3执行Run/AppRun/operation id和request_key必须均为新值，Release是新id，typed version3关联新AppRun，CLAIMED原事件与操作回执可核查；不得把原v1=30当新执行缓存。Goal3再回quantity也同理。

## 最小唯一API cases

### A1：一条完整连续链（唯一正例，复用一个fixture）

1. `baseline`创建同Goal来源CSV app、Release1、实例1。正常NoModel Worker产business v1=30，通过已有csv-owner-review正常PREPARE/DECIDE写**明确合成**ACCEPTED。
2. 现有Goal2→quantity修订、独立CHECK真实运行、Release2保存、同实例CAS→revision2、business v2=5。再为v2写合成ACCEPTED；到此冻结v1/v2 Release、Run、AppRun、typed result、Operation及owner records/seals的原始行与序列化字段hash。
3. 不调用Goal PUT，重新显式开启修订。fresh GET context必须指向当前Release2、instance revision2、data_version2、Goal head仍2、当前有效规格revision2及quantity绑定；baseline_column必须quantity，目标amount。
4. 原API顺序不变：POST previews→明确ACK POST checks202→原Worker一次完成独立CHECK→GET checks PASS→POST version-approvals201→明确ACK POST `/api/internal/approvals/{id}/commit`200→POST adoption-approvals201→明确ACK POST原instance switch-approval commit200。
5. 采用后instance id/app/runtime均原值，Release3新id、规格revision3、instance revision3，Goal2 card/version/fp/历史行不变。此时采用本身不写business结果；明确POST新business Run input=amount，原NoModel Worker产生新v3=30，same-Run owner GET必须PENDING。v1/v2 ACCEPTED声明与ledger原字节/hash不变，不能继承为v3 ACCEPTED。
6. 继续明确PUT同Goal expected_version2保存Goal3；PUT前没有隐含Goal写。旧v1/v2/v3历史仍可读，旧Goal2新执行/新批准被拒。明确新预览才能把Goal3与列quantity绑定成下一规格4/实例4并实际产结果4=5；不自动重用之前CHECK/approval或静默更新Goal。
7. 关闭API/Store/进程，新进程/新Store只GET三/四份原Run、对应Release、business typed rows与owner合同；全库持久行不变，0Worker/0POST/0模型。新Run均初始PENDING；合成旧ACCEPTED没有变成真实人工语义验收。

不要用 `drive()` 的最多5次once作为成功兜底：在本链每次仅排队精确一条CHECK或business Run，执行一次Worker.once，断言目标SUCCEEDED、恰一CLAIMED/fence1；失败保留原件，不重放/换key求绿。现有NoModel.request明确拒绝模型；如驱动涉及其它发送入口也应以forbidden sentinel拒绝，Attempt数保持0。

### A2：父链/绑定损坏（一个负测，3–4代表参数，用A1较短已完成v2/v3历史）

每个变体只作用于该测试自有副本或可回滚事务，不重跑Worker；只读/预览/批准读取拒绝403/409或明确合同错误，不写新Release/实例/Run。无递归栈溢出、挂起或任意深度遍历。

- v3直接parent不存在/缺seal；不能回退原v1或当前business指针继续算。
- 将直接parent从Release2改为原Release1，或换成同app另一实例的合法链；**同时重算局部paired request/response/snapshot fp及可见Release fp**后仍拒绝，证明真正核独立parent/CHECK/approval锚，而非只靠局部hash自洽。
- 替换当前绑定列、Goal fp或effective candidate revision，并重签本地可变层；独立CHECK真实input/output proof、immediate parent和effective重构必须识别不符。
- 自引用或两节点环/跳过规格版本，若合同允许表达则有界拒绝；不存在parent字段时用对应实际source reference测试，不制造未支持schema绕路。

记录具体改动字段、修改前后raw/hash、哪些局部层已重签，以及被保留的独立原锚。仅改一个fingerprint导致通用hash mismatch不能冒称“重签父链攻击已验”。不要求伪造所有不变历史原件；恰应由独立原件拒绝。

### A3：当前权限/Goal/CAS（一个轻负测分阶段或3代表参数）

在同Goal2的第二轮已经checked后：

- 当前身份失去原材料读取权限或换外账号，请求当前context/preview/check/approval必须拒绝，旧私有Goal/提案不泄露。由root在自有fixture经既有正常API安排权限负例；本代理不改变Grant或策略。
- Goal head明确变3后，Goal2的新批准/采用/新Run拒绝；已冻结旧Release/结果历史仍在当前合法权限下可读。禁止用Goal head3重新解释旧Goal2合同。
- 检查后原business实例出现另一个实际结果或revision/Release已变，CAS拒绝且不会指向新Release；同一有效adoption approval并发两次commit最多一次真实切换，重复原件可恢复、revision不跳两次。另一实例不能消费这份adoption approval。

这三类原首轮已有覆盖，新节点只核它们对连续parent链仍生效；不重跑暂停/取消/故障恢复或全部lock矩阵。

## 最小页面cases（复用真实HTTP+NoModel CJS）

### U1：连续修订可发现 + 三确认前导航恢复（一个case合并三个阶段）

走可见目录进入已采用Release2的原business实例，明确开启新修订。不得仅显示“已采用Goal2”而无入口，也不得把旧adopted entry用于新请求。第二轮生成新request_key，同时保留旧key审计历史。当前原列应显示quantity，目标选amount；即便仍Goal2也应可明确预览。

按现 `confirmationReturn` 在第二轮的3个确认前各离开resources→返回apps一次：

1. CHECK ack前；2. Release commit ack前；3. CAS adoption ack前。

每次恢复完整冻结payload（context、原preview、check、release approval/Release、adoption approval及新增parent链），与服务器原件deep-equal。fresh GET context与原preview必须实际出现；Release阶段还GET原internal approval并检查未过期/未消费；adoption阶段GET原adoption preflight。parent/R2及当前I2/D2不变。三ACK全部清空，按钮不自动提交，from/to锁定冻结quantity→amount，导航过程0POST；重新明确勾选后才只提交一次下一步。

采用后UI提示规格revision3/实例revision3/Goal2，use-column仅amount；明确新Run显示真实30和新Run id；same-Run人工入口PENDING且不残留旧ACCEPTED。Goal3可见编辑/保存仍明确触发，可在同case尾仅确认PUT与新context，不必另开第二份页面Worker链（完整Goal3实际结果在A1验证）。

### U2：UNKNOWN原键恢复 + 双击（一个case，不分别重跑全故障矩阵）

第二轮选两处最关键真实成功丢响应：CHECK202、CAS commit200。服务端实际受理回执先保存到raw，随后驱动抛传输丢失；UNKNOWN禁新key/新POST/重置。导航回来仅GET对应原key、原approval/原instance history，精确确认原preview fp/Run/parent/R2→R3 switch历史。

双click只产生一次实际CHECK；CAS未知恢复也只有一次commit POST，I2→I3一次，business新Run只一次。原key恢复得到相同已受理效果；不同body同key冲突。只有服务器明确NOT_ACCEPTED/TX_ROLLED_BACK才允许可见“重新准备”新key，网络错误本身不允许。

### U3：账号/项目/实例迟到隔离（不需新Worker）

复用已有 `navigation` 场景结构，在第二轮GET context/preview/approval或已受理回执读取延迟时切换项目、instance2、账号A→B→A；释放旧响应后不得回填原proof、勾选ACK、替换新选实例或发起原项目追加GET。返回原同owner实例时fresh GET并重新验证，不用旧generation视为当前。可与U1/U2同fixture阶段或轻量production-script probe执行，不额外造业务Run。

## 必须证据：以业务实例过滤，避免CHECK混入

- 精确源码SHA、实际产品JS资源SHA、NoModel实现、执行nodeid/case和真实范围。
- 每步HTTP完整method/path/request/status/response（包括模拟丢失的真实202/200）、可见DOM动作、三阶段导航前后完整proof JSON、ACK/disabled状态、新GET与POST计数。
- 四计数状态表Goal/spec/instance/result以及独立CSV oracle源字节/sha/计算结果。spec revision从已验证effective definition读取；app_drafts原始generation候选继续不变，不要用draft.manifest.revision冒充effective revision。
- 每Run执行Run id、AppRun id、CHECK隔离instance id、business instance id、Release id、parent id/fp、preview/check/approval key及其fp，单CLAIMED原事件和新Operation id。
- v1/v2的Release snapshot、run_contract、Run context/result、AppRun output、typed result、csv_owner_records/seals、各自ACCEPTED ledger，及原app draft/generation记录：保留完整行比较和**数据库原序列化JSON文本UTF8 bytes SHA256**。SQLite可driver-level SELECT原JSON列取得text，不经SQLAlchemy JSON反序列化再canonicalize；同时保存标量字段。不要把此称整个SQLite文件字节不变。
- 旧owner合成ACCEPTED在所有新CHECK/采用/Run后raw/hash不变；新Run没有owner record/seal且PENDING。只比较最新owner状态字符串不够。
- 关闭前与cold新进程前/后全库行/hash、GET列表、0POST/Worker/model证明。初次CHECK proof懒生成如已有合同，应在冻结基线前读完；不能把冷页首次补写收据冒称零写。
- 负例单独记录测试自有篡改/重签方案、拒绝原回执、无新增业务effects计数，不把负例DB篡改混进正例“旧行未改”结论。

不新增executor、费用模型、Grant策略或真实语义承诺；不重跑无关PA/PB/锁/恢复大矩阵。未实际执行的新cases保持NOT_RUN，后续按冻结SHA审原始回执。
