# 自然应用人工Run选择与运行详情反向接线缺口

结论：**确认一项值得立即最小修复的真实用户功能缺口**，而非仅缺资格：自然P-A/P-B人工Run下拉选择不会同步该Run的运行详情。未找到比它更高价值、已证实且需立即实施的第二项；不要为满足数量新造功能。

基线实读0a0430223be5bf27d8dc72ee33a4a479bfd92fdc。本轮未执行产品/HTTP/Worker/模型，未改repo，未触任何旧sealed目录。精确读取hash见source-readback.json；以下用户复现路径为源码推导，不冒实际执行。

## 具体断点

- owner-review.js:123–132冷打开owner面板，列出成功Run，但engineering.run仍可为空。
- :197–200的owner-run.onchange只有view.workflow分支调用showInternalRun；自然view.spec走selectOwnerRun。后者:182–195只修改owner下拉/rid/state/evidence，不写engineering.run或internal-run-detail。
- 因此用户冷页选B可读B人工合同却没有B运行详情；若之前历史选A，改人工下拉到B则机器详情仍A，人工证据/标准却B。同一屏两个Run不一致，用户还需另找历史条目手工同步。
- 正向已实现：internal.js:703–743结果卡/历史条目调用showInternalRun，:388再绑定owner；use.js:59–63统一目录自然家族入口也已接好。这些不需要重造。

## 最小修复与安全判断

将onchange的view.workflow条件拓展为(view.workflow||view.spec)，保留id非空、ownerCurrent及当前engineering.run.id比较；直接复用showInternalRun。没有新API/executor/Grant或后端放宽。

无事件递归：showInternalRun:388调用selectOwnerRun，后者赋select.value不派发change；:341先清旧owner，:337–340保留run/instance/identity/workspace代际，当前Run读取后才新owner读取。只有跨终态读的既有:383–386刷新链，刷新后previousStatus为空终止，不是新循环。ownerPending/correctionPending按原Run保留，切换不得删除未知请求、自动重POST或迁移人工选择。

**旧v1仍必须STALE。** owner_acceptance.py:720–725要求所选result等于当前data_version且无inflight。修UI只同步历史机器详情，不能为让旧Run人工正文可见放宽门；最新RunPENDING/ACCEPTED按本Run独立账本，新结果不继承旧声明。

## 既有测试与最小新验收

natural_application_entry.cjs:52–58、natural_input_preparation和PB完整flow主要历史按钮→Run→owner正向。pa_natural_uses_ui.cjs:42确实会edit owner-run，但43–51只核owner合同/状态及版本列表，没有核engineering.run/internal-run-detail；所以该缺口不是“动作从未测”，而是选择后的机器详情漏接未被oracle捕获。workflow旧onchange行为应保留。

最小合成实际HTTP/JSDOM资格按PA/PB两参数复用已有normalWorker/Mock成功历史fixture：冷统一目录→选实例→从人工下拉直接选当前B，证明engineering.run、详情JSON、owner-rid/contract、材料Goal/version都B且仅GET；再历史A→人工下拉B，证明原A机器详情被B替换。选旧A仍显示A机器详情且旧owner STALE/无旧声明继承；返回当前B不恢复旧choices。对一处实际Run GET或owner GET投递后导航/改选保留现有current/generation隔离，GET不产生Run/Operation/Grant；旧未知人工pending不被切换清除。无需完整再走P-B提取安装、关闭流程或相邻恢复矩阵，真实模型0。

原方案：V5产品60–65行每次运行历史/按需详情、125–127行新输入新Run与历史不能冒当前；阶段计划97–98行F2-T05统一入口和F2-T06成果可回读。此UI修复不关闭真实语义、Windows/native、PG/CI、正式发布门。旧取消安装窗口、exit139Unknown和旧满盘独审缺证保持。
