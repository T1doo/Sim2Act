# 自然试验跨 Run 预算的只读入口

基线 `fae2a3d7de3978671ca9c1c1c19cb8012e731eeb`，普通分支 `dev/natural-trial-budget-view-20261018`，root唯一仓库写入者。开工HEAD与远端一致、clean，约23GB可用。用户已明确授权安全门代码的常规开发与合成验证，真实执行仍未获授权。

先独立审查实际源码与原V5：自然家族专属准入、三阶段七槽非退还总账、零费证据检查、默认拒绝及离线Worker接线已经存在。本轮纠正此前把普通LIVE关闭概括成这些代码缺失的过宽判断。10月13日提案之后的现有代码不能忽略；同意记录及SYNTHETIC_ONLY permit均不是有效LIVE令牌。生产account/零费权威与network sender仍未注册，现有默认拒绝保持。

实际可见缺口是现有P-A七槽同意面板只显示固定caps，没有访问已有受鉴权预算GET的入口。原V5产品§7.5要求未知用量不能填0、token不能直接换算费用。本轮只改index.html与natural-goal.js：用户明确点击查账，以完整准备回执里的原approval key读取既有预算API；不改任何后台.py、资格anchor/pin、Principal/Grant、执行器、发送门或默认设置。

显示总计及generate/source/cold各Run的已保留槽、保守token envelope、未预留数学容量、HALTED/RECONCILING和未知用量。完整total_tokens未知保留null；已返回total分量不是已接受总量。费用严格显示UNKNOWN、币种null、免费/强制不可收费未核实、LIVE拒绝；付费上限0不等于已核实费用0。所有原槽不退还，不因换Run重新计数。

独立digest与完整Scope绑定项目/本人/项目runtime、原试验/approval/contract指纹、quota_subject和expiry。逐stage的Run、数量和envelope与原slots/stage_runs核对，未知/known分量及完整总量与原settlement一致。不同阶段不要求同一runtime。已过期/撤回但仍可完整授权读取的历史不隐藏占额；metadata-only不能拼key降级读取。

仅显式GET，不随恢复自动查询。单flight防双击，开始读取先清旧账，所有await后检查账号连接、项目、工作区、entry/operation/receipt和读代次；原key或导航变化不采用旧响应。任何读取或绑定失败清旧私有范围和账目、保留原key为UNKNOWN，先只读重核；无ledger实际409不能伪装零使用或七槽可发。

计划内资格是一条真实loopback HTTP/JSDOM页面：两份正常材料/Goal、两个正常准备及仅LIVE_BLOCKED同意记录；一个普通生成Run仅claim一次，现有真实准入配SyntheticOnlyFeeAuthority及原预算reserve/未知settle建立合成账本，不运行Worker或模型。页面读无账本409→原key重核→读1槽/1124 envelope/未知用量→双击单GET→一条真实完整预算200迟到时切另一原key，旧响应不覆盖→换项目清空。全页面GET/0POST/0下载，全55表保持；另三项明确合成validator篡改拒绝，非实际HTTP故障。

执行冻结、实际结果与有限独审待完成后补记。当前不生成有效LIVE批准、不读取/填写凭据、不启用LIVE，不恢复旧撤销窗口、不扩大系统网络权限。真实模型/语义、P-B页面、Windows/native、PG、远端CI未因此验收；旧满盘未落盘报告缺口不补签。
