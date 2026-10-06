# 本轮观察到的失败与修正

以下为本轮工具输出及独立审查报告的事实摘要，不伪造未保存的逐条原始日志。最终永久负例覆盖相关边界；没有通过重跑CI取代修复。

- 初版budget9PASS未覆盖独立发现的4项：max_requests忽略、authorize别名篡改wire、stage实际usage超额、False/0 schema比较。实测可被接受，已修并独立复验关闭。
- scope更窄的read-only实验集成首版protocol27PASS1FAIL；测试误用read+aggregate范围，修成实验只读范围，未放宽budget。
- budget新增测试直接修改frozen Settings造成FrozenInstanceError（11PASS1FAIL），修测试为replace。schema测试首次修改共享TOOLS引用导致16PASS1FAIL，改私有copy，并固定可信工具schema指纹；不把这些测试错误当产品攻击。
- 协议独立发现合法候选替换+同步FP、null source attempt、halt后纯工具cold旁路、identity True→1；已加持久acceptedresponse→candidate receipt锚点、typed attempts/canonicalFP、执行admit停止门并独立实复验关闭。合法optionalnull保留RAW validated JSON，不改变实际回执绑定。
- Linux mypy平台stub初报msvcrt四attr错误，改仅Windows分支动态加载，运行逻辑不变；Windows行为仍未实测。
- preflight初ruff仅unused loop variable，修名；8完整MOCK wire始终0external。

最终budget19PASS、protocol39PASS；独立合并58PASS；root相关回归145PASS1SKIP，警告为已有Starlette/httpx弃用。最终四包语义UNKNOWN，owner未签；协议测试中的SUCCEEDED/PASS只来自明确TEST-only fixture verifier，不是F1状态变化或真实验收。
