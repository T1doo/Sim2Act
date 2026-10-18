# P-B 首次局部逻辑修改完整页面：只读合同预审

基线 `e73004e3529ebfdc27e0105a33f888dbcf042543`，核读时HEAD一致且clean。本目录新建，与全部旧sealed目录分离。只读源码、原规格与既有验收记录；产品/HTTP/Worker/模型/SQL/网络执行均0。未发现须新增产品能力的确定断点，先按test-only接通实际页面资格，尚无当前PASS。

原规范：V5《平台产品设计》§9.3:429–436要求冻结基线、类型影响/失效传播、保留无关ID/内容、未知扩大重验、人工锁冲突、先检查后新Release；§9.4:442–446要求独立应变/保留集且不得将全量改写叫增量。V5《分阶段开发计划》F2-T07:99、F2-T08:100、分别入口:103、验收边界:113–115、AT-13:343（AT-14/15:344–345）。本条实际正向只覆盖既有有限依赖开关，不重新验完整AT-13/14/15或加入锁/恢复/撤权矩阵。

历史能力不能重造：NaturalSpecLocalLogic20261013.md:7–11实现六步requirements→qualifiers的prior_items/prior_feedback及depends_on开关；该期完整page为PA(:9/31/39)。NaturalLogicSecondRevision20261014.md:25已有PB R0→R1→R2→冷新材料 API/Worker实际1PASS；LogicVersionPerUse20261013.md:20–23已有PA/PB修改版本新资料与页面通过。前次只读回读仓库归档也确认首次local page是PA prepared，R2 page是PA parallel种子，PB两修改case走API。当前缺口是**P-B首次局部调整从原实例进入CHECK、批准、commit、新实例与新材料的连续普通页面资格**，不是PB后端/修改版per-use从未实现；不借旧PASS为当前代码运行背书。

## 最小页面差异与 oracle

1. 用正常成功任务、显式提取形成真实task来源PB六步parallel原始candidate与Release/实例；不能伪造PB标记或以PA同款手工清单替代。原qualifiers无prior_items/prior_feedback，页面明确选true，预览采用同app/action/step稳定ID。独立按原candidate重建变更：qualifiers增加两个端口与first model依赖，manifest/action_bindings/该action revision2；其余五个action定义逐字保持。APP未知扩验不能误写成确定局部只验一节点，也不能把五个action定义保留混称图retained_objects（其集合可为空）。
2. 页面preview只建立原协议proposal元数据，不启动模型/新Release/业务typed；单独check ack/按钮才排队。CHECK在与原PB实例不同的隔离实例，仍精确绑定旧Release，执行普通Worker六步骤及两模型并取得完整实际readback。单纯once返回True或PREVIEW hash不是CHECK PASS；第一次未通过完整CHECK时不得批准新Release。
3. CHECK PASS不自动发新版本；独立version ack→version-approvals→完整snapshot/check/source指纹再读→再次明确ack→commit。新Release id/fingerprint与旧版不同，原snapshot.draft逐字保留，natural_logic_source只封印精确preview/check/execution digest。原PB实例继续旧Release/data_version不变，不自动切换。
4. 从页面内部历史**明确选择新Release并新建实例**，核新实例Release精确匹配、data_version0；选择预存THIRD/匹配Goal→普通per-use preview和单独同意→正常Worker两模型，成果typed **result_version1**、data_version1。不要叫结果v2：revision2属于逻辑/manifest，新实例首成果属于version1。核actual两模型wire只有THIRD且second prior_items/prior_feedback确来自该Run first输出；CHECK输入应为PB自身COLD绑定而非原来源任务SOURCE。正常结果PENDING/UNKNOWN/NOT_RUN，不发布，不把机器出处PASS升格语义接受。
5. 完整来源source Run/AppRun/typed/原PB draft/旧Release/实例指针、Goal/材料及原history保持。若fixture原PB实例未执行业务Run、data_version0，则只称其未污染/指针不变，不可声称保留了并不存在的PB v1 typed成果。只有fixture实际先生成该PB结果时，才可主张其具体typed/artifact历史保留。

## 风险与有界建议

- 新THIRD材料/Goal及其全部正常授权应在graph derive和preview前保存，之后不额外写目标配置，避免冻结context因新增资源/授权失效。CHECK保存自身artifact带来的既有派生READ按当前合同处理，不编辑旧grant_version或扩大权限。
- `tests/test_natural_result_navigation_ui.py.once`是single专用，硬断言每次wire+1，不能原样给本链CHECK/新Run两个模型。复用正常Worker/guard/claim/clock但每阶段期望2；不扩lease/deadline/预算、不强制时间或修复运行状态。generation与真实来源任务的Mock按当前fixture实际wire分列，不先猜总分母。
- `parallel`只表示两个模型间无声明前序DATA边，不是同时网络并行承诺；本轮页面true依赖是sequential模型输入关系。
- 原backend关键点：natural_logic_patches.effective:92–126、context:129–146、preview:211–225、checked:283–309、propose_version_tx:397–414。UI openNaturalLogic:1347–1367按6步显示；naturalLogicWrite/Render与按钮:1413–1451保留原scope/key/current/双ack、当前hash/Goal/权限/版本门。新测试不能通过直接赋naturalLogicView、硬显示控件或改后端body替代页面手势。
- 不运行第二次patch、版本采用老实例、恢复/回执丢失/late窗口、下载、权限故障或人工锁矩阵；无必要生产改动则保持0生产diff。原已取消精确安装窗口与原私有诊断拒绝不重试。Windows/native/PG/真实模型/语义/正式发布/远端CI仍不因此验收。

后续先审具体draft/冻结字节，再读闭合实际原件作一次有限独审。当前不预写PASS、不提前seal。
