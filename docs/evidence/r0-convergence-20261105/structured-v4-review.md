# v4结构化阶段输出

9c9d4985正式Run run_a324506e301f4b85a8160a59632376a5已使用同步4096适配器到达check_candidate响应，但finish_reason=length。实际用量1987+7442=9429 tokens；候选响应completion4096，reasoning_content长度12144字符、参数长度0。没有有效候选；旧响应/账本不重发、不退还。两个会话exit0/PG停止。只保存计数，未输出推理正文。

新增natural-checked-candidate4096.v4：保留v3声明函数映射，读取阶段不改thinking默认；仅check_candidate和最终无工具候选阶段在冻结wire中明确thinking_mode=false。完整Goal、实际读取反馈、模型选图/样本和原严格编译校验保留；不注入固定候选，不增tokens/请求/期限。

sender白名单要求准确新协议/阶段及false字面量，缺失或额外字段仍拒绝。旧v3不新增thinking_mode，原wire/捕获回读保留；旧失败不能被新版本改认成功。

17项结构化阶段/旧wire、别名、预算/Core模拟生成和适配器回归通过；新增严格缺字段断言后定点2项再次通过，重复节点不累计。尚未建立新资格/同源包或真实v4请求，不能推导候选成功。下一步按该目标封存并验证生成闭环。
