# E16 内部合成生命周期证据

范围与服务：[InternalLifecycle.md](../../F2/InternalLifecycle.md)。事前范围 eaeb731、源基线 764a20f，内部合成 service，未连接正式发布/部署。实际源码、聚合结果、精确 WindowsServerCI 终态将在执行完成后记录；不预写成功。

同工作区独立只读 reviewer 实际复现两个 schema 校验缺口，并发现新测试文件与原 AT05 进程测试重名；已纠正，新增用例移至 test_internal_lifecycle.py，原文件逐字保留。独立复验报告将在固定源码 hash 后记录。审查未替代真实 PG/Windows 及视觉验收。

保留：类型化结果账本不是通用业务数据写入；无新增/恢复 Grant、不复制 preview 作运行；失败保留 FAILED，无结果版本。正式发布/实际部署/完整 P-B及AT10/F1/Win11/protected browser 未签收。真实模型0、无额外导出/上传。

修复后同工作区[独立复验](independent-review.md)32PASS/1PGSKIP/1警告5.41秒；两schema缺口关闭、原AT05逐字恢复，另独立双实例/失败/撤权/跨owner smoke PASS。覆盖文件hash与最终源码一致后另记录。

主开发SQLite完整[JUnit](sqlite.xml)：286PASS/16PG或平台SKIP/1旧Starlette warning42.21秒；新内部路径32PASS/1PG角色SKIP，原AT05在Linux按原平台规则SKIP，不丢测试。ruff/mypy19源模块/JS syntax/diff通过。LinuxPG完整aggregate及精确ServerCI仍进行中。

主开发真实LinuxPG完整[JUnit](linux-pg.xml)：301PASS/1Windows平台SKIP/2警告111.58秒。包含33新内部检查（含PG业务CRUD最小角色）与原工程完整覆盖；真实loopback PG17.11，测试隔离schema，临时应用角色仅业务CRUD且无DDL。现有Starlette/Pydantic并发构造警告保留。
