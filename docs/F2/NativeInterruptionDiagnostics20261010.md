# Native interruption diagnostics — 2026-10-10

此轮先解决 Windows pytest 中断后丢失失败节点、断言和活动节点的证据问题。既有 754 run38024430136 留下未完成 JUnit 的26 failures，但没有节点详情；同473源码后续6eb run38025760656也因15m0s作业上限取消，Report只输出 `NOT_RUN: no engineering JUnit`，artifact为空。完整原日志私存并保留SHA256；两次运行不能归为通过，也不能把取消前失败归因为取消本身。

精确诊断源码 `88cb3c64b5dcbaf3df7183ebbf72773547585e15` 已普通推送至 `dev/native-interruption-diagnostics-20261010` 并快进 `dev/f1-foundation`。360冻结文件 Git/worktree匹配，69个src产品文件与 `47388f573746daa27f8d5790ca358eef91378ad5` 完全相同。新增std-library pytest观察器，Test.ps1通过显式可选CLI启用；每个节点开始和失败即时flush到Actions日志并逐条关闭JSONL，always Report恢复失败、活动节点、未开始数量和不完整状态。pytest原选择、退出码、fixture效果及严格Ruff/mypy/R0门保留。未改workflow、依赖、900/240/150预算、数据库角色、安全门或产品。

独立首审d8 BLOCK：Basic授权值及带空格password后半在JSONL、诊断stdout、Report三通道泄露；全部材料为合成值。其他3场景15检查通过（真实硬杀、选择/fixture/退出码透明性、不完整尾部与缺失日志）。d8完整失败材料封存，不能改写成通过。

88cb脱敏增量只修改诊断器redact与其测试。含凭据字段整行余部隐藏，完整引用多行值也消费，避免源码转义和求值文本的层次差异。独审新6类实际失败材料27检查通过，三通道覆盖Basic、空格、转义、未引用、多行、JSON键、大写PG URI/Bearer；结论 `LIMITED_PASS` 仅适用该增量。其余358冻结文件与d8一致，69产品同473。作者new lifecycle4+existing phase5为9PASS；显式外层观察器4PASS，collected/start/finish4、exit0；fullRuff与mypy55通过。作者初始collection error、marker framing2FAIL、first quoted delta2FAIL全部保留，未挑选隐藏。

精确88cb原生 [run38027015081](https://github.com/T1doo/Sim2Act/actions/runs/38027015081) 因原作业上限取消：2234collected/856started/855finished，791PASS/26FAIL/38SKIP，活动节点1、未开始1378，exit2、suite_complete=false。Setup/smoke/Report/Cleanup成功，EdgeSKIP。26份即时失败详情全部恢复：25份Node驱动不能导入jsdom，1份CSV上传read_text经LF规范化、断言却hash Windows CRLF文件。根因及修复另见 [工程前置条件修复](NativeEngineeringPrerequisites20261010.md)。旧754的26个F位置与本轮26节点位置完全一致，10份相关测试源逐字不变；这一对应属于推断，旧断言NOT_RECORDED原状态不改。两版本之间还有既有Report history优化，不能宣称所有历史产品源码完全相同。

证据：[README](../evidence/native-interruption-diagnostics-20261010/README.md)、[失败账本](../evidence/native-interruption-diagnostics-20261010/FailureLedger.md)、[d8首审](../evidence/native-interruption-diagnostics-20261010/independent-d8-blocked/FINAL_REVIEW.md)、[88cb增量复核](../evidence/native-interruption-diagnostics-20261010/independent-88cb/FINAL_REVIEW.md)、[实际26份失败](../evidence/native-interruption-diagnostics-20261010/native-88/result.json)。独审分别按39/19路径SHA256白名单复制；作者143路径及其白名单保留，排除私存完整6eb CI日志（有精确摘要与hash）。公开证据207条目的首次核验回执封存于publication-review；其后补充实际88cb终值，最终清单重新计算。两份完整Windows原日志私存，公开JSON即时诊断与规范化摘录另记hash/范围。

历史 Report GET idle6 与 PG resources-history Future10 仍 **OPEN**。HTTP200损坏响应提示限制、Windows900/Edge240/Node150未验收保留。PROJECT `PENDING/BLOCKED_PARTIAL`，overall `NOT_ACCEPTED`，LIVE=0、真实模型调用0、正式发布关闭。此轮无main修改、强推、部署、凭据/安全网络修改。

日志字节补充：旧私存6eb/88全文经CRLF→LF并额外添加1个尾随LF，旧白名单字节仍保留。原connector运输CRLF UTF8原件另行精确保全，两类哈希及逐字节变换核验见[log-byte-provenance](../evidence/native-interruption-diagnostics-20261010/log-byte-provenance.json)；不改变失败或数量。
