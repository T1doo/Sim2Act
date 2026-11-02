# Sim2Act 前端日逐项覆盖

基准为已批准 DOCX version 1：`1e6e34ec404c8e319e84b0c14c1d4f9293fce26e78c1c5d1f38fa439dceb6e74`。995段正文、49张参考与原创图已本地消费；设计图不是产品实测。源码从 `b6b2e32884fad0252ad739105fdd0ea7430807f7` 接续。

下表记录实现位置与实际证据，**不表示42项已完成全部验收**。受控DOM证据见 `docs/evidence/frontend-day-20261102/frontend-interactions.json`，真实HTTP/合成SQLite回归与其限制见同目录README。

| 项目 | 要求 | 实现文件/职责 | 已做与实际验收边界 |
|---|---|---|---|
| S01 | 浅色指令与非空应用成果 | index.html; app.js; app.css | 原节点左指令右成果；非空文本阅读；同Run断线保留已读成果。DOM与HTTP回归；像素待验 |
| S02 | 指令与成果双区 | app.css #task-workbench | 统一细线双区与原三个一级工作区。DOM顺序已验；比例实看待验 |
| S03 | 成果居中 属性靠边 | app.js renderFrontendInspector | 当前任务与应用共享同一检查节点；窄宽改为可返回检查视图。DOM归属/关闭已验 |
| S04 | 成果旁常见的指令入口 | app.css #task-list-panel; app.js | 原目标输入与材料选择身份不变，右侧独立滚动。输入保留已验；实际滚动待验 |
| S05 | 暖白外壳与细边线 | app.css :root | 浅暖、陶橙、细边统一；重整旧色彩覆盖。36组实色对比计算通过；非整页无障碍结论 |
| S06 | 可调指令与成果宽度 | app.js frontendPresentation; app.css | 键盘方向/Home/End、拖动、双击复位、成果优先。键盘280–420边界已验；指针实操待验 |
| S07 | 导航收成窄图标轨 | app.js nav-text; app.css 窄导航 | 64px图标轨保留中文可访问名及hover/focus提示；未作像素/读屏验收 |
| S08 | 事件列表与当前详情 | app.js renderFrontendInspector calls | 事件阶段和原始详情分层；只读当前实际回执。受控事件DOM已验 |
| S09 | 资源列表与网格切换 | app.js applyFrontendMaterialFilter; app.css | 材料列表/网格共享查询；能力连接仍为目录。切换保查询DOM已验；无虚构封面 |
| S10 | 无结果仍能清除查询 | app.js refresh; applyFrontendMaterialFilter | 成功空目录、查询无结果、读取失败保持不同语义，清除不删资源。DOM/真实HTTP文件回归已验 |
| S11 | 同一成果的按需检查侧栏 | app.js frontendApplicationInspection | 来源/调用/验证/版本共用检查区；切应用Run清旧内容。单节点与失效清理DOM已验 |
| S12 | 说明就地展开 | index.html 原details; app.css | 关键流程控件保留；补充说明原生展开及180ms局部揭示。展开高度/真实焦点裁切待浏览器验证 |
| S13 | 提交按钮解释短等待 | app.js renderRunSubmission; app.css | 实际sending文案/aria-busy与固定宽度；原意图防重不变。原键与双击回归通过 |
| S14 | 复制结果的就地反馈 | app.js frontendTextCopy; frontend-copy-result | 文本复制等写入Promise，拒绝和迟到不报成功；约1.6秒反馈。受控剪贴板DOM已验，真实剪贴板未验 |
| S15 | 版本回看与恢复分开 | app.js frontendPreviewGoalVersion | 历史只读、返回当前、独立确认带回未保存编辑草稿；保存仍走原版本检查。没有自动服务器恢复承诺 |
| S16 | 成果区域轻展开 | app.css reveal; app.js 成果阅读 | 局部揭示不缩正文；减少动态直接呈现。原位关系已实现，浏览器动效未验 |
| S17 | 结构化表格成果不离开指令 | internal.js renderManifestViews; 原列选择器 | 表格数值对齐/局部滚动，沿已有材料/列选择；不声称任意文本片段或逐格回写。实际表格/图表回归 |
| S18 | 运行主按钮的轻落键 | app.css button:active | 1px/90ms按下与120ms释放；系统/产品减少动态禁止位移。CSS审阅，实机待验 |
| S19 | 行内更多动作自然出现 | app.js frontendResourceActions | 贴行命令菜单、方向键、Esc还焦、碰边翻转。菜单焦点DOM已验；真实定位待验 |
| S20 | 真实运行旁的安静状态点 | app.js updateFrontendRun; frontendRunCommand | 只有RUNNING动点；未知取消不重发，终态静止。受控未知、迟到、双击与原独立取消回归通过 |
| S21 | 成果条目打开非空独立画布 | app.js renderOrdinaryOutcome; frontendReadableDocument | 真实成果条目到阅读面，保留完整原文；原应用实例/历史继续工作。文本/CSV与应用真实HTTP回归 |
| S22 | 低占位来源标记与按需解释 | app.js 检查工具条 | 来源中性入口，不添加置信度或AI认证。当前来源绑定与未知说明DOM已验 |
| S23 | 用户改写后仍保留依据 | manual-locks.js; delivery-graph.js; 历史预览 | 原锁定/修改影响/原证据保留，本轮未重写。原流程全量人工锁回归未重跑 |
| S24 | 暖灰深色工作台备选 | app.css dark tokens; app.js 外观偏好 | 暖灰独立主题，不对材料/图表反色；36色对含深色。主题/密度独立DOM通过 |
| S25 | 长中文成果的稳定字阶 | app.css 中文字阶与回流 | 列表15/18、阅读16/20，长内容换行。真实320/200%/400%及原生DPI未验 |
| S26 | 统一单线图标并配中文 | index.html 原SVG; app.js nav-text | 沿用一套1.5线宽SVG和中文动作；无新图标包/外部素材。折叠标签DOM保留，读屏未验 |
| S27 | 应用运行页的输入与本次结果 | use.js; internal.js; 原生字段校验摘要 | 原输入/执行/实例历史/结果/返回项目编辑入口保留。应用4场景与报告HTTP回归；无新增必填业务字段 |
| S28 | 空闲区少量暖柔光 | app.js frontendRefreshIdle; app.css idle-edge | 原创80px空闲暖光，默认静态，编辑/任务/检查退出；无第三方脚本。真实帧率/后台耗电未验 |
| G01 | 主题密度分工 | app.css; app.js appearance.v1 | 两主题两密度独立偏好，不改变输入/版本/原恢复URL。DOM通过 |
| G02 | 成果优先布局 | app.js setWidth; app.css | 成果优先收至280px，恢复344px；保原输入。DOM边界通过，实际宽表实看待验 |
| G03 | 局部展开备选节奏 | 原details; app.css reveal | 同一补充展开规则与减少动态；原生details即时提供内容，180ms揭示。精准高度节奏未实看 |
| G04 | 两种状态点都保留 | app.css pulse/dots; app.js calls | Pulse主状态/Dots详情；检查调用时主Pulse静止，未知/终态不动。受控状态DOM，实际动画待验 |
| G05 | 淡蓝极光保留 | app.css idle-edge cool; 外观偏好 | 淡蓝极光与暖光互斥；原创静/动态低幅渐变，不打包外部代码。性能未验 |
| G06 | 完整页面关系补件 | index.html 原应用目录; app.css | 保完整目录与指令工具关系，无CMS功能与外部模板分发。报告/应用HTTP回归通过 |
| G07 | 窄窗检查与材料选择 | app.js frontendDialog; app.css 响应式检查 | 材料查询/多选/确认独立对话框；检查非模态，关闭还焦。选择保留/确认DOM通过；窄屏像素待验 |
| G08 | Kanso可选快速查找 | app.js openLookup | 可见查找与Ctrl/Cmd+K，仅已读取项目/应用/材料，不发新查询请求。0请求DOM验证 |
| G09 | 文本差异局部 | app.js frontendTextDiff; delivery-graph.js | 局部按词边界标记历史/当前变化，原类型化图差异保留；不取代主成果。局部差异DOM通过 |
| G10 | 历史行为参考 | app.js frontendPreviewGoalVersion | 只读历史与确认带回草稿分开，明确尚未保存与现实副作用不撤销。DOM通过；服务器冲突恢复全流程未验 |
| G11 | 两组中文字号 | app.css 字阶/媒体查询 | 两套中文场景字阶；窄窗动作换行/局部表横滚。真实缩放/屏幕键盘未验 |
| G12 | 来源与资产管理 | docs/design/frontend-assets.md | 仅原创CSS/JS与已有SVG/系统字体；原参考图仅存在批准文档，未进入产品素材 |
| G13 | 应用验证和资源三分 | 原项目/应用/资源控制器; tests | Source/Cold、原键、撤权、实例、输入错误、历史与真实状态分离。合成SQLite/离线HTTP/受控wire；非PG/LIVE/原生 |
| G14 | 全局动效降级 | app.css; app.js 外观/visibilitychange | 系统/产品减少动态、后台暂停、静态正文、终态停动。受控DOM与静态审阅；真实性能/读屏未验 |

## 仍未完成的验收与实施边界

- Linux Chromium 在保留沙箱的启动中因SUID helper配置中止；没有前后截图、真实页面像素或真实键盘浏览器证据。没有通过关闭隔离重试。
- 1440/1366/1280/1024/768/320、125/150/200/400%回流、读屏/高对比与原生WebView2缩放/关闭重开均未验。
- 动效位置、精确展开高度、真实剪贴板、拖动命中、背景帧率/耗电、长文滚动性能未实测。
- 历史恢复目前明确带回**未保存编辑草稿**，再走原保存/version检查；未增加服务器恢复接口，未宣称恢复已经持久化。任意文本片段指令与逐格回写未实现，仍按文档第7章的现有材料/列选择阶段边界。
- 原人工锁定、全部异常组合与完整双材料到任意模型成果场景未全量重跑。当前测试是合成SQLite/受控wire/Mock或NoProvider，不能外推真实模型、PG、完整P-B或R0。
- 独立审查仍需另一位只读审阅者完成；本任务完成的是作者源码自查与针对性回归。没有因该项建立竞争writer。

CI账沿用487/900秒，本任务新增CI执行0；未部署、未发布、未把产品分支合main。
