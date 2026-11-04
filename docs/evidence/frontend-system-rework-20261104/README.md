# 浅蓝专业工作台：系统性重构

2026-11-04，Windows 本地开发。此记录对应用户最后的系统性UI/UX规范，取代前面多色/磨砂/粗边框候选的视觉结论。代码仍在 `codex/frontend-windows-polish` 未提交工作区；main基线为 `6452ae95012ad9c72c0d4d735f4f5b2ca37c9cde`。

## 代码诊断与实施

检查了静态HTML、`frontendPresentation`的原DOM重组、`selectProjectSection`、材料与运行控制器、应用使用面及全局CSS。具体问题是：多轮规则重复覆盖同一元素；10–12px文字混入主操作；多个同等权重按钮平铺；粗框和不同透明材质并列；配置区缺少连续表单关系。

本轮保留原业务模块与控件身份，将多轮视觉覆盖替换为一套 `Professional workbench system`，集中定义颜色、间距、圆角、阴影、状态、组件和断点。规范见 [workbench-ui-system.md](../../design/workbench-ui-system.md)。

- 配置区成为单张连续表单卡片：任务类型 → 目标 → 材料 → 开始任务。主按钮是该区唯一实色操作。
- 成果区保留更大宽度，以状态、标题和实际数据建立层级；来源/调用/验证/版本集中在“检查详情”。原按钮和监听器保留，关闭后回到可见的入口，支持Escape。
- 保留已有材料选择、移除、完整名称读取、历史、CSV高级流程、应用和资源入口。相同材料刷新不会重建摘要节点，键盘焦点保留。
- 清理高饱和多色、深色粗框和背景网格，改为浅蓝底、白色内容面、轻边框与弱阴影。背景仅两层低对比氛围，可停止并尊重减少动态。
- 页面标题22px、功能标题18px、正文/表单14–16px、辅助13px，关键值30–32px。图标标记最低12px；不再用大面积小字体压缩布局。
- 资源页的标题与添加操作对齐；应用页沿用相同表单、结果与状态规范。窄窗项目分区使用明确的选择控件，避免中文导航挤成单字列。

新建的图片资产来自本轮内置image_gen，已接入品牌区与favicon。源图、128px运行时PNG与Windows ICO分别在 `src/sim2act/web/sim2act-mark-v1.png`、`sim2act-icon-128.png`、`sim2act-icon.ico`；运行时PNG17,452字节，未把1.58MB源图用于每次页头请求。完整生成提示词见 [brand-generation.json](brand-generation.json)。ICO已导出和HTTP读取，未据此声称重新打包Windows EXE。

## 实际验证

| 范围 | 实际结果 |
| --- | --- |
| 已有回归 | 8个驱动共209项检查通过，包括受控DOM/几何、状态与真实HTTP读取；不是209次浏览器测试 |
| 浏览器交互 | [20项实页检查通过](browser-interactions.json)：分组工具入口、四种检查、焦点返回、Escape、材料选择/移除、完整名称键盘读取、草稿保留、高级CSV入口、导航收窄、主题和减少动态；该组操作0业务POST，0未捕获JS异常 |
| 响应式 | [9个视口记录](viewport-checks.json)：1920×1080、1440×900、1366×768、1280×720、1101×768、1024×768、768×800、375×812、320×800。无整页横向溢出；常见桌面尺寸的典型目标+两份材料配置无需内部滚动，提交按钮在首屏 |
| 小屏补充 | 最终375/320布局另检项目分区选择、成果/来源检查返回。手机按流式布局允许纵向滚动；未把手机说成全部内容一屏放完 |
| 组件状态 | 无效逐字读取选择禁用提交，切回普通任务恢复草稿；Hover不移动按钮；输入15px/400，键盘外框2px，focus边界实际为rgb(29,79,135) |
| 本地文件选择 | 实际选择UTF-8 CSV，名称/格式/内容正确进入本页预览；未自动保存，服务端材料条数不变，0业务POST；测试后恢复原草稿，见[file-preview-check.json](file-preview-check.json) |
| 配色与语法 | 36组浅/深色基础token色对通过；修改JS的node语法检查、API Python3.12 AST解析和git diff --check通过 |
| 数据与接口 | 当前API与独立合成SQLite中的30/v1、5/v2仍可读。没有改变任务或授权接口，没有用假数据替换接口响应 |

此项目是随Python包提供的静态HTML/CSS/JavaScript，没有单独的TypeScript/Vite打包流程，因此没有声称执行不存在的前端构建任务。

## 截图

- [当前项目工作台](project.png)
- [1366×768项目](project-1366.png)
- [1280×720项目](project-1280.png)
- [深色模式](dark.png)
- [资源工作区](resources.png)
- [应用工作区](apps.png)
- [小屏](mobile-375.png)
- [本次重构前的候选](before.png)

截图是Windows Chrome实际页面，使用独立合成测试数据。旧截图保持原件，本文件只引用本轮明确记录的证据。

## 技能与参考使用

`ui-ux-pro-max` 已按用户要求安装到 `C:/Users/Lenovo/.codex/skills/ui-ux-pro-max`，来源提交 `dd9a1b4cf9f67ca2e326f646d93e101b2778db30`。73个配套源文件逐个核对Git blob摘要，SKILL.md只适配了本机绝对调用路径；搜索脚本实跑通过。

采用了匹配到的表面层级、紧凑标签完整值入口、可取消交互和语义token建议。自动生成的两次完整方案偏营销页面，不适合当前应用，未保存成项目设计规范。折叠专项查询没有可靠匹配时，使用一般表单规则及[Fluent Accordion官方文档](https://fluent2.microsoft.design/components/web/react/core/accordion/usage)作为补充。

公开研究还包括 [Fluent Figma UI kits](https://fluent2.microsoft.design/get-started/design)、[AlignUI Accordion预览说明](https://figma.alignui.com/components/accordion)、[Figma交互组件](https://help.figma.com/hc/en-us/articles/360061175334-Create-interactive-components-with-variants)、Aceternity材质/背景与Motion交互文档。Figma连接器实际尝试读取AlignUI公共文件，但返回无编辑访问权；没有读取到该文件图层，没有复制付费组件或把访问失败写成成功。

## 验收边界

- “三秒识别主功能”是设计目标，未开展独立用户计时研究；视觉认可仍以实际使用为准。
- 色对计算不是全页WCAG、读屏、真实触屏、系统DPI、浏览器菜单缩放或完整动画性能验收。
- 当前运行使用项目已有的显式test-only SQLite工程入口；标准新合成工作台此前的原生租约模块缺项未在视觉任务里绕过或解决。
- 未重验真实模型、正式PG、完整Source/Cold、全部人工审批组合、WebView2原生关闭重开或完整产品验收。
- 未提交、未推送、未部署。原项目数据未覆盖，临时测试资料留在忽略的 `.local/frontend-review/`。
