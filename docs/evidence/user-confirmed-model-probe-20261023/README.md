# 用户确认费用后的单次模型连接诊断

执行源码 `bed0f091fdddd6703d1119247ff8eababd67700c`，普通分支
`dev/production-trial-stages-20261018`。用户于2026-10-23明确确认现有接入无消费、要求使用；
父级授权最多3次请求、每次至多1024输出token、总10分钟。实际只使用一次，不自动重试。
费用依据为 **USER_CONFIRMED_NO_COST_NOT_OFFICIAL_VERIFICATION**，不是官方证明。

## 实际结果

现有环境只检查凭据是否存在；实际发送仅进程内使用现有 `INTERN_API_TOKEN`，
没有输出、复制、哈希或保存凭据。固定原端点
`https://chat.intern-ai.org.cn/api/v1/chat/completions` 和 `intern-s2`，无重定向或回退。
输入仅为合成短提示，要求返回 `{"probe":"sim2act-connectivity","value":7}`；空工具，无业务输入。

- HTTP **200**，一次 adapter、一次精确 wire guard、零重试；正常退出0。
- **3.627964166秒**，输出39 token，输入139 token，共178；用量状态known。
- 原模型身份规则ACCEPTED、原响应结构校验、固定JSON及严格字段类型校验通过。
- 单次技术记录在发送前落盘，目录不能复用；本次120秒请求期限，600秒窗口，1024输出上限。
- 未创建Store、Run、Worker、Grant、业务许可或新服务；没有调用G0、Cold2、W5或真实业务链。
- 原 `production_evidence.resolve_account` 及所有业务来源/权限门未修改。

原始provider body、headers、私有reasoning及异常消息不落盘。`result.json` 是安全结果投影，
含程序观测的响应长度与SHA；没有原始响应，独审不能独立重算该响应SHA。
返回原名未保存，ACCEPTED表示原规则接受的两个精确别名之一；没有扩大别名集合。
账号归属及权威来源验证仍NOT_PERFORMED，不能凭本次结果宣称生产来源、官方免费资格、
G0、整体F2/R0或真实任务语义验收通过。也不凭token用量推算金额。

## 实现、测试与失败保全

新增独立诊断脚本及针对性测试。原适配器只在capture失败时增加私有HTTP状态观测，
公共错误、身份策略、发送次数、deadline、来源门和清理路径不变。

最终16项Mock测试全部通过（JUnit 0.06秒），Ruff及源码diff检查通过；没有重跑旧大套件。
测试覆盖一次发送、目录不可复用、缺配置、错误模型、截断、严格值类型、未知用量、
403/429、超时、wire篡改、超大流、凭据回显不保存/不哈希，以及同步私有状态不泄入公共错误。
这些Mock次数不计作真实模型调用。首轮10PASS/3FAIL保留：异步拒绝在header即停止读body，
超时空缓冲不证明收到body，初版记录/断言误判已修；中间13PASS也保留，不累计为额外覆盖。
归档脚本首次把自身Python进程算入存活列表的失败亦保留；仅修正只读归档核查，未重试模型。

`source-freeze.json` 记录执行前5份源码摘要；执行后全部一致。`cleanup.json` 记录正常退出后
无其他Python/pytest/Node进程，核查只排除核查器自己的PID，未触碰未知进程。未安装依赖、
新增账号/凭据/安全权限或扩大服务。性能候选继续保持撤回，本次没有性能窗口或净收益宣称。

## 原件

`result.json`、执行前源码冻结、首轮/中间/最终JUnit、清理观察及独立审查均在本目录。
原运行目录 `/workspace/model-probe-authorized-20261023/run-1` 保留。
MANIFEST记录归档字节摘要；代码从冻结Git提交读取。没有将程序安全摘要冒充原始HTTP抓包。
