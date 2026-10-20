# 双求和独立逻辑：代码首轮独审

当前不能签最终代码 ACK；发现两个 P2，均已发父侧。无 P1。本审只读源码，产品导入、测试、Worker、DB、模型、PB/G0 执行全部0。当前不是冻结版本，不将随后采得文件 hash 冒充最初缺陷 diff 的精确快照。

1. 旧单列非法列从原 INVALID_INPUT/400 改为 instances.require 的 VERSION_CONFLICT/409，属于不必要公开错误合同回归。父侧已确认将在当前旧字节批次结束后恢复原 code/message，并增加严格400回归。
2. csvLogicPlanSeal 只核 public authority 双 schema、canonical composition/input 与 manifest 全局预算，generic csvDagCompositionSeal 不核各 action.limits/output_schema 或完整 manifest 双终端 schema/outputs。静态可见：改单 sum 节点预算或第二 sum schema 并重算 p.plan_fingerprint，现有校验仍可接受并先写 i.accepted，随后正确 GET fp 不等导致 UNKNOWN；恢复继续使用坏 accepted 对象，不能读回正确结果。建议在逻辑专用 seal 中纯构造冻结 cap/3、规范两 sum 完整 schema、精确输入 enum、双终端输出 keys/mapping 的期望值并完整比较，先拒绝后才缓存。需要局部页面篡改已重算指纹的 POST 回执并验证原 key 恢复可成功。

另新私名归一化夹具 uppercase step ID 不符合现行 lowercase IDENT，父侧已改合法小写；它不是产品缺陷。

其余当前源码未见新增阻断：专用 consent 在 mint/load 都按 audited version 重验；私有源 schema 依原sid核验、public只canonical total_a/b；严格双映射与共享目标schema门；derived prepare和restore逐节点完整canonical；marker不可降级；post-mint沿旧immutable Release/approval与Run scalar audit，不新读旧resource/result/context/operations；原独立authority撤销/TTL/target/frozen cap/事务守卫仍保留。最终需两P2修复、精确冻结字节及作者实际测试原件再核。
