# 原清单的 text/table 组合（2026-10-18）

原产品设计 §3.3、§5.3 和 F2-T04/T06 要求结构化成果引用注册视图。本片接续 `b2d7edd7`，直接解释已接受的 `View(component_ref, output_field)`，不新增 AST、执行器、Grant、API 或正式发布能力。

## 实现前固定范围与验收

- 首先接入已有确定性文本工具和离线文本结果入口。最多16个组件，严格保持清单顺序，允许 text/table 混合及同一字段重复引用。自然规范和四步报告现有专用成果入口继续使用原合同。
- text 支持声明为 string 的成果字段（最多65536个 UTF-16 单元）；table 支持 schema 声明的有界、封闭、同型对象数组，最多64行、16列，序列化整体最多262144个单元；列顺序来自 `items.properties`，列值限 string/integer/number/boolean。空表仍展示声明列和空结果提示。其它形状给出明确未支持提示，保留原始结果查看。
- chart 缺少轴、序列和单位合同，本片明确显示未支持，不把引用行号当业务图表。任意 HTML、脚本、URL、iframe 不进入视图；全部值以 DOM `textContent` 写入。
- 每条历史成果绑定自己的 `record.release_id`。在本次实例选择内逐一重新鉴权读取不同 Release，核快照及候选指纹、app/project/runtime/principal、typed 指纹、成功 Run/AppRun/版本及输出一致性。不得采用当前草案或实例最新 Release 的视图替代历史定义；不做跨刷新缓存。
- 所有异步读取继续受账号连接、项目、工作区、应用及实例选择代次保护。拒绝/不一致时清空内容，迟到回调不得填充新选择；页面呈现不提交 Run、Grant 或其它写入。

实际验收使用合成 TXT/MD，正常两次 MockTransport 生成→确认→内部 Release→正常 NoModel Worker 的 Alpha/Beta/无命中三次成果。由真实 ASGI TestClient 提供完整页面资产与 GET，JSDOM 操作可见入口：核三组件顺序、schema 列、完整引用、HTML 字面量、空表、同 Run 入口、冷页面重开、每次重新读取 Release、迟到 Release 跨实例隔离。另以明确标记的前端负例核当前草案污染不能改写历史视图、错误绑定拒绝及 chart 未支持。保留实际执行源字节、命令/时长、HTTP、Worker 对象与领取、完整表快照，页面期55表不变。

此验收不等于原生浏览器、Windows、PostgreSQL、远端 CI、真实模型或真人语义验收；本片不重跑已有 T06 集合导出/恢复矩阵，也不补称旧满盘独审原件已恢复。

## 实际执行结论

- 正常接受的候选声明 `text:term → table:citations → text:semantic_status`；两次 MockTransport 响应，经原确认/内部 Release 流程。生成 Worker 为 PARTIAL（语义 UNKNOWN），三个独立 NoModel Worker 分别领取 Alpha/Beta/NoMatch Run 并 SUCCEEDED；四个对象 ID、领取 Run/fence 和调用起止均在原件中。
- **首次整例 FAIL**：pytest 136.83秒，外层140.310677秒。此前24项页面检查通过，55表完全未变。失败为测试驱动在慢实例 GET 之前开始12秒 `releaseRead` 等待，尚未到真实 Release hold 点就超时；最终实例和 Release GET 均为实际200。原 stderr、HTTP、执行字节和失败状态不覆盖。
- 仅将驱动同步改为实际 Release 响应到达后触发的 deferred，并在打开链提前返回时拒绝；原12秒普通等待定义、业务断言、Run/Worker租约和180秒外层上限均未延长。产品 JS/CSS 字节自首轮起完全未变。
- **同原 SQLite/同三个 Run 的冷页面续验 PASS**：独立 page-only pytest 1PASS/122.76秒，外层133.471705秒。46项检查、50个页面 GET、54个实际资产、2次冷启动；前后55表全等。续验0夹具、0Worker、0模型、0POST。覆盖全部三视图顺序/类型/列、完整引用/HTML字面量/空表、原始结果、同 Run 入口、当前草案污染、错误指纹拒绝、真实迟到响应切换到空实例、冷重开。三个前端负例仍明确为合成输入，不是新的合法 Release。
- 修正后的完整生成→页面测试 **NOT_RERUN**；旧 literal 断言仅随新表格 DOM 更新且完成语法检查，旧整链 **NOT_RERUN**。agent及自然规范/四步报告的兼容性为有限源码独审结论，不冒充本次运行资格。

原件根目录 `/workspace/manifest-view-composition-20261018`：`command.json`、`pytest.stdout`、`actual-first/test_manifest_text_table_actua0/{page-proof,actual-http,workers,claims,before-page,after-page-or-failure}.json` 分别保存首次执行；`continuation/{command,measurement,page-proof,actual-http,before-page,after-page-or-failure}.json` 与执行源副本保存续验。见[证据索引](../evidence/manifest-view-composition-20261018/README.md)。远端既有认证拒绝本片没有重试，未推送、CI、正式发布或部署。
