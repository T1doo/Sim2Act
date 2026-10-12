# 新Goal摘要迟到错误门：只读设计审查

2026-10-12，独审`/root/text_logic_review`。初始核验仓库`/workspace/Sim2Act`，分支`dev/own-goal-read-errors-20261012`，HEAD `a747a7aafe7a537858f75bbfa129addd8696d0a6`且worktree干净。root唯一产品作者；本阶段仅只读src/tests/doc并写本/tmp，未执行测试、Worker、HTTP或Node。

结论：用户P2成立，建议的内外两层门是必要且足够小的修复方向。只修新Goal摘要读取/恢复/读回的失效错误和continuation，不改服务端授权、执行器、轮询时钟或全局busy策略。当前不签修复执行PASS，等待作者冻结。

## 已核实的具体问题

`appOwnGoalRead`已经在成功路径捕获`appOwnGoalFence(v)`和递增的`v.readGeneration`，包括hash等待后再校。但函数没有catch；API拒绝、验证抛错或pending回执hash不一致都会直接传播。初始`openAppOwnGoal`的catch仅检查`appOwnGoalCurrent(v)`，缺少读取代次、编辑和workspace fence；其initial读取并未busy，正常较新手动GET可先成功，而较旧GET后失败覆盖CURRENT文字。编辑内容A→B→A恢复字节也不恢复编辑代次，旧错误不能因此有效。

手动read/recover外catch虽捕获编辑/workspace fence，却没有该次readGeneration，无法封住inner错误传播到outer处理之间的较新读取。save读回外层同样没有readGeneration，且其确定4xx分支还能清空`v.state`，不只是覆盖提示。

既有`ownerRead`内层catch失效时return false，以及其初始caller的readGeneration门可作为仓内模式参照；这不是旧候选安装逻辑，也不要求复现已取消的安装目标。

## 最小修复合同

1. inner `appOwnGoalRead`包住API、验证/hash、pending回执和render；catch在原`fence && reading===v.readGeneration`已经失效时return false，仅仍当前的错误rethrow。成功路径现有同一门继续保留。
2. 每个caller在调用`appOwnGoalRead`后、第一次await之前同步捕获它递增后的`v.readGeneration`；外catch必须原编辑/workspace fence有效且该代次仍当前，才写提示。不能只捕获调用前旧代次，也不能在catch中重取新代次。
3. 初始、手动read、recover及save读回都使用外层门。即使inner在检查时仍有效，之后较新读取/编辑发生在outer处理前，outer也必须丢弃旧错误。这是两层门的目的，单靠inner不足。
4. save区分POST阶段与GET读回阶段：GET尚未开始时保留原保存fence和明确4xx效果处理；GET开始后所有状态清理、提示及后续owner刷新都受该读回代次门。`appOwnGoalRead`返回false时不得仅按保存fence继续刷新owner。
5. pending清理仍核原key/body对象身份。被失效GET抛出的4xx不能清空较新GET已经安装的`v.state`，也不能错误释放另一份未确认意图。真正当前的失败仍应正常显示，不能把全部错误吞掉。
6. UNKNOWN及原key恢复依旧GET-only，不自动重发POST；保留表单/明确选择，不继承旧目标/签收，不新增授权。不靠将initial设busy来消除合法重叠，不停止/替换正常interval。

## 冻结后最低必要验证

- 修前真实红：initial旧GET未决→较新GET完整成功CURRENT→旧失败；CURRENT文字、proof/state、表单/选择不得被旧错误覆盖。
- 编辑ABA：旧GET开始→真实input/change A→B→A→迟到失败，编辑代次决定失效，不能按内容相等让错误生效。
- 两层间交错：inner已判定错误仍当前，outer处理前开始较新read或编辑；旧错误及save读回状态清空/后续刷新仍不得生效。
- 手动read与原keyrecover同样迟到错误静默；当前有效失败仍给出提示；UNKNOWN只GET、无新增POST。
- 原4个正常可见owner链和直接新摘要UI回归有限运行，修前/修后各自log/XML/源hash保留，不扩大到其它微观时序或F2-T08兼容执行设计。

定向测试允许按本次明确授权在本地JSDOM安排新Goal摘要Promise先后，使用进程内TestClient/IPC和现有模块；不bind socket，不native/真实模型/CI Forbidden，不执行、实现或替代此前永久NOT_VERIFIED的候选安装精确竞态。用户另要求的小修后F2-T08兼容接续由父作者及另一设计独审负责，本报告只覆盖本P2。

本阶段测试执行0，无活动独审测试；未遇工具/平台拒绝，未写产品/src/tests/仓库或push。源码冻结后才可启动独立验证。
