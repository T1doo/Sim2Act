# 第二批闭合与BodyArchive静审

原JUnit实际2PASS/1FAIL，outer289.064秒，pytest285.32秒，155输入映射前后相同。正例只有3份GEN合成交换；Source inspect200但RUNNING、无steps/Attempt/结果，尚未完成Source/Cold，不能作为七请求PASS桥接。原件哈希及逐节点记录见[机器记录](closed-second-and-body-archive-review.json)。

**确定P2：BodyArchive仍误标offline。** natural_source_archives允许LIVE写入，但BodyArchive仅定义OFFLINE_MOCKTRANSPORT，_body沿用默认。需按受验原Run/Attempt mode+marker区分生产来源，保留旧默认；原REQUEST重构、RESPONSE和_read必须同样绑定，PB原MOCK读取门不可顺带扩大。

Source具体失败尚不能定因。text_workflows处理DomainError后，natural_spec_runtime.fail_owned在原lease过期时会直接return，因此error=null不代表没有异常。GA读取段仍仅对旧JOURNAL_VERSION复用完整候选/来源证明，新production marker重复完整读取是静态耗时候选，必须由新被动异常/耗时证据确认；本次未将其写成已证实租约根因，也不建议改原lease/RPM/deadline或重发旧Run。

最新两项后续修复已静态闭合：生产公开offline入口在source/journal前拒绝，capture按原Run frozen.mode防降级并保留旧policy-only无Attempt历史。未见另一个可单凭源码确认的Source mode阻断。

本人只读已闭合非DB日志/JSON及源码，未开DB、未运行产品/测试/模型/网络；没有读取其他在途输出。目录继续未封存。
