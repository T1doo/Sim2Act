# E18 合成预览写隔离证据

事前范围 4c545ef24de3c63cf733c2d81ec6301e15fc10cf，基线 727d023。原 V5 AT17：预览中执行写入，只有预览 namespace 变化，真实实例业务数据和权限不污染。本轮只关闭 **AT17_SYNTHETIC_FIXTURE**；[阶段门审查](../../F2/StageGateReview.md)保留原正式 AT17/F2/P-A/P-B/AT10/AT20/F1/Win11/protected-browser 未完成项。

`tests/preview_write_fixture.py` 是 **FAULT_INJECTION**：只允许显式 test_only Store + tmp SQLite 文件或 test_[32hex] PG schema；独立测试 MetaData 两表由 fixture Setup 建立，不进入生产 meta/CLI 迁移，不由 API/worker 初始化建表，不注册工具、不新增生产 Grant 或业务写入口。唯一生产变更是保存已有显式 test_only 标志，默认 False。

监听真实 `apps.preview` 持久事务的精确 app_previews INSERT，只在 SUCCEEDED 时同 Connection 执行固定 note 记录和 receipt INSERT，均实际同事务 SELECT 读回，再可注入提交前故障。新 engine/连接独立读回，note 不是 CSV 求和/原答案或 cache。fixture guard 验 namespace/owner/project/app/candidate fingerprint、禁止 instance/release target；它验证测试 adapter 的边界，**不证明尚不存在的生产 writer gateway**。production response business_writes=0 仍指生产工具链，不把注入写算成正式能力。

种子创建真实内部 Release 和两个有类型化 result 数据的 instance。前后查询全部生产 meta 表，仅排除合法 preview 历史表；所有列 SQL CAST 为原始存储文本、PK 排序、UTF8 byte 比较，含 Grant/principal/instance/release/data/resource/Run/operation/checkpoint/event；不是只数行或比 hash，也不是物理数据库页字节。比较基线在合成 fixture 初始化后冻结，测试动作期间无授权增加/扩大。

13 项覆盖成功新连接读回、两次真实 SQL 写后失败整体回滚、同键可重试/缓存重试/并发只一效果、异指纹冲突；namespace/instance/release/owner/project/app/fingerprint 七负例；FAILED production preview 无注入写；非 test_only/错误隔离位置在 DDL/listener 前拒绝；finally listener 移除后普通 preview 不再写。故障回滚无已提交 FAILED preview 行，是事务注入拒绝，不伪造已持久失败历史。

独立审查指出初版故障发生在 receipt INSERT 前，receipt 为空不足证明它回滚。已把故障移到 record 和 receipt 两者实际 INSERT/SELECT 后，记录 Observation 并负例验证。初版 SQLite13PASS，不称发现产品事故；最终专项/聚合/精确 ServerCI 以本目录最终结果为准。0LIVE、没有生产数据/外发、没有导出包、没有安全策略调整；原 V5/历史 AT02/原 AT05 保留。
