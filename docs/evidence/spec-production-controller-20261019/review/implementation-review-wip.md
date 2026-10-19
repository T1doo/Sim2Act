# SPEC生产controller WIP有限静审

本次发现一项P1接线阻断及一项P2到期检查窗口，均已即时通知root；没有执行产品或测试。完整原观察条件与当前源码指纹见[wip-findings.json](wip-findings.json)。

1. **P1：生产provider被旧mock条件拒绝。** `_dispatch`在record_attempt之后，无条件对_business覆盖成合成token并要求mode=mock，生产必然无法到达adapter。最新源码已按production分mode/token，保留原wire/model/quota/caps；这一静态矛盾已解除，尚非运行通过。
2. **P2：长证明后的到期尾核不足。** source原本在`_qualified()`之前核时间；admission及terminal的Run/lease核也在后续完整证明之前。已看到source在资格hash后重验、admission在source后核context/source deadline。最后读取的terminal仍在完整phase/history后仅_binding，应在所有证明完成后再核原RUNNING lease、contract/source期限和stop；不续租或放宽预算。等待root最终代码复核。

所读范围中，新ProductionTrialBinding与旧exact Journal/PATrial分支分开，默认resolver仍缺源拒绝。MODE/marker、归档、旧原键history、固定Store及接收DENY保存事实均有接线；未发现另一个已确定的隔离或死锁问题。实际sender._loaded沿project/account/ledger后Run锁，未误报反向锁序。PG insert原本已有dialect分支，早期只读误推更正仍见observer-correction.json。

这些是WIP源码意见，当前仍由root编辑，不是freeze或运行资格。未执行产品、测试、数据库、网络、模型；只允许的只读Git diff，无远端/auth操作；仅写本新review目录，旧sealed不动。
