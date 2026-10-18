# 当前关键产品路径只读分诊

基线 `304bff97584ac157d56597f5ab52ea7f5ecb1d9f`，开工 clean、/workspace 可用24GB。只读原V5、当前源码/测试和仓库已保存证据；没有运行产品、HTTP、Worker、模型、SQL或写仓库/旧sealed目录。未确认一个必须新增executor/Grant才能解决的普通用户源码功能缺口；以下首先是已有能力的完整页面资格缺口，不能包装成从未实现。

1. **按父级最新优先：当前 P-A 统一目录→v1显式合成人工DECIDE→未见THIRD输入→同实例v2→两Run回读/人工隔离，含一次真实可操作的错误输入。** 原V5计划:94/97/98/103/113、AT-11:341要求两路径分别验证未见与错误输入；产品:60/125/127要求使用/历史与独立结果。P-A per-use backend/API和历史完整page本来存在（PANaturalPerUse20261013.md:11、45–47；tests/test_pa_natural_uses.py:90–126；tests/pa_natural_uses_ui.cjs:22–51）。304bff之前新一轮完整页面只实际PB，不能以它代PA；其v1仅fixture PREPARE无DECIDE。当前价值是把真实页面v1逐项新声明、错误选择纠正、v2及旧声明STALE/新sequence0空账本串成一条可见链，复用现有控制器，不新增产品协议。

   **重要范围更正：材料/Goal不匹配不会POST到服务端，不可写actual409。** internal.js:1272–74独立两个下拉允许正常选错；:1279 GET选定Goal，:1280核唯一resource_snapshots.resource_id不匹配即显示“所选 Goal 必须明确引用本次材料”；:1283才是review POST。合法实际验收是选THIRD材料+SOURCE Goal→点击预览→可见错误、一次Goal GET、零review/run POST、全表不变/模型0；改选THIRD Goal继续正常预览/确认。不能篡DOM/请求绕过前端再冒充普通页面错误。若确需服务端错误，应另选正常可选但超2048B/40行的授权TXT/MD，UI仅format筛选(:1273)，natural_specs.py:88–97实际INVALID_INPUT，预期HTTP码应依现有映射核准，不凭空指定409；本轮优先不扩。

   显式使用ready(data,style='parallel'或'sequential')形成六步双模型；ready默认single(test_natural_spec_apps.py:247)，不能把默认单模型标成六步。前者正常generation3+v1模型2+v2模型2预计7Mock，按实际wire/claims计数。THIRD/Goal及全部fixture Grant先于页面PREPARE完成，v1 artifact派生READ也在PREPARE前完成，保留全项目grant_version门；不复发上轮夹具错误。页面owner PREPARE/每项ACCEPT及理由/ack/DECIDE是真实控件提交，但选择必须明确SIMULATED，不等同真人语义接受。新v2仍机器PENDING/UNKNOWN/不发布；旧接受ledger原字节保持并STALE。不重做下载/关闭/恢复矩阵。

2. **备选、现在暂停：P-B六步应用的首次局部逻辑修改完整页面链。** V5 F2-T07:99/113及产品§9.3:429–436。源码已支持共同的六步要求→条件依赖开关（natural_logic_patches.py:92–126/context:129–146；internal.js:1347–1367及1372后现有按钮）。历史NaturalSpecLocalLogic20261013.md:9/31的“PB未跑”不能独自代表当前状态：NaturalLogicSecondRevision20261014.md:25已有PB R0→R1→R2→冷材料 API/Worker1PASS755.856s，LogicVersionPerUse20261013.md:20–23已有PA/PB修改版新材料API/页面各通过。只剩明确区分的页面环：从PB原实例用可见控件做首次preview→隔离CHECK→独立同意新Release→新实例新输入。仓库旧归档author/test_visible_logic.py:23走PA prepared；R2 page author/test_visible_r2.py:13复用r2_fixture.opened:12–15的parallel PA种子；PB author/test_pb_second.py:16–40则API，不是PB修改page。因此属于重要已有能力完整page资格缺口，未证明功能实现坏。按父级最新steering不继续PB正例/不运行。

3. **剩余整体R0/F3承诺需要外部条件，当前不作通过。** V5计划:87前置Windows/真实书生链，:155要求两条实时真实任务；产品:234–257和目标环境条款不能由Linux SQLite/JSDOM/Mock替代。真实模型/语义评价、Windows/native、PostgreSQL角色/并发、远端CI/部署都保留未验；无本任务额外授权或现成条件，不推进被拒或永久取消窗口。没有建议为计数扩防重/回执/证据框架。

避免旧缺口误报：LogicVersionCorrection20261013/LogicCorrectionLease20261013的modified PB correction旧BLOCKED已被LogicCorrectionStage20261014:26–28、EffectiveScope20261014:9/16–25及HeartbeatRecovery20261014:19/27–38后续实际PB correction及PB页面通过收敛，仍保留历史FAIL，不应列作当前首要功能断点。local R2/修改版peruse也已经真实通过，不重新造。

所有判断均为只读定位，不是当前304bff运行资格。父级可据首项做一条fresh有界Mock完整page，实际失败时再定位最小产品修复。
