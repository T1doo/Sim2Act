# 下一产品缺口：项目任务历史打开自然成果时落入CSV渲染

基线：`2c21d278dbe0d46e05c4ba4cccd473a8edfa4716`。仅只读代码/Git/既有测试，本轮没有产品、HTTP、Worker、模型、SQL/DB、pytest/collect或网络操作；root仍唯一仓库写入者。全部此前sealed目录保持未写。

**本次只建议一个有确定源码路径的修复：让项目任务历史中的内部自然Run正确展示，并能明确回到同一应用/实例/Run成果与人工入口。** 已有应用页结果/owner能力要直接复用，不新增executor、Grant、API或恢复框架。

## 确定断点

普通用户在项目→任务历史→“查看任务”打开自己此前的自然P-A/P-B业务Run：

1. `src/sim2act/api.py:319` metadata_only历史查询列出本owner/project的所有Run，没有排除internal；`web/app.js:174`–`:177` 所有历史按钮调用showRun(x.id)。
2. `db.py:1399` inspect先owner/source_scope_gate，再通过is_app_job调`app_jobs.inspect_job`；`:608`之后仍完整鉴权/自然verify_job。其`:644`–`:671`返回namespace=`INTERNAL_APPRUN`，instance/release/app_run锚、结构化result、自然steps/markdown_view/UNKNOWN/PENDING。这里不是未经授权的stub路径。
3. `web/app.js:389`–`:391`却把**所有**INTERNAL_APPRUN统一显示为“内部工程只读任务 · 0 模型请求”，有result就按`column/sum/count`拼CSV汇总。自然result实际为resource_id/hash/checklist，四步文本result也不是CSV，所以会形成`undefined 合计 undefined，共 undefined 条记录`。自然模型节点真实有既有Mock/受限模型调用，通用回执也未提供任何能证明“模型请求0”的usage字段，不能按namespace硬填0。
4. 同一internal分支跳过renderOrdinaryOutcome，后续没有调用showInternalRun、specResult、owner或到原应用/实例的明确导航按钮。原始JSON details虽然仍在，不等于普通成果视图。用户只能自行切应用、重新找app/Release/实例/Run，项目历史的成果入口实际断开。`web/internal.js:703` specResult与showInternalRun/owner已有完整路径，不应复制另一个自然成果渲染器。

对应原V5：产品§2三工作区（`docs/sources/V5/平台产品设计.md:58`起）要求项目真实任务/成果画布、应用历史结果；§4共同条件要求新输入Run与历史结果区分；F2-T06（`docs/sources/V5/分阶段开发计划.md:98`）要求成果可回读。这个缺口是已实现能力的一个普通入口未接通，非“PB静态缺动态”或刚通过图/锁资格的重复任务。

## 最小建议

在showRun的internal结果分支按实际受鉴权回执处理：只有严格CSV结果结构才呈现column/sum/count；自然/四步等其它family不拼CSV字段，模型用量未有可信计数时展示未知/原记录，不能推定0。

新增一个明确“在应用中打开这次成果与人工验收”的只读动作，使用当前Run回执的instance/release/app_run/id，经现有实例GET得到并核source_app_id，再复用showApp/openSavedInternalUse→showInternalInstance→showInternalRun。读取和导航不新建实例/Run，也不自动PREPARE/DECIDE或下载。导航要在每个await后保持当前账号/项目/原Run选择与workspace/app generation，防旧回执把用户带回旧app。若当前权限或历史版本不再支持，应明确显示原原因并清旧内容，不反向从失败body恢复隐私或绕STALE门。

最小定向资格可用一条实际自然PA fixture：正常Mock生成/一个成功业务Run（复用已有normalWorker/fixture，不重跑图/锁/局部修改长链）→项目历史选此Run→无undefined与无硬填0→显式打开同app/instance/Run→实际成果入口及ownerPENDING相符，所有导航/GET业务表不变、0新Run/Worker/模型。可以有必要合成路由负例，但不要新起下载/关闭/恢复/旧故障矩阵。PB同namespace能力不等于本轮PB实际跑；精确报告范围。

## 已有与未执行范围

人工修正已有完整合同与页面按钮（owner-review.js:283起），以及`test_natural_spec_corrections.py` PA/PB后端normalWorker与`test_natural_spec_owner_ui.py`自然签收页面；不能仅因本轮没再跑就说未实现。兼容实例版本切换也已有renderSwitch/prepare/commit及lifecycle严格保留数据路径，不应凭印象重造。此前图/锁、PB完整局部修改、PA未见输入、PB v1/v2下载等已覆盖切片不重复。

本建议仍是静态triage，**未动态复现页面文字、未实现或测试PASS**。源码能确定分支/结果类型不匹配；是否还有更深路由问题需root在实施时核定。真实模型/真人语义/Windows/PG等外部验收条件仍不由本修复补齐，模型0授权边界保持。
