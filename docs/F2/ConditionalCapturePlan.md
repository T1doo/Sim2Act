# 条件报告双图与同预算准备耗时切片

事前范围：独立 dev/conditional-capture-local，base0126f5459d7385f0c33f3ca4d9d585d91e2a4a1f；本地实施与提交，不push/CI。独立 /tmp/conditional-capture-venv，依赖文件复制为独立副本，排除旧sim2act/editable/pth，以本树src优先；每项测试自己的tmp fixture，不共用其他线DB。

最小实现：共享条件oracle提供可选capture回调，在真实手工报告PASS/BLOCK与PASS/UNKNOWN阶段复用protocol-desktop.png、protocol-narrow.png。旧protocol26和布局检查保留；原协议图明确superseded，不引入输出槽。新截图记录source/hash/contract/状态/viewport/保护观察，语义UNKNOWN、用户PENDING、正式false。DOM验证回调的真实页面状态和元数据，不能替代Edge/像素验收。

耗时量测：先同集合pytest --durations观察setup/call慢项，以正常隔离fixture及同一oracle至少两次实际HTTP专项比较。定位重复Python准备/导入/fixture控制进程成本后仅优化可证明重复开销，保持collection、全表指纹、权限/ABA/冷/失读/真实2500ms poll等全部断言与fixture作用范围。不提高15min job、4min step、150s helper、12s predicate；不改runner/workflow/WindowsPS/cache/权限。

验收：22旧check全部保留；双capture正确顺序和技术/语义状态，optional caller兼容，错误capture不得被PASS吞掉；fixture更新仍仅原资源content/hash及一条原grant撤权、恢复全表边界。完整相关HTTP/条件API/旧protocol/注册fixture/整合回归、Ruff/mypy/Node/diff检查，保存初失败及基线/最终实测。真实保护Edge、新双PNG及Windows总耗时保持NOT_RUN，既有7c02 CI不能验证本轮源码。
