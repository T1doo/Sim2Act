# 自然生成v7：指定阶段函数

33d175f3/v6实测收到2次真实响应。读取返回结构化read调用；下一次返回普通content，内容以`[tool call] check_candidate(...)`开头，没有tool_calls，finish_reason=stop。原Worker正确拒绝PERMISSION_DENIED/Actual checker tool must precede final candidate，未执行检查或创建应用，原范围和响应保留。

官方Chat Completions文档支持以函数对象指定必须调用的名字：https://internlm.intern-ai.org.cn/doc/docs/Chat/index.html?id=1731617612397 。这不证明本轮服务部署的实际兼容性，需实测。

新v7仅新合同使用当前stage的唯一wire函数名字read/check_candidate，不允许切到其他工具；read和check阶段使用服务默认思考配置，final保留thinking_mode=false。v6端口规则及原始读取位置索引继承，旧v1—v6 wire保持原设置。调用、输出、总预算、期限、真实工具回执及最终严格检查均不变。不会把自由文本改写成已执行工具，也不回写旧失败。

25项合成检查PASS，含指定名字、未知工具、v6原required模式、实际Worker预算与无效候选拒绝。资格封存、同源构建和真实模型结果另行记录，不将这些检查计为P-A通过。
