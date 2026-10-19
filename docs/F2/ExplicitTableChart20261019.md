# 显式表格图表 v1

接续 `2deea01b4ca879a84dbbbeab65102fc4ecfb6976`，原14本地提交保留，不访问远端。原产品设计 §3.2 F05（第88行）明确要求“受控文本/表格/简单图表视图”，§3.3（第103行）要求“文本/表格/图表展示”；V5来源同文，分阶段计划96/98行将其归于F2-T04/T06。不是新增业务producer或下载格式。

实施前合同：

1. 在已有、严格验证的同型封闭表格成果旁提供“横向条形图 v1”。当前接入已经支持原清单视图的确定性文本/离线文本成果；实际既有表为citations，字段quote/start_line/end_line。数值坐标仍仅称原字段名，不解释为业务量。其他家族专用成果不提升为通用图表支持。
2. 类别列和单一数值系列均无默认选择。用户只能从当前schema真实列中明确选取；系列限integer/number且每个值是有界有限数。单位显示“未指定”，不推断单位/时间/趋势；不读取自由文本单位。仅显式点击“重新核对并显示条形图”生成展示；改变选择立刻移除旧图，既不训练也不提交业务Run。
3. 复用原表格限制（64行/16列、严格required和additionalProperties=false、有限scalar、262144单元上限）。拒不存在列、非数值系列、空表、缺值、null、非有限数、超过安全数值范围和无法表示比例的值；不转字符串为数、不插值、不补值、不聚合、不重排、不连线。每行一条，零为明确图形基线，按原数据顺序。保留原表格/JSON与原值文字；SVG仅计算展示比例，不改结果。
4. 展示合同为`table-bar.v1`，显示原Run/Release/结果版本、结果字段、类别字段、系列字段及单位未指定。选择仅存在于当前页面组件；重新打开历史Run后仍须明确选择。历史成果读自己原Release，不能用当前草案替代。不是对未知旧chart声明的自动解释；chart输入也必须满足同一表形及绑定才能提供选择器。
5. 原结果入口已验证Release和typed指纹。显式作图再fresh/no-store GET同Run及原Release，核项目/实例/Run/AppRun/版本/Release/typed/result与原清单一致，重新验证指纹。沿用原鉴权与账号/连接/项目/工作区/应用/实例/Run选择代次；更改列选择有独立代次，迟到回调不得出现图。期间禁用按钮、同成果共享in-flight锁，失败后可明确重试；403清空受保护内容。
6. 合成合法生成→原Worker→实际HTTP→完整页面DOM验至少一个条形图、切换系列/不重复请求、原字段标签与数值、空表/非数值/不存在字段拒绝、历史原Release、冷页面重开、迟到回调与实际撤权拒绝。所有页面动作GET；55表前后全等，fixture撤权单列。真实模型0，无新executor/Grant/API/表。JSDOM/SVG结构与数值证明不等于原生浏览器视觉验收。

以上为实施前合同，原件保存于本轮证据包的`contract-before-implementation.md`。

## 使用与实际资格

在统一应用目录打开已有确定性文本应用与实例，在某条历史成果的表格旁选择“类别列”和“数值系列”，点击“重新核对并显示条形图”。两项均无默认选择；可选`quote`与`start_line`等真实字段，轴名称保持原字段，不赋业务含义。单位显示未指定，图注列明table-bar.v1、Run、原Release、结果版本和结果字段。换列立即移除旧图，须再次明确点击；重开历史成果亦须重新选列。原表格和原JSON继续可读。

当前有限支持有界封闭同型表格及一个数值系列的横向条形图。图形零基线不是新增结果行；每条原记录独立保留，重复类别不聚合。过小非零值若在实际SVG坐标中舍入成零，明确拒绝作图；负数/全零域有独立合成展示检查。输入为标量、缺值、数值字符串或其他未知chart形状仍不支持，不声称自动解释任意Manifest.chart。

实际运行使用新wheel安装包：960382字节，SHA256 `bdd222e96b37be35c33a309c86f4bd33aec4505a628775d9eb89327e1a9ef3fe`。141包文件与源/安装一致，仅`internal.js`和`app.css`较前包变化，112个Python文件未变；最终189项输入与冻结副本一致。94个已导入产品模块全部来自该安装包。现有setuptools84离线构建，固定82.0.1构建未运行。

共有3个唯一pytest节点取得通过，保存5次执行为3P/2F，不能称单批3P0F：

