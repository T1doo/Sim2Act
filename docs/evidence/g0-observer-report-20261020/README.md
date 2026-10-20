# 磁盘观测口径修正及 G0 离线设计

基线 `337569ed731bb806a25f29328a8119e7b40cf2b4`。本轮业务窗口和真实 Mock 调用均为0；未创建grant、未运行 --describe/--execute-grant、未读取归档DB。产品src、租约、额度、deadline、auth与事务结构均未改。

原报告的 interval_seconds=0.1 是配置值，不能代表实际频率：父循环每轮先sample，随后select最多等待0.05秒，事件可更早返回，收尾另有sample。第二窗口6795次/342.200031s≈19.8568Hz只是整轮粗比率；原件没有完整采样时间序列，无法补造准确间隔分布。原receipt和全部失败证据原样保留。

本次选择**如实报告，保留原调度规则**：configured_interval_seconds=0.1且configured_interval_is_scheduled=false；单列selector_timeout_cap_seconds=0.05、每轮及收尾采样policy，并新增实际采样完成时间的间隔min/max/mean及观察频率。它们是测量值，不是固定周期或硬配额承诺。parent仅将原check→sample→select提取为可测函数，原超限/扫描失败、截止时间和清理规则不变。没有降低采样频率，没有声称这会解决G0期限。

[OBSERVER-UNITS.log](OBSERVER-UNITS.log)：6项fake clock/selector测试验证空闲20Hz、事件更快、收尾大间隔、零/单次/同时采样、原deadline截断、扫描失败在select前传播。完整[PURE-UNITS.log](PURE-UNITS.log)共42项，38通过、4旧原生案例skip；包含3项纯数据深层字段/别名回归和2项临时SQLite写锁/CAS机制测试。[ruff](RUFF.log)通过。既有纯CLI测试仅以非法--child参数验证BLOCKED，不启动产品或分配业务输出。

[OBSERVATION-AUDIT.json](OBSERVATION-AUDIT.json)保留历史口径审计，原G0仍为31.125280s，结束超过原lease约1.109072s；342秒整轮包含原journal每次reservation至少60秒的节流。五个原区间的5620次check/5685次input_key与对应完整扫描调用链已定位；没有CPU profile，不能断言其全部wall时间的CPU归因。[STANDIN-MEASUREMENT.json](STANDIN-MEASUREMENT.json)是100次已存primitive数据完整序列化/SHA分解，不是生产图性能对照，不预测提速，不重做删SHA/提前标量校验或此前失败方向。

[DESIGN.md](DESIGN.md)给出可审候选及未满足条件：锁外不可变完整快照、提交前新事务中的全读集/授权见证及原期限CAS；旧guard不能跨事务复用，单Run version CAS不够。当前先保留生产路径，等待覆盖性和原子性证明，不直接拆事务。Cold RUNNING/RECEIVED是诊断BaseException保现场，不能据此推断生产漏收尾。

[独立审查](REVIEW.md)仅复跑指定9项观测/纯数据回归；SQLite2项只静态读，未执行产品/Mock/G0/launcher。[CHECKS.json](CHECKS.json)记录命令、冻结代码hash和旧证据55份不变；[MANIFEST.json](MANIFEST.json)绑定本目录所有材料。最终提交及远端状态见最终回复。
