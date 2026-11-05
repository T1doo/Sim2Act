# 正式生成适配器额度同步

2f2398c0正式Run run_bc3d04e1d3eb46b3834b65c3754f6752完成首轮read别名接收和绑定材料读取，2024实际tokens。第二槽已保守预留/标记，但模型适配器设置仍1024，与冻结wire的4096不符，被原LIVE_BLOCKED一致性检查拒绝；没有该槽接收体。保留unknown用量和可能发送标记，不退还、不重跑。两会话exit0/PG停止，见managed-natural-wire-v3-check.json、wire-v3-journal-diagnosis.json。

修复：每个生成请求按generation_output_tokens从冻结消息推导的额度构造InternModel设置副本，传输、token、mode、model、quota、期限和其他设置保留。Worker.s与应用运行限额不变。原sender逐字段一致性谓词抽为_check_business_provider并继续在原调用点执行，没有删除预算等式或放宽范围上限。

验证：初轮17项适配器/命名/预算/旧4096协议测试通过；抽出原sender谓词后最终7项通过。包括旧1024适配器对4096 wire必须拒绝，修复适配器通过同一谓词，Source仍拒绝4096，Worker默认不变。重复节点不累加；均为受控测试，无新增模型请求。

当前源码尚待新资格和同源包实测。此结果只说明发送前设置接线修复，不证明有效候选、Source/Cold或R0通过。
