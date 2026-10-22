# 可选完成回执定位失败后原完成路径的投影释放

基线 `71c086f62f473baf706c7176eb97bab5b1da43e7`。根独审发现组合P2：未完成Source/Extract先GET完成回执得到NOT_FOUND，再按原流程显式完成，原回执和详情GET均严格匹配且被当前ctx/selection采纳，但 `completionProjectionInvalid` 未清，继续隐藏成果/Source核查/Extract→Cold路线。

产品只有 `web/protocol.js` 一行：原 `readProtocolCompletion` 在 `protocolCompletionReadMatches`、`current()`和精确selection检查通过后，仅当flag等于当前entry.rid时清flag，再走原accepted状态及渲染。未移动/减少门、未改POST、原key/body、UNKNOWN、只读readbackMap或任何Python后端。历史完成回执不会因此自动变FOUND；Source技术完成仍UNKNOWN/待独立核查，不变语义PASS。

同一最终控制器VM脚本 `tests/protocol_completion_ui.cjs ... readback-composition [可选基线JS文件]` 对基线Git blob与修复源码分别运行：12场景中两族成功路径**2红→2绿**，其余10个对照（每族403、严格详情不符、较新selection、关闭上下文、完成响应UNKNOWN）两侧均维持关闭。每个场景原key及body/只读Map均核；UNKNOWN不换键/不因普通再次点击重发。原件见`red/`、`green/`、`red-green-summary.json`，基线原字节为`protocol-before.js`。正常完成后以原控制器的常规重绘核按钮，不增加详情GET或显式“重新读取”来替代修复；Source仍须显式勾选独立核查，Extract只恢复原已完成计划路线。

新增pytest入口只跑这一新mode：**1 PASS，0.09秒**，内部为上述12个VM场景；不与12相加计总数。`pytest.xml/log`和`pytest-runtime`保存原件，实际源码SHA对应`source-hashes.json`。Node语法及该Python测试文件Ruff通过。没有重跑62项、旧logic/http套件、Edge、模型/Mock/Worker/API进程或真实业务HTTP；VM内假的原完成POST与GET不冒充实际网络证据。

初次原件也保留：`initial-red`已复现两族失败；`initial-green`仅Source下一门断言仍红，原因是测试在原completion的busy渲染后误要求确认框即时启用，正常旧路径同样要常规重绘。没有为迎合它再改产品；最终同脚本在操作结束后的正常重绘核确认框/原显式确认门，两侧重新对照。产品仍只增加一行。

独立只读源码与红绿复审：`/root/next_scope_review`限定ACK，该行仅在严格当前采纳之后清当前Run投影；未改原键、UNKNOWN、只读Map、POST或权限，未发现新增确定问题。审查者未执行测试，不要求扩大窗口。

仅控制器VM组合回归，不是原生DOM、像素、PG/provider/G0或整体F2/R0验收。前片62PASS及后端29原件/16依据源码的证据保持原版本，不继承为本次全回归。owner PENDING，未发布。
