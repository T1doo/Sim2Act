# 从任务到证据的连续工作面

用户否定通用模板后，保留Sim2Act研究/任务工具定位，替换布局而非再换一组卡片。视觉记忆点只有深色常驻导航与连贯的白色证据工作面：左侧任务是上下文，右侧成果是阅读主体。去掉英文眉题、装饰字形和重复容器；没有吉祥物、宠物或AIyou素材。

颜色：研究纸面#ffffff、工作底色#f2f5f6、导航#173341、正文#1d2d3c、行动#12695d。文字沿用离线系统可用字族，不在用户加载页面时请求外部字体；标题30/25px、主体13–16px、原代码12px，层级靠字号和间距而非装饰。原确认、授权说明、UNKNOWN/人工PENDING及未发布均可见。

桌面通过body Grid布局适配工程预览banner/登录，不假定固定header高度；任务/结果是一张连续工作纸。移动端恢复水平导航、单栏成果优先。高频按钮没有位移动画，保留即时键盘焦点、原生details和减少动画。

只读学习，不安装/运行这些仓库的代码、launcher、hooks或npx，不向其发送项目内容：
- https://raw.githubusercontent.com/anthropics/skills/main/skills/frontend-design/SKILL.md
- https://raw.githubusercontent.com/pbakaus/impeccable/main/.agent/skills/impeccable/reference/craft-floor.md
- https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
- https://raw.githubusercontent.com/kylezantos/design-motion-principles/main/skills/design-motion-principles/SKILL.md

第一版真实Windows Edge图已亲看，仍模板化，且主卡406.6875px违反原<400px，原失败不关闭。第二版基于该实测修构图、去眉题/空间；原阈值不改。v2像素待真实渲染，不能用静态检查或第一版截图签收。
