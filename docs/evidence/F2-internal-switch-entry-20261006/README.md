# E22：内部兼容版本切换入口（进行中）

原V5 F2-T08/AT16/产品§10.1最小工程切片。既有认证owner/project/app/runtime/instance，手动目标Release→准备→精确批准回读→未默认勾选确认→一次性事务切换。正式发布false/0LIVE，不新增Grant/身份/表/生产DDL/CSV能力。回退仅指针切换，不能删除结果/Run历史或撤销外部动作；已有Worker版本改变时保守拒绝旧接受任务策略不变。

prepare/GET/commit共用目标范围、兼容schema转移、保留数据验证；目标fingerprint/revision/data/hash/grant/expiry全部绑定。API实例URL与批准必须一致；服务commit在锁实例前核项目。损坏字段/类型及一致重hash跨app/project拒绝，批准不消费。重复提交一次成功其余409，无重放机制。UI代际保护迟到回执，取消/返回不撤销已接受切换，未知确认结果只提示读回历史，不自动重发。

[独立报告](independent-review.md)：11 SQLite PASS 6.36s、实际损坏批准及合成NodeVM双击/取消迟到复验；独立未跑PG/Windows/真实浏览器。独立首次复现旧服务跨项目损坏批准直接commit被接受（HTTP本已拒绝），当前修复后直接commit DomainError闭合。初开发helper变量错误6FAIL/44PASS/2SKIP保留[记录](implementation-first-failure.json)，修复后focused58PASS/2SKIP，后续新增类型与项目负例11PASS；不删失败。初SQLite360PASS22SKIP102.97s对应中间源码/10新测试；最终aggregate另存。

现WindowsBrowserCI仍同windows-2025既有job15min、browser step4min，官方固定SDK/签名预装Edge、chromiumSandbox:true、实际renderer只读token检查、CSP不改/bypassCSP:false。新增真实继续命令、兼容升级/回退/结果Run lineage、手动确认、重复点击、取消/返回迟到、过期及不兼容拒绝。仅owned test_only fixture调用已有service生成incompatible target；一次合成switch批准在首次回执前把TTL收紧3秒并重算精确fp，等待实际到期后UI禁用/实际API409，不改生产300秒期限或系统时钟。该短TTL不冒称生产五分钟计时验收。截图/JSON经既有job日志白名单回读/块序长度SHA核验，仅repo证据。

源码commit/真实CI/browser终态/PNG核验待补。Win11普通用户、物理手机、其他浏览器、完整焦点/无障碍/复杂业务schema迁移、完整AT02/F1/F2/P-A/P-B/正式发布均未签收；E20最初AT05根因UNKNOWN继续保留，Linux SUID保护路径阻塞未改。

本地最终产品源码：SQLite361PASS22PG/platformSKIP118.65s；LinuxPG382PASS1WindowsSKIP300.43s；最后HTTP focused29PASS1PGSKIP14.14s，实际CRUD-only角色switch额外1PASS3.28s。PG collection之后在原role测试追加switch断言，已单独实际通过，最终精确ServerCI完整重验待；没有把此前aggregate当作新增断言已收集。ruff/mypy21/3JS syntax通过，[source hashes](source-hashes.json)；生产/API/UI与独立接受hash相同。最终follow-up只静态核新增worker-v2浏览器/role断言。
