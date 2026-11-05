# 85b8b619 真实生成接线与失败诊断

本轮用已授权的独立 PostgreSQL 和 Intern API，执行一次冻结包的有限字面应用生成。未操作原生窗口。

通过的接线：同一后台会话内准备 v3 范围、明确批准、按准备键和批准键只读恢复、提交绑定原批准的 Run。不需要静态批准 ID 或后台重启。原期限未续期。

生成未通过。Run `run_d2ad1fe43d0342c5a67ffcc81a187759` 为 FAILED，未创建应用。3 次实际请求共 15655 tokens（3955 + 5136 + 6564），读取1024、候选4096、修复4096，保守预留总和61601，未超过64000预算。

第一次候选 JSON 语法不完整；唯一一次修复得到完整 JSON，但将输出 `source_hash` 指向 data binding 的 `hash`。数据绑定只提供 `resource_id`，因此 preflight 按原规则拒绝 `Source field missing or not guaranteed`。原提示已要求所有输出来自同一动作步骤，但模型没有遵守。

下一步应在新版本输出协议的候选 JSON Schema 中明确输出映射的 source/field 约束，并保留旧协议序列化与校验兼容。不要人工修改候选、补造 data.hash、放松 preflight，或把失败签成可复用成功。修复需要新冻结版本再验证。

本次 supervisor/API/Worker 全部 exit 0，收到 clean stop 回执，自有 PG PID 文件消失。诊断仅只读数据库，并再次停止。观察脚本曾在后台已经退出后得到连接拒绝；随后同一原执行句柄确认任务已失败且退出完成，没有因观察失败重启或重新提交任务。

原始记录：`managed-pa-consent-integration.json`。它证明接线可用和失败安全退出，不证明生成稳定、自然 P-A/P-B、UI-ready 或 R0-ready。
