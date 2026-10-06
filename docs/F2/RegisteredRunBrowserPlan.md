# Registered Run 生成入口：受保护 Edge 验收范围

2026-10-06，起点 dev/f1-foundation `021b19207e5658c244540e20c6cdf72aa9e8c41b`。用户明确授权先本地 DOM/API 与独立审查，随后普通 dev push 和一次原 standard CI；只有确切 harness 失败才允许最小已审修复重试，保留失败、不盲跑。此前生成切片额外 CI 偏离原阶段门槛，本轮先明确以下范围变化后实施，不沿用自动追加 CI 的假设。

同一现有 Windows job、签名安装 Edge、原 SDK/保护参数、原 helper/150 秒 Node 上限、原八文件输出白名单及 2MB 每文件上限不变，无新部署、LIVE、身份/权限扩展。测试建立的是本地合成前置授权；产品的生成过程不创建 Principal/Grant。原 agent33 交互与布局检查保留，原38 CSV 检查保留。新 registeredGeneration 独立结果，不合并旧计数。现有 agent-desktop.png/agent-narrow.png 两成功名本轮归档新的生成里程碑，metadata 明示 scope；不留旧 agent 图片 hash 冒充新图。原成功 agent 图片仍留在其原 CI。原失败名继续承载真实失败页面。

## 冻结合成数据与预期

- source：原 fixture.csv `amount\n1\n2\n`，源应用是现有已授权 initial registered CSV app。浏览器实际确认内部快照、创建实例并提交 Run，冷现有 Worker 真执行，可信成功结果应为3。
- target：不同 CSV `amount,quantity\n10,7\n20,8\n`，另一个事先获授权的 initial CSV app/runtime。用户从 options 明确选择此域；服务端新草案继续共享此现有授权，quantity 新结果应为15（amount 为30），不是源答案3。
- fixture 不预造 registered 源成功 Run、衍生候选、版本确认或新结果。无可用目标的独立项目只 seed 一个初始 CSV app，让浏览器实际建立成功 Run后验证 NEEDS_INPUT，不为满足生成自动补权限。

## 真实用户路径与负例

通过可见导航和控件：初始CSV→精确快照/默认未勾选→人工勾选并确认内部Release→独立instance→sourceamount持久Run→冷worker→回读SUCCEEDED→“将这次任务保存为可复用草案”→可信proof/options→明确已有target/名称→真实POST服务端生成→新app来源链→quantity快照/确认Release→新instance→新Run/冷worker→15与源3不同且引用/版本可回读。截图展示生成草案来源、不同材料与新结果；desktop及390窄屏检验布局及实际像素，当前捕获范围之外不扩大验收。

负例覆盖丢已接受回执的原key手动恢复、旧options响应跨app/project/identity、主体/project拒绝、空目标状态、服务端产生的第二草案 mutable candidate+fingerprint 篡改、target与source现有Grant撤回后当前/缓存读取或生成拒绝，清空受保护内容。完整权限/身份记录在生成前后应不变；人为撤权单列预期变化，不恢复/继承权限。所有negative使用合成项目，原AT02/生产历史不改。source PARTIAL/FAILED/UNKNOWN 的后端验收边界不提升。

每个新capture阶段复用原实际PID/token审计；只有真实保护检查通过才能归档新图。capture fonts.ready/有界正常scroll仍非旧空白归因；旧空白根因UNKNOWN，不以本轮PNG成功称已修特定原因。原 runtime visualReview NOT_REVIEWED保留，人工actual original像素结果单独记录。

## 阶段记录

1. 本地API/DOM夹具及独立静态审查：进行中，无native PASS预写。
2. 普通push精确源码及唯一standardCI：等待第一阶段完成；不混未审代码。
3. 实际stdout字节/SHA/PNG和独立像素复审、失败/cleanup记录及最短使用说明：待真实CI终态。

完整P-B、目标语义、Win11/F1/AT02、模型自主生成、发布保持未签收；此阶段只验真实registered CSV用户入口。

第一阶段实际结束：fixture/API专项5PASS，新直接真实HTTP-DOM专项1PASS（functional source3→newquantity15/全部负例；不是native）；root合并fixture+新DOM+旧agentHTTP+现生成HTTP **43 PASS/0FAIL**，91.89秒。旧agent HTTP/jsdom22checks另实跑PASS。独立fixture审核5PASS，并在旧agent腐化/撤权后实复现CSV生成兼容；完整native导航/capture/安全/partialFAIL静态审核APPROVE。新DOM wrapper曾把实际id写成run造成一次KeyError，修复后实际专项与合并闭合，未运行任何CI。源码hash及证据在registered-run-browser-20261006；本地API/DOM不能替代下一真实Edge阶段。README现链接最短运行说明，原完整P-B门不提升。
