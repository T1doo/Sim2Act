# P-A 受控书生适配：执行证据

基线 `a4fd476127a477006dbdb29a9a1f6c2f09e6a001`，独立分支 `dev/pa-intern-provider-20261012`。合同见[PAInternProvider20261012](../../F2/PAInternProvider20261012.md)。原owner草案仍在原工作树，原source/草案hash见[source-protection](source-protection.json)，未复制进本片。

## 已结束的 r4 冻结

422 src/tests 文件（71 PY包含config，70实现PY排config）map SHA `6732ed8db8b7040fbd2c5c103547486881c4e75fd4e4ec79e0d638fc111a43d9`，完整源码快照留在保存环境 `/tmp/pa-intern-provider-20261012/frozen-final-candidate`。本目录的 `candidate-r4-source-map.json` 与原map同字节。源码/所有20个页面资产均纳入；目前独审前后0diff。

- 作者 final-r4：41PASS/0FAIL/0ERROR/0SKIP，229.32秒；25 provider、12 typed material binding、4实际TestClient/IPC/JSDOM页面。先前37后端通过属于combined-r1，不能改写为r4全跑。
- 独立复跑：41PASS/0FAIL/0ERROR/0SKIP，271.98秒，与作者重叠；额外12独立fault PASS、24.13秒，合计53唯一节点，不与作者相加。1实际屏障校准＋11产品反例；校准内12故意SQL拒绝不是12额外pytest节点。
- 4页面144检查（34/34/38/38），全部资产经实际HTTP读200/hash核对；可见native DOM事件操作、编辑historyUndo、未知POST原key GET、单次精确提交与冷Store NoModel Worker的新材料结果。JSDOM不是原生浏览器，模拟事件不是人工验收。

独审启测前曾遇原exec-server transport disconnected，全文保全。停止原失败读取；原环境/原工具的新轻量核验成功且source map0diff后，继续已授权测试，未重复原失败读取动作。无权限/安全审批拒绝原因被删去；旧浏览器/Forbidden CI/已取消窗口仍不重试。

## 原失败历史（不覆盖）

- provider-r1 12PASS/3FAIL：2个测试误试SQLite production初始化、1个全局patch误拦TestClient。生产适配测试改为明确SimulatedProductionPolicyStore façade，不改实际Store.test_only或Production bootstrap；局部AsyncClient Mock注入无外部发送。
- provider-r2 14PASS/1FAIL：默认关闭HTTP码夹具期望错误，实为RESOURCE_UNAVAILABLE/400；修期望，没有改API状态语义。
- provider-review-red 6FAIL：发送器构造后配置撤销/凭据替换五例到达合成sender、已封存响应与最终失败错误更新冲突一例；实际产品缺口，修复后provider-r3 21PASS。
- material-r1 12PASS。
- combined-r1 37PASS/4FAIL：页面夹具在精确批准之后新建资源/授权，改变冻结Grant指纹导致批准列表为空；材料准备移到批准之前。
- ui-r2 4FAIL：真实新材料应用保存后，页面来源说明仍读取缺失的原goal_application字段而无法打开。补独立模型图绑定来源分支。
- ui-r3 3PASS/1FAIL：迟到保存被拦后只读恢复仍disabled。修安全controls刷新；新的显式GET操作重新冻结当前读取上下文，旧回应继续失效。
- legacy-red 1FAIL：现API对普通路线传可选None keyword，旧legacy archive helper不接kwargs，TypeError；未表现为旧库读取或权限FAIL。r4大回归亦复现；r5后续修复及实际通过另列，不覆盖原失败。

logs/XML原字节保留。219份已终止的合成fixture SQLite以无损gzip保存，解压原SHA与压缩SHA见[archive-map](author/database-archives/archive-map.json)。combined-r1源码map在运行中拍下、期间无编辑至终态；更早部分测试版本没有独立全树pre/post快照，不声称完整逐文件冻结覆盖。

## 实际出站包与费用提案

[合成请求原字节及计划](synthetic-outbound/plan-and-archive.json)：两请求有效例为16488、17203 UTF-8 bytes；三请求修订例再加22802 bytes，总保守预留59565（每次输出上限1024），均≤批准64000。完整有效候选4662 UTF-8 bytes；实模型1024输出tokens可能截断，合成usage不能证明真实token成本或成功率。

