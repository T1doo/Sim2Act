# 自然候选工具约束协议

新增natural-checked-candidate.v1，仅用于新natural_spec生成合同。旧合同缺省output_protocol仍保留原消息及wire。新协议在resource.read阶段和spec.check_candidate阶段分别通过tool_choice指定当前唯一注册函数，并要求紧凑JSON；最终无工具阶段不增加tool_choice。不改变1024输出、七槽、请求数、总预算或期限，不注入模板候选或固定模型答案。

依据为书生官方Chat API文档，支持指定function对象的tool_choice：https://internlm.intern-ai.org.cn/doc/docs/Chat/ 。实际接口是否按期望产出有效候选仍需新冻结包验证，不由文档或Mock推导。

发送端白名单仅在原generate阶段、冻结初始消息含准确新协议和natural版本、当前工具为既有read/check之一时接受精确tool_choice。改成auto或其他函数会拒绝，其他额外字段仍拒绝；预留与发送共同使用原body serializer。读取/编译/确认/保存的权限、来源与语义UNKNOWN不变。

受控验证7个唯一节点通过：2个阶段工具选择、1个最终/未知工具拒绝、1个旧自然合同生成后确认、1个旧字面合同确认兼容、1个自然生成及实际模型节点/原子清单运行、1个未知发送原键读取不重发。全部合成模型、无真实网络调用。见natural-tool-protocol.xml、natural-tool-compat.xml、natural-tool-flow.xml；重复执行节点不累加。

此前真实响应截断发生在正文（1024输出tokens、3660正文字符、0推理字符），不能误归因为推理消耗。新工具约束并不保证足以容纳所有合法候选；仍需实际验证，不擅自改旧七槽合同。此工作树版本尚待新资格清单及同源包。
