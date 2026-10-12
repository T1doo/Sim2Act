# 有限文本无旧内容逻辑复用实际证据

基线e2b856bb453fc74452583fa10843148758e2d9b9；3e890e329332d434e8f3aa245cb15f905bb41455亦已核为祖先。唯一产品作者root，独立审查仅/tmp，所有作者/独审测试结束后才编辑。独立开发分支dev/pb-text-logic-reuse-20261012。

最终有效执行，分别报告、不合并成一轮全套：

| 执行 | PASS | FAIL | SKIP | 证据 |
|---|---:|---:|---:|---|
| 作者候选8新主链/API/Worker/页面 | 32 | 0 | 0 | candidate8.xml/log + candidate8-pages |
| 作者候选7直接相关（产品src与8相同） | 84 | 0 | 1 PG | candidate7-related.xml/log + final-registered-pages |
| 独审候选8新32+另9独立污染/授权/seal校验 | 41 | 0 | 0 | independent/candidate8/final41.xml/log |
| 独审候选8纯目录 API/无socket synthesized DOM | 2 | 0 | 0 | independent/candidate8/catalog2.xml/log |

四个实际IPC TestClient HTTP/可见JSDOM场景：valid、authorization-lost、binding-lost、revoked-retained，每场两次boot，HTML/CSS/JS共40次读取、hash与实际源文件核对；新目标Gamma由fresh Store/NoModel普通Worker实际重算。source被删除或仅撤权保留时，原Run/生成Run、resource content/hash、source App candidate、Release/approval/binding snapshot、Operation/intents、AppRun/typed/instance history私有单元全段SQLite屏障0求值。它是对真实SQL单元求值的故障屏障，非字符串扫描或假worker。Node stderr/exit与全SQL记录保留。

实际有限上限第64写允许、第65拒绝且无部分写；精确证明/目标/请求、单边seal及JSON数值/布尔类型污染、跨owner、当前预算/撤销/过期、typed最终写后到期回滚、新Release索引插入故障整事务回滚均覆盖。owner PENDING、语义UNKNOWN、LIVE0、发布false。

历史错误与未完成范围逐项保留，见test-history-index.json、作者各candidate日志/XML与independent各candidate REVIEW/日志/XML。候选4作者误选10个socket旧UI，独审误选2个socket旧UI，实际OUT_OF_SCOPE_EXECUTED且不计验收；未重试这些路径。作者候选4额外回归44FAIL24PASS exit2，其中未设NODE_PATH导致模块缺失的原错不改写；后续仅明确允许的纯API/IPC页面。作者候选5相关74PASS后因已知主线修复中断exit2、候选6作者test变量遮蔽10PASS后中断exit2，都不是全套PASS。候选7独审两个BrokenPipe stderr当时未捕获、原因UNKNOWN，另两页虽DOM proof成功仍因CSS计数FAIL；不能借作者日志补签独审。候选8加入真实CSS及关闭前drain/完整stderr记录后独立重新41PASS。

changed ruff与Node语法PASS；全局ruff10/mypy5既有错误见final-global-ruff.log/final-mypy.log，不签全局绿。PostgreSQL/应用角色、Windows、原生浏览器、真实设备崩溃、真模型/付费、人工语义、完整旧源码升级、完整P-A/P-B/AT-10、部署/正式发布均NOT_RUN。此前取消的精确安装竞态对照永久NOT_VERIFIED；旧raw rejection与old sealed证据sha保持。远端CI不能由本地测试推出。
