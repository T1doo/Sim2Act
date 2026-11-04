# 请审阅 Sim2Act 当前前端的 UI/UX

请作为资深 SaaS 产品设计师和前端 UX 审阅者，实际查看下面的截图与相关代码，对当前界面提出具体、可执行的改进建议。请先审阅，不要立即重写代码。

## 项目背景

Sim2Act 是一个“目标与授权材料 → 任务执行 → 可核查成果 → 可复用应用”的工作台。一级导航包括：

- 项目：配置任务目标、选择材料、开始任务、查看成果及来源/调用/验证/版本。
- 应用：使用已有应用实例，输入参数，查看本次与历史结果。
- 资源：管理材料、可信能力、连接与授权。

前端技术栈是静态 HTML/CSS + 分模块 JavaScript，由 Python API 提供；不是 React/Tailwind。现有权限、请求恢复键、不可变版本、任务状态和审批逻辑需要保留。项目仍在工程预览阶段，不能为了视觉效果增加假数据、假进度或不存在的功能。

## 最近这一阶段做了什么

本轮保留浅蓝、白色、蓝灰色的清爽专业风格，收敛了前几版的多色装饰、重磨砂与粗边框：

1. 全局导航、配置任务、任务成果形成三个区域；配置区合为连续表单卡片，成果区获得更大的空间。
2. 统一颜色、间距、圆角、边框、阴影和组件状态，清理了多轮重复覆盖的CSS。
3. 统一中文无衬线字体层级：主标题22px、功能标题18px、正文/表单14–16px、辅助信息13px、关键数值30–32px。
4. “开始任务”是配置区唯一实色主按钮；来源/调用/验证/版本集中到“检查详情”，复制按已有能力出现。
5. 减少重复说明与不必要折叠，保留高级CSV、历史、完整回执、授权、版本与恢复功能。
6. 背景取消网格和高饱和光带，保留低对比浅蓝氛围；支持深色与减少动态。
7. 保留AI生成的软件图标，已接入页头与浏览器图标。

已有209项回归检查、20项真实浏览器交互及多尺寸验证记录，但请独立评价视觉质量，不要因为测试数量而提高审美评分。

截图中的金额30/v1、人数5/v2是实际保存的合成CSV结果；左侧输入是当前草稿，不能把它与既有成果自动视作同一次执行。

## 请实际查看这些资料

- [审阅入口：按编号整理的截图与背景](https://github.com/T1doo/Sim2Act/blob/main/docs/reviews/frontend-ui-review-20261104/README.md)
- [01 当前项目工作台，1440×900](https://raw.githubusercontent.com/T1doo/Sim2Act/main/docs/evidence/frontend-system-rework-20261104/project.png)
- [02 笔记本窗口，1366×768](https://raw.githubusercontent.com/T1doo/Sim2Act/main/docs/evidence/frontend-system-rework-20261104/project-1366.png)
- [03 较矮窗口，1280×720](https://raw.githubusercontent.com/T1doo/Sim2Act/main/docs/evidence/frontend-system-rework-20261104/project-1280.png)
- [04 资源工作区](https://raw.githubusercontent.com/T1doo/Sim2Act/main/docs/evidence/frontend-system-rework-20261104/resources.png)
- [05 应用工作区](https://raw.githubusercontent.com/T1doo/Sim2Act/main/docs/evidence/frontend-system-rework-20261104/apps.png)
- [06 深色模式](https://raw.githubusercontent.com/T1doo/Sim2Act/main/docs/evidence/frontend-system-rework-20261104/dark.png)
- [07 小屏375px](https://raw.githubusercontent.com/T1doo/Sim2Act/main/docs/evidence/frontend-system-rework-20261104/mobile-375.png)
- [08 小屏320px](https://raw.githubusercontent.com/T1doo/Sim2Act/main/docs/evidence/frontend-system-rework-20261104/mobile-320.png)
- [当前UI规范](https://github.com/T1doo/Sim2Act/blob/main/docs/design/workbench-ui-system.md)
- [检查记录与未验证范围](https://github.com/T1doo/Sim2Act/blob/main/docs/evidence/frontend-system-rework-20261104/README.md)
- [主要样式 app.css](https://github.com/T1doo/Sim2Act/blob/main/src/sim2act/web/app.css)
- [页面组织与交互 app.js](https://github.com/T1doo/Sim2Act/blob/main/src/sim2act/web/app.js)
- [原始页面结构 index.html](https://github.com/T1doo/Sim2Act/blob/main/src/sim2act/web/index.html)
- [应用使用流程 use.js](https://github.com/T1doo/Sim2Act/blob/main/src/sim2act/web/use.js)

如果链接打不开，请明确说明具体缺少哪张图或哪个文件，让我补充附件；不要假装已经看过。请以01–08当前截图为准，审阅入口最末的历史图只用于对照。

## 我特别希望你判断的地方

1. **第一眼的理解与焦点**：是否能快速分辨导航、配置、成果三个区域？“开始任务”和重要结果是否突出？当前草稿与已保存/历史成果的关系是否可能令人误解？
2. **布局与密度**：三栏比例、卡片宽度、表单顺序、剩余留白是否合理？尤其是右侧只有少量结果时，如何集中内容而不增加假KPI或装饰？同时考虑长文本、长表格和复杂结果。
3. **字体与中文阅读**：字号、行高、字重和对比度是否协调？1366×768是否仍清楚？材料名称的截断及完整值入口是否合适？
4. **功能边界与组件一致性**：卡片、输入、材料行、状态、表格、工具按钮之间是否自然？哪里仍像零散组件拼接？如何用层次和对齐解决，而不是机械加粗边框或加阴影？
5. **主次操作与可发现性**：“检查详情”归组是否过度隐藏重要能力？复制、来源、验证、版本和完整回执的分工是否清楚？应用页是否仍有重复信息或过多工程术语？
6. **状态和动效**：结合代码检查Hover、Focus、Disabled、Loading、等待、失败与恢复。仅凭静态截图无法判断的部分请标为待验证，不要假定其不存在或已经完善。
7. **响应式与可用性**：在窄窗保留可读字体与明确操作顺序，而不是强行缩小所有内容；检查键盘、焦点返回和触达范围。

## 输出要求

- 先给简短、坦诚的总体评价，指出做得合理的地方与最影响体验的问题。
- 按P0/P1/P2列出最多10个具体问题，每条写清：对应截图/区域、可观察证据、为什么影响用户、建议怎样改、可能涉及的组件或CSS职责。
- 给出一套连贯的优化方向，保留浅蓝/白色专业工作台风格；可以借鉴Linear、Notion、Vercel Dashboard的信息层级，但不要照搬其配色。
- 最后给出优先实施的5项改动及推荐顺序，区分立即能做、需交互验证、依赖新增业务能力的建议。
- 不要泛泛重复“更现代、增加留白、字体放大、卡片加阴影”；也不要为了好看删除功能、隐藏必要的确认/错误，或要求无理由迁移技术栈。

我最看重的是：用户一眼理解当前在做什么、下一步该操作什么、重要成果在哪里，同时界面克制、统一、精致。
