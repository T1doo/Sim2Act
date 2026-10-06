# E16 内部合成生命周期证据

范围与服务：[InternalLifecycle.md](../../F2/InternalLifecycle.md)。事前范围 eaeb731、源基线 764a20f，内部合成 service，未连接正式发布/部署。精确源码与完整本地/Server聚合终态已核实，见下文。

同工作区独立只读 reviewer 实际复现两个 schema 校验缺口，并发现新测试文件与原 AT05 进程测试重名；已纠正，新增用例移至 test_internal_lifecycle.py，原文件逐字保留。修复后独立复验报告与源码 hash 已记录。审查未替代真实 PG/Windows 及视觉验收。

保留：类型化结果账本不是通用业务数据写入；无新增/恢复 Grant、不复制 preview 作运行；失败保留 FAILED，无结果版本。正式发布/实际部署/完整 P-B及AT10/F1/Win11/protected browser 未签收。真实模型0、无额外导出/上传。

修复后同工作区[独立复验](independent-review.md)32PASS/1PGSKIP/1警告5.41秒；两schema缺口关闭、原AT05逐字恢复，另独立双实例/失败/撤权/跨owner smoke PASS。覆盖文件hash与最终源码一致后另记录。

主开发SQLite完整[JUnit](sqlite.xml)：286PASS/16PG或平台SKIP/1旧Starlette warning42.21秒；新内部路径32PASS/1PG角色SKIP，原AT05在Linux按原平台规则SKIP，不丢测试。ruff/mypy19源模块/JS syntax/diff通过。LinuxPG及精确ServerCI终态见下文。

主开发真实LinuxPG完整[JUnit](linux-pg.xml)：301PASS/1Windows平台SKIP/2警告111.58秒。包含33新内部检查（含PG业务CRUD最小角色）与原工程完整覆盖；真实loopback PG17.11，测试隔离schema，临时应用角色仅业务CRUD且无DDL。现有Starlette/Pydantic并发构造警告保留。

源码[e029922](https://github.com/T1doo/Sim2Act/commit/e029922794c9f9829ddb41bca0010aebc277e761)已普通push，精确[ServerCI37413258268](https://github.com/T1doo/Sim2Act/actions/runs/37413258268)/job112106185925completed/success；[95源码/测试/配置指纹](source-hashes.json)与独立复验三个源码hash一致。初始work树HEAD6f688e4不改，专用本地PG sim2act-e16-pg已stop/remove。收到断开通知后实际pwd/git/gh再次成功，环境当时仍可达，未声称平台恢复完成。

精确ServerCI终态 SUCCESS，job112106185925历时3m26s；PG302PASS/0FAIL/0SKIP/1旧Starlette warning118.16秒，33新内部项及原AT05进程用例全部纳入。Setup/五表显式迁移、最小应用角色CRUD、原生API-worker smoke、ruff/mypy19模块、Report/Cleanup全成功，server stopped。[实际计数/平台](windows-results.json)、[完整步骤](windows-run.json)与95源码指纹归档。Server2025Datacenter/build26100/镜像20260925.250.1/PS7.6.6/Python3.12.10/原生PG17.11/admin=true/EnableLUA1；现Node20动作被GitHub强制Node24注释保留。不是Win11或视觉验收。文档收尾只变docs，源码/test/config保持CI精确版本，不再次触发CI。
