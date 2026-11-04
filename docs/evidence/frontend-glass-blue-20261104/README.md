# 浅蓝磨砂玻璃视觉候选

用户于2026-11-04明确要求浅蓝科技感、磨砂玻璃按钮、更丰富颜色与动态背景，覆盖早期DOCX的无磨砂/动态默认关闭要求。保留既有业务控制器、授权与运行归属，未提交或推送。

## 参考研究

- [Miguel Ángel Avila：Glassmorphism Dashboard](https://dribbble.com/shots/26136889-Glassmorphism-Dashboard)：作者页面可读，关联[Figma Community UI Kit](https://www.figma.com/community/file/1514405085901665002/glassmorphism-dashboard-ui-kit)访问受限，未读取原图层。
- [Aceternity Liquid Glass](https://ui.aceternity.com/components/liquid-glass)：材质层次和磨砂降级思路参考。
- [Aceternity Aurora Background](https://ui.aceternity.com/components/aurora-background)：外围缓慢光影参考。
- [Aceternity Hover Border Gradient](https://ui.aceternity.com/components/hover-border-gradient)：悬停描边层次参考。
- [Motion hover](https://motion.dev/docs/hover)：区分鼠标与触摸hover，避免触屏残留反馈。

均为视觉/行为研究；本轮以原创CSS和已有JS实现，没有复制第三方图层、素材或组件源码，没有新增运行库或外部资产请求。Figma不可访问没有被记为已查看图层。

## 实际实施

浅蓝基础配色，紫/青/粉用于局部图标与格式标记。玻璃按钮使用透明渐变、内高光、12px背景模糊和低幅阴影；悬停柔光跟随鼠标位置，不改变点击位置，禁用按钮没有柔光。顶栏与指令区形成半透明材质，成果正文保持高不透明度。

背景仅三个装饰层，26/32/29秒transform/opacity动画，配静态淡网格，aria-hidden及pointer-events:none。外观偏好提供“流动光影背景”开关，关闭暂停；减少动态关闭动画，页面隐藏/失焦沿既有生命周期停动。没有用背景表达业务进度。

## 验证

- 实际Windows浏览器测得按钮backdrop-filter为blur(12px) saturate(1.45)，鼠标位置变量有实际更新。
- 背景三层animationName均为sky-drift；关闭开关后playState=paused；减少动态时animationName=none。
- 1440/1366/1024/768/320五档实际渲染无整页横向溢出，原合成CSV30/v1可读。
- 六个既有驱动147项通过，新版36组基础token色对通过。透明渐变全位置对比、持续帧率和耗电尚未独立签收。
- 实测发现顶栏backdrop-filter建立层叠上下文后偏好控件被正文拦截，已提高顶栏层级并以真实点击复测成功。
- 本轮截图为[当前项目页](project.png)。用户视觉认可、原生DPI/完整产品验收不由回归数量替代。