- 首批590.965秒，2P1F：display通过142.862秒（32页面检查、44 loopback页面GET、54资产、4图、2次DOM启动）；原text/table完整回归通过253.198秒（46检查、50 ASGI页面GET、54资产、2次DOM启动）。guard191.934秒失败：驱动100秒总watchdog超时，随后10秒收尾断言遮蔽主异常；4图保留，但原最终结果/Worker/HTTP观察文件未落，不补称恢复。
- 仅修测试记录/收尾及guard总watchdog100→240秒，普通UI等待15秒和业务断言不变。guard续验仍失败164.821秒（批次165.353秒），37检查、5图和55表全等已保存；错误在测试用撤权POST漏JSON正文，被原严格JSON中间件400拒绝，未进入Grant撤权。该400正文当时未存，不补造具体errorcode。
- 仅补同一个fixture POST的JSON头/`{}`正文及其响应日志，最终guard通过219.284秒（批次219.560秒）：40检查、41 loopback页面GET、27资产、5图，服务器正常停止。真实原Grant API撤权200之后原Run GET403，保护的表格、图表和控件清空。其余场景及产品字节未变。

首批两个PASS未因纯测试修正重跑；原两FAIL不改签。页面检查为断言记录，重复数值/图注检查不算独立测试；页面GET、资产、fixture TestClient和ASGI记录分列。原回归119条ASGI记录包含其夹具、页面及资产，不能另加为119次页面请求。3个通过场景共12个已捕获fixture Worker（3次MockTransport生成、9次NoModel业务运行），各领取一次/fence1；页面本身0 Worker/POST。全部5次执行保存10份合成provider请求，真实模型调用0。

通过场景捕获9份实际图形DOM快照，逐行数值及SVG几何与原Run重算一致；它们是JSDOM的outerHTML记录，扩展名虽为`.svg`，并非独立XML导出或原生视觉验收。一项纯文件观察器曾错误用XML解析HTML属性而失败，脚本/log保留；改用HTMLParser读取原快照后通过，未修改图形、产品或原始文件。负数、全零、重复类别及非法数值反例明确为展示函数合成输入，不冒充实际producer数据。

55表全行快照中，display和原回归前后全等；最终guard仅原fixture撤权修改一个READ Grant的revoked和revision，其余54表与其他Grant原样。改系列、工作区往返及切实例后的实际迟到200均未回填图形，工作区返回后新的明确点击仍可用；错误typed/历史Release反例标注为实际HTTP200后合成污染，不是服务端拒绝。账户/项目/重连等旧完整矩阵未重跑。Ruff与Node语法检查通过；未改Python运行代码，未重跑mypy。

[原件说明](../evidence/explicit-table-chart-20261019/README.md)、[首批JUnit](../evidence/explicit-table-chart-20261019/qualified-installed.xml)、[失败续验](../evidence/explicit-table-chart-20261019/guard-followup.xml)、[最终guard](../evidence/explicit-table-chart-20261019/guard-final.xml)、[逐文件核验](../evidence/explicit-table-chart-20261019/closed-verification.json)、[完整原件](../evidence/explicit-table-chart-20261019/author-raw.tar.gz)随提交保留。作者封存manifest SHA256 `ce00537bc3c7a5bbaa737d29e6c1a57cd4c603b8203decbd42823c4c995c5561`。

[有限独审](../evidence/explicit-table-chart-20261019/final-independent-review.md)结论为`LIMITED_PASS_EXPLICIT_TABLE_BAR_V1`，未发现本片剩余确定P1/P2；[机器核验](../evidence/explicit-table-chart-20261019/final-verification.json)与[完整独审原件](../evidence/explicit-table-chart-20261019/review-raw.tar.gz)一并保留。独审封存34文件、162852字节，清单SHA256 `d3e97bcc4d1778a5b7a6418601784f60388528ce37f064ff603e01f453c627c2`。独审逐SHA核918个非DB原件，23个DB文件仅stat，不声称独立重算DB。

Windows/PG/原生浏览器视觉及文件保存/远端CI/真实模型/正式发布未验，语义UNKNOWN、人工PENDING；旧满盘独审缺失不恢复。14个原本地提交保留，本轮无远端/auth探测或推送，当前远端HEAD/差异UNKNOWN。此项仅关闭有限显式表格条形图缺口，不签整个F2。
