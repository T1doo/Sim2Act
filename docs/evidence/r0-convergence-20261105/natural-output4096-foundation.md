# 正式P-A候选4096：合同与策略基础

fbfe58c4实测Run为run_a8b6d615f27e497a9e984b5edbffce82。新期限实现下第二响应已完整接收，输出1024、finish_reason=length，截断后未形成工具调用，任务仍WAITING_RESOURCE/OUTCOME_UNKNOWN。两次已知用量为1998+4321=6319 tokens；未重发，两个会话exit0/PG停止。见http-deadline-journal-diagnosis.json。

依据用户既有新P-A单次4096授权，开始接入新的显式profile：pa-natural-output4096.v1。当前仅实现合同/账户要求/策略账本投影，发送路径尚未开放4096；UI、prepare、readiness、API、Core预留、wire校验、历史读取仍需一起完成后再冻结。

- TrialContractV2新增可选generation_profile；旧合同缺省时序列化完全不增加字段，保留原指纹和期限。新profile必须形成不同合同指纹并单独批准。V1/P-B没有此字段。
- 账户要求投影绑定同一profile；未配置时不增加序列化字段。
- 新profile仅Generate的保守账本envelope按4096计算；Source/Cold保持1024。实际请求仍需后续按阶段检查，投影不是权限。
- 每Run64000、三阶段192000、3/2/2请求数保持。显式维持原7168总已接受输出约束；本轮没有将它放大到16384。拒绝/未知用量仍记录和停机，不伪装接受或退还。

验证：初始配置/旧期限组合15通过；更新后的配置/策略组合9通过，有重复节点不累计。包含旧合同完整序列化一致、新指纹区别、账户投影、Generate与Source/Cold区别、旧scope不接受2048输出、新scope接受受限2048，以及总已接受输出超过7168拒绝。均为合成配置/SQLite受控策略，不是4096真实发送或正式P-A通过。

当前是分阶段实现，不能把合同元数据存在当作新预算已可执行。下一步完成预留与发送的同一wire预算绑定，补权限/恢复反例，然后更新资格和新包实测。旧未知任务不改绑或续期。
