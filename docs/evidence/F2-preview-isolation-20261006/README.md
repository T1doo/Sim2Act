# E18 合成预览写隔离证据

事前范围 4c545ef24de3c63cf733c2d81ec6301e15fc10cf，基线 727d023。原 V5 AT17：预览中执行写入，只有预览 namespace 变化，真实实例业务数据和权限不污染。本轮只关闭 **AT17_SYNTHETIC_FIXTURE**；[阶段门审查](../../F2/StageGateReview.md)保留原正式 AT17/F2/P-A/P-B/AT10/AT20/F1/Win11/protected-browser 未完成项。

`tests/preview_write_fixture.py` 是 **FAULT_INJECTION**：只允许显式 test_only Store + tmp SQLite 文件或 test_[32hex] PG schema；独立测试 MetaData 两表由 fixture Setup 建立，不进入生产 meta/CLI 迁移，不由 API/worker 初始化建表，不注册工具、不新增生产 Grant 或业务写入口。唯一生产变更是保存已有显式 test_only 标志，默认 False。

监听真实 `apps.preview` 持久事务的精确 app_previews INSERT，只在 SUCCEEDED 时同 Connection 执行固定 note 记录和 receipt INSERT，均实际同事务 SELECT 读回，再可注入提交前故障。新 engine/连接独立读回，note 不是 CSV 求和/原答案或 cache。fixture guard 验 namespace/owner/project/app/candidate fingerprint、禁止 instance/release target；它验证测试 adapter 的边界，**不证明尚不存在的生产 writer gateway**。production response business_writes=0 仍指生产工具链，不把注入写算成正式能力。

种子创建真实内部 Release 和两个有类型化 result 数据的 instance。前后查询全部生产 meta 表，仅排除合法 preview 历史表；所有列 SQL CAST 为原始存储文本、PK 排序、UTF8 byte 比较，含 Grant/principal/instance/release/data/resource/Run/operation/checkpoint/event；不是只数行或比 hash，也不是物理数据库页字节。比较基线在合成 fixture 初始化后冻结，测试动作期间无授权增加/扩大。

13 项覆盖成功新连接读回、两次真实 SQL 写后失败整体回滚、同键可重试/缓存重试/并发只一效果、异指纹冲突；namespace/instance/release/owner/project/app/fingerprint 七负例；FAILED production preview 无注入写；非 test_only/错误隔离位置在 DDL/listener 前拒绝；finally listener 移除后普通 preview 不再写。故障回滚无已提交 FAILED preview 行，是事务注入拒绝，不伪造已持久失败历史。

独立审查指出初版故障发生在 receipt INSERT 前，receipt 为空不足证明它回滚。已把故障移到 record 和 receipt 两者实际 INSERT/SELECT 后，记录 Observation 并负例验证。初版 SQLite13PASS，不称发现产品事故；最终专项/聚合/精确 ServerCI 以本目录最终结果为准。0LIVE、没有生产数据/外发、没有导出包、没有安全策略调整；原 V5/历史 AT02/原 AT05 保留。

最终本地聚合：[SQLite](sqlite.xml)332PASS/21PG或平台SKIP/1旧Starlette warning55.92秒；[真实LinuxPG](linux-pg.xml)352PASS/1WindowsSKIP/3旧Starlette/Pydantic warnings155.54秒；[真PG专项](target-pg.xml)13PASS/1warning13.01秒。独立最终13PASS/1warning4.57秒，未独立PG/aggregate/CI。[独立报告](independent-review.md)关闭receipt回滚证据缺口并收窄F2-T07未验收措辞。ruff/mypy20/JS syntax/diff通过；原AT05/V5/历史AT02差异为空。

源码925e560dc1a196c6c4747cb349d558156a721c0f普通push，ServerCI37416936441/job112117505998仍运行，最终状态另记。[100源码/test/config hash](source-hashes.json)固定，继承E17文件仅db.py增加test_only标志，另两tests；无生产工具/表/权限变化。

## E18 精确终态

源码[925e560dc1a196c6c4747cb349d558156a721c0f](https://github.com/T1doo/Sim2Act/commit/925e560dc1a196c6c4747cb349d558156a721c0f)已普通push；[ServerCI37416936441](https://github.com/T1doo/Sim2Act/actions/runs/37416936441)/job112117505998 completed/success（2m47s），PG353PASS/0FAIL/0SKIP/1旧Starlette warning105.29秒。13新合成写隔离项和原回归全过，Setup/原生应用角色API-worker smoke/ruff/mypy20/Report/Cleanup全成功，server stopped。[实际结果与边界](windows-results.json)、[步骤](windows-run.json)、[100文件hash](source-hashes.json)归档。Server2025/build26100/PS7.6.6/Python3.12.10/原生PG17.11，admin=true/EnableLUA1；Node20动作被强制Node24注释保留，不改系统策略、不冒充Win11。

主开发LinuxPG352PASS/1WindowsSKIP/3旧警告155.54秒；SQLite332PASS/21PG平台SKIP/1旧警告55.92秒；独立13PASS/1warning4.57秒且三文件hash一致，未独立PG/aggregate/CI/browser。原work树6f688e4保持clean，原V5/历史AT02/AT05差异为空，专用本地合成PG已stop/remove。源码/test/config与精确CI一致，文档收尾普通push不重复CI。仅AT17_SYNTHETIC_FIXTURE PASS；原正式AT17/发布/F1/F2/完整P-A/P-B/AT10/AT20/Win11/protected-browser门不提升，0LIVE/无导出/无安全绕过。本轮至此结束；下一真实决定/接入见StageGateReview，不继续邻接便利功能。
