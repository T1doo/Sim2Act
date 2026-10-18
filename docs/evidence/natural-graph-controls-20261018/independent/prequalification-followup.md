# 同一 case 的预审补核

结论：**前述 Python 元数据白名单 P2 证据缺口已收敛；当前已读 Python 与 CJS 未发现阻止冻结并执行一次 PA actual 的具体问题。** 这只是非作者静态预审，尚无本轮实际测试 PASS。本轮只 PA 页面，不声称新增 PB actual 场景或完整 first-guide/局部逻辑长链资格。

`exact_graph_metadata` 现在把7个实际页面 POST约束为11条精确 journal header：3derive、2canonical lock、2组manual pair/seal、成功preview pair/seal；每条 principal、原 request/response、request fingerprint、snapshot fingerprint均校验，LOCK_CONFLICT请求key不得出现在新增journal。3个anchor revision1/2/3、原graph/sourceVersion、fingerprint、唯一目标app/project/principal/runtime state指末anchor、sourceVersion集合/revision/definitionFP和最终unlock回执锁均收窄；原metadata行保持，其它50表全等。它能排除上一版允许任意metadata附带写入的问题，无需新增case。原后端记账种类与数量也已只读核对，不是凭数猜测。

CJS逐段审查确认：从实际GET index、CSS、25个生产script构造JSDOM，全部fetch限定owned loopback；使用普通token连接/目录选择/实例选择，开页和正常缺graph GET没有POST，预期409明确证明fixture未预派生。随后通过可见可用控件和独立确认触发3derive、lock/unlock、LOCK_CONFLICT预览及成功预览，真实请求/响应JSON、字节SHA和增量jsonl均保存；derive与lock双击仍只发一次POST。当前控件消耗production提供的上下文，未直调API制造图或锁，未改业务clock/budget/Worker。

每次锁/解锁后清旧graph证明、读当前lock revision、重新derive；成功preview校canonical fingerprint、graph与instance绑定、PENDING/UNKNOWN，仍不能未确认CHECK。脚本限定所有POST为derive/manual-locks/preview；没有CHECK、Run、version approval或commit。正常projects→apps roundtrip后主动GET图，应验证自然入口未留下开页临时callback的永久false围栏；该行为仍待实际执行确认。原app/Release/空实例随后重新读取与初始对象相等。CSV列/DAG控件保持隐藏。finally会核清owned HTTP/handler、错误时维持FAIL并保存results，不会仅因生成finally而记PASS。

两处生产接线的前次结论不变：post-openInternal完整选择复核后才打开严格自然namespace图，不自动derive；manualOpen复用已支持自然PA/PB的后端，CSV/Report条件保留，无新API/executor/Grant/Principal。通用图控制使用现有identity/project/appGeneration/epoch，开页临时fence不被永久绑定，允许后续workspace handoff。没有要求放宽后端权限/版本/锁门或泛改其它family。

此处未运行CJS、产品、pytest/collect、HTTP/Worker、模型、SQL、网络，也未打开数据库。仅用标准库ast.parse检查Python可解析并核对采纳CJS字节；该语法检查不能替代root静态门或实际资格。

读取字节：

- `src/sim2act/web/app.js`：125060 bytes，SHA256 `70cd470333fee58d76ab12232f4184e96be236291ac07071991fda48659139c0`。
- `src/sim2act/web/manual-locks.js`：6177 bytes，SHA256 `a03a9638f6c0ce9dc78ee05ddf14d109ec92e2222ed054bfeed5ed08bc95034b`。
- `tests/test_natural_graph_controls_ui.py`：10919 bytes，SHA256 `ee2a6e8e8273f71b5c22d1d99798d7ea68799aa065b374e818c40f383db47ee7`。
- `tests/natural_graph_controls_ui.cjs`：21630 bytes，SHA256 `b2de550927d08bb51a7e14af8fbc7fdd3e211b1a13691ae6bb3cee1a3a9b34e1`。

本目录继续未封存；冻结字节及闭合原件到达后再作有限最终独审。
