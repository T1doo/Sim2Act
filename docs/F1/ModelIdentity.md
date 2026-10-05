# F1 书生返回模型标识兼容规则

独立接入验证向父任务报告：官方模型发现 ID 为 intern-s2，实际文本/工具成功响应的 model 字段为 Intern-S2。本文记录该已提供证据；本次修复未访问账号、未发真实请求。

策略版本：`intern-s2-returned-name.v1`。

| 请求模型 | 允许的原始返回模型 | 规范化值 |
| --- | --- | --- |
| intern-s2 | intern-s2 | intern-s2 |
| intern-s2 | Intern-S2 | intern-s2 |

使用明确白名单，不调用通用lower/casefold、不去空格、不模糊匹配。请求模型配置仍只能为原 canonical intern-s2；未知/异型号、缺失/非字符串、未确认的全大写 INTERN-S2 等继续 MODEL_OUTPUT_INVALID，验证失败不派发工具。该规则只处理返回标识，不代表权重版本、工具结构、权限、预算或目标验收已通过。

Worker 与未知请求 record_response 共用同一规则。适配器没有其他返回模型大小写判断，继续保留原始响应；请求端仍发送 intern-s2。离线 probe 以 MockTransport 合成 Intern-S2 返回，并显式检查兼容规则；模型列表解析仍保留上游 id，不用返回名别名替换发现 ID。

Attempt 原 request_model 与 response_model 保持请求值和原始返回字符串，不用规范化值覆盖 response_model。parameters.model_identity 保存 requested_model、raw_returned_model、normalized_returned_model、normalization_policy_version、enforced/verdict；预约时保存 model_identity_policy_version，收到成功或失败响应均保留审计信息。缺失/非字符串标识按缺失字符串值记录 null 并拒绝。模型身份判断通过后，工具参数、资源范围、授权、独立回执和预算仍分别检查。

LIVE 配置分支的零网络回归只使用 SYNTHETIC token + httpx.MockTransport；外层证据明确 FAULT_INJECTION，不是实际账号 LIVE 验收。默认 MOCK 行为仍为工程夹具，身份元数据标 NOT_ENFORCED_SYNTHETIC；人工导入 MOCK 响应仍只能是既有 MOCK-intern-contract。人工响应保留 USER_SUPPLIED 来源、未知原用量和暂停规则。
