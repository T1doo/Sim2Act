# 4096首次正式范围与required模式

9d5ef2d9846c2fe63e93accc8c0eb1758394409f桌面运行包SHA256为56cffe7dd3a0de840bbc921c4938626ebfa3cb960c11c7ce18e99c761d69a8b7。包内两条原资格检查通过。

新范围、readiness与冻结协议均确认profile=pa-natural-output4096.v1 / natural-checked-candidate4096.v1。Run run_0fad3f4074e5478da1a4981402ca90b7在首轮拒绝：模型响应finish_reason=stop、tool_calls为空，未符合唯一绑定读取要求。实际用量1966 tokens，未执行读取工具或生成应用。两个会话exit0、PG停止；失败和原响应不改写、不重跑。

另依据用户API测试授权，做一次独立有界合成协议探测：tool_choice=required、最多512输出、不执行工具、不接触业务材料。实际返回resource.read工具调用，365总tokens。该探测不走正式七槽控制器，不当作应用验收；也不能据此断言所有具名调用都不支持。

新增natural-checked-candidate4096.v2，只对新冻结生成选择required。每阶段仍恰好一个既有read/check工具，发送端仍逐字核对tool_choice与冻结wire；旧v1继续使用原具名对象，历史消息不改。读取1024、候选/最终4096，Source/Cold及总预算不变。

10项工具协议/旧版本wire区别/预算/准备/Core模拟生成回归通过，见natural-required-v2.xml。当前v2尚未封存资格、打包或真实执行；不预签有效候选或完整P-A/P-B。原始记录managed-natural-output4096-check.json、natural4096-journal-diagnosis.json、intern-required-tool-probe.json。