这些包只含合成Goal、明确ID/hash/schema、获批材料实际读取反馈与候选/诊断；无真实账号Authorization header。它们是OFFLINE_TEST原例，没有LIVE授权。当前真实请求0、费用0；未来拟intern-s2、同一固定endpoint、≤3请求/1读/1修订/300秒/RPM1。当前单价、账号额度、货币硬封顶NOT_VERIFIED，费用估算NOT_ESTABLISHED，不自动扩大预算或配置凭据。

## 当前限定

生产形状验证只是SQLite测试façade和本地MockTransport。真实书生/付费模型、PG/角色、Windows、原生浏览器、实际旧源码/旧库升级、人工语义/客户业务、完整P-A/P-B、正式发布、部署、远端CI均NOT_RUN。源模型图复用不产生新的模型请求，目标由人明确绑定，源仍需当前审计授权；不宣称模型理解新目标或无旧源内容授权。

r4的53PASS与相邻大回归分别计数；两处有限修复及r5最终证据列于下节，不能把r4通过数当成完整项目资格。

## 最终候选r5

422文件map SHA `671955ea8cff8da3c84dde2cc3a7de8c3bdf373180cf58c1222284ffb2773ad7`，70实现PY FP `44dc40ab98fdafd8dc0928e17fa599a8df8e20e696bf1dbc570702f7e6ed05c7`。r4→r5只变api.py与pa_material_bindings.py，其余420原字节相同；[逐文件桥证](r4-r5-byte-bridge.json)。普通路线不传None可选关键字，保留原4-pos工厂接口；P-A分类器用namespace/task kind/pa_binding.kind三个投影判族，不在无关CSV撤权前探完整回执表。未改原测试或旧软件白名单。

作者当前56PASS/0FAIL/0ERROR/0SKIP、264.73秒：41新片＋14拒绝响应与旧形状历史整文件＋1确切CSV撤权/原来源只读。原两个实际失败各已在当前候选重验通过。独审当前68唯一PASS/0FAIL/ERROR/SKIP（56与作者重叠＋12独立fault），56节点228.94秒、12节点27.85秒；报告另附。4UI144检查/160资产loads，20资产每次HTTP实际哈希一致；pre/post422零diff。全树ruff原10错误未修，改动ruff通过；新mypy5错误已修，当前仅既有status_report/tools的5基线错误。

完整相邻r4回归为675唯一=587PASS/84FAIL/4SKIP，2453.43秒，源码归属r4，不声称r5全仓重跑。84FAIL精确：legacy None keyword1、无关CSV撤权前ledger查询1（r5修复且实验PASS），text_continuations46与boundaries36共82（仍为实际兼容门FAIL，r5未重跑）。4SKIP的PG节点及完整失败信息见[分类](author/broad-r1-failure-classification.json)。两个旧锚实际只读known检查均CLOSED_REJECTION；新增两模块及contracts/db/goal_applications/text_apps/worker的变化不在允许集合，anchor与CHANGED原字节/集合不变。支持性检查不计pytestPASS。旧版本续用资格仍阻塞，不改标SKIP或baseline绿，也不借新切片掩盖。

r4独审53及完整报告原字节仍保留；r5独审另外封存。源码修改及最终测试均已结束后才正常commit/push；精确最终Git SHA/远端核验在交付回执中记录。没有远端CI资格声明。

最终r5独审[报告](independent-r5/FINAL_REVIEW.md) SHA `07a882a36fa461336422971b00097997d8ebe845d3efdaa1d91ed55c6d268a72`；[原manifest](independent-r5/manifest.json) SHA `1b471b804753f1cd8a3aa7702dc0d39345e159c9ee55f05ad42abb772df919a1`，114件逐字节核对归档。结构化[最终限定](final-qualification.json)分别记录作者、独审及旧扩验，不把重叠节点相加。

产品src/tests与本轮F2文档的暂存差异空白检查通过。全暂存检查因原始pytest失败日志/XML及历史diff中的空白返回2；这些原始证据保留原字节，不为通过格式检查改写。
