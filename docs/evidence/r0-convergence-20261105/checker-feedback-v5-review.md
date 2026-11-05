# v5已知检查输入的失败反馈

仅新natural-checked-candidate4096.v5：已收到、名称严格匹配check_candidate、参数为合法JSON且根精确为candidate一键的调用进入原只读检查工具。candidate字符串或其他无效候选不成为有效对象，不解码修补、不补字段，原check_report返回INVALID_MANIFEST/FAIL。未知名称、坏JSON、额外根键、绑定读取或权限错误仍拒绝。

与旧版的差别仅在传输协议判断和诊断机会：完整工具调用不是有效候选的证明。检查仍产生FAIL，业务写入0；最后一次模型响应必须重新通过完整Goal/source/recipe/sample编译和引用校验才能生成可确认的PARTIAL候选。请求仍至多3次，预算/期限、确认和Source/Cold边界不变；不会重发旧未知任务。

旧v4捕获仍走原object输入判定，原字符串输入UNKNOWN不被改认成功。捕获重验从原冻结协议取版本，assistant原文/参数/哈希和检查意图保留。

测试初轮17通过；补充最终仍坏的反例后三个Core边界定点通过，有重复节点不累计。覆盖正常三请求、无效字符串→实际checker FAIL/0写入→模型末次修正→严格PARTIAL，以及末次仍坏→FAILED/无结果/不加第四请求。该模型由MockTransport合成，不是修补真实响应；正式范围尚未运行新版本。

当前源码需要重新封存资格/构建同源包。旧v4真实失败及完整接收记录保留。P-A实际闭环和P-B性能尚未签通过。
