# 两项修复及七请求证据桥接：实施前有限意见

**拟议修复合适；无需机械重跑七请求，但证据复用必须按以下条件收口。** 当前第二批仍在途，本意见不预判其终态，不把源码推理记为运行PASS。

1. **公开offline入口前置拒绝。** 在_dispatch的_binding之后、任何source/history/journal/provider操作之前，生产Worker只允许原受信_business continuation：exact ProductionTrialBinding、与worker.pa_trial同一绑定，沿_dispatch_business原校验。不能只判断_business非空、不能靠token匹配拒绝；两个公开offline函数不得借caller ALLOW或server-fixture loader走生产Store。普通synthetic入口保留原实现。新拒绝测试应以函数调用窗口核source/journal/adapter均0，构造Worker之前已有的验证不混计。

2. **原Run mode为独立防降级锚。** 从已核owner/slot的原Run frozen.mode取标量，缺失/未知拒绝。live只能配exact生产Core Attempt/version/mode及生产capture provenance；mock保留合法policy-only、无Core Attempt的旧synthetic历史；存在Attempt时仍核MOCK/非生产，保持原字节SHA、完整capture重算及EMPTY独立派生。不能仅依赖capture自述provenance，也不能将删Attempt视为恢复旧synthetic条件。

3. **静态桥接应精确限定。** 七请求所在freeze与最终freeze的产品变化只限上述前置拒绝和_capture来源校验。对所有其他产品路径逐字或AST核不变，尤其private continuation、_derive、wire guard、六镜像/BodyArchive接收写序、settle、lease/deadline、typed/CAS及原terminal尾核。新SQL只读mode锚虽不改业务效果，也不能以桥接宣称最终PG时延/租约负载已重验。

4. **正例向量必须来自已闭合原件。** 只有七请求实际最终PASS才复用；从其原55表JSON逐项核7个Attempt的原Run frozen.mode=live、Attempt.mode=LIVE、exact生产marker/version、原contract/approval/account/worker/Run/Attempt/wire identity与capture/seal/provenance一致。这样才证明新增mode条件对该次已观测正例为真；不是声称两个版本对所有输入等价。不得执行新产品函数处理旧记录来补造七请求成功。

5. **最终源单独实测变化范围。** 针对公开offline前置拒绝、旧无Attempt重复/history和接收时来源拒绝仍保facts运行必要节点即可；不扩旧8/9/19矩阵。旧七请求PASS、较新针对节点、全部失败各自保留source/input hash/JUnit，合并唯一节点与执行数时剔除重复，不称最终freeze七请求fresh PASS或单批全绿。

测试里的固定source/环境/资格patch和MockTransport只证明生产形状的软件接线；不安装真实账户来源、不授予LIVE、不扩大旧资格。需最终原件及精确diff后再核桥接成立。本次未读取在途结果，未执行产品/测试/DB/网络/模型/Git命令；仅写现有未封存审阅目录。
