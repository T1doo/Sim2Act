# Registered CSV 生成入口真实浏览器验收

精确源码 `447b597fefd6c2a191ef4e9ff6d4bf2f0c06d3d5`，[唯一标准 Windows CI 37476996252](https://github.com/T1doo/Sim2Act/actions/runs/37476996252) SUCCESS，未重试。既有受保护 Edge 实际完成初始源 CSV amount=3 → 服务端生成草案 → 明确选择已有授权的新 CSV → 人工核对内部版本 → 新实例/冷 worker 的 quantity=15/resultVersion1。fixture 未预造成功源 Run 或衍生候选。

原38项、旧agent33项及新生成29项分别PASS。新项包含手动原key恢复、来源篡改、撤权、旧响应、跨主体/项目、空目标及390窄屏；完整Principal/Grant记录在正常生成前后不变。Windows工程564PASS/2SKIP/2warnings，跳过项不计通过；本地真实HTTP-DOM/API合并43PASS。实际capture两次及最终PID/token保护检查PASS，PID差集并非严格页面到进程映射。

[终态与来源ID](result.json)、[CI原终态](ci-summary.json)、[原agent JSON](native-agent-results.json)、[原legacy JSON](native-browser-results.json)、[stdout提取摘要](native-extracted-summary.json)、[独立实际像素复审](independent-pixel-review.json)。原字节仅通过既有stdout白名单恢复，PNG仍在原Actions stdout和本机临时解码目录；没有另上传PNG或恢复包。原runtime visualReview NOT_REVIEWED不改写；主审及独立审实际原图均接受本次健康生成里程碑的历史展示范围。

操作见[最短使用说明](../../F2/RegisteredRunQuickstart.md)：预览列与下方新任务列分别设置，每次提交前明确选quantity；历史quantity15不因新任务表单amount而变化。截图之外JSON不按像素宣称全文可读。

Report/Cleanup成功，原回执为“Owned API/worker stopped; database service and data preserved.”及“server stopped”。本地wrapper初次误用run字段造成KeyError，修后43项通过；第一阶段证据保持原样，未借CI补未审代码。无LIVE、新权限/身份、表/DDL或正式发布。Win11、完整AT02/F1、语义与完整P-B仍未签收，旧窄屏空白根因UNKNOWN。
