# E15 PostgreSQL来源退休与消费者串行

2026-10-06，恢复保存环境ready，/workspace/Sim2Act-pb/dev/f1-foundation 54ac055，正常origin fetch同HEAD。初始/work树未改。事前范围63f87bf；无新表/权限/CSV能力/模型/发布。

[基线结果](baseline.json)：真实PG17.11 READ COMMITTED barrier观察退休先行200/direct创建400，消费者先行201/退休409。**未复现成功插入失效app**；现有grant FOR UPDATE已串行这两种direct交错。静态怀疑不写成已发生故障。新共享project锁断言基线1FAIL/1PASS，确实缺project消费锁。初始测试harness误用FastAPI派发线程名及未传必填Limits导致timeout，已改为同一真实生产service/授权、两独立PG事务和真实blocking_pids观察；不伪造授权或SQLite锁。

实现统一Store.lock_project；所有消费者先project后card/app/grant：direct、目标卡创建/修订、MOCK目标候选、PREVIEW提取、新完成任务提取/退休、F1提交；共同候选持久化入口重验当前CSV实际hash/退休状态再写principal/app/grant。F1新提交显式拒绝退休输入；既有Run历史不改。无锁顺序倒置。E14现退休扫描/内容清空/当前来源授权保持。

新增9真PG检查：direct/目标卡创建/修订/F1提交双顺序8项，PG backend/blocking_pids证明等待；退休先行创建拒绝且无新增principal/app/grant，消费先行退休409且内容/既有消费者可读。第9项完成合成任务→提取→退休→fresh Store新40/坏列FAILED及历史，映射[冻结AT10子项](../../F2/AT10Subitems.md)。PG专项9PASS/1旧警告3.26秒，[JUnit](pg-barrier.xml)。主开发实跑，不是独立复验。

精确源码[53dc124](https://github.com/T1doo/Sim2Act/commit/53dc124ea8aeb554939ad79bbbb7d9526a66578f)已普通push，[ServerCI37411714116](https://github.com/T1doo/Sim2Act/actions/runs/37411714116)SUCCESS/job112101374653/2m51s，PG269PASS/0FAIL/0SKIP/1旧警告88.51秒。9新PG专项及既有最小应用角色CRUD/原生smoke/静态/Report/Cleanup成功、server stopped。实际平台/计数[results](windows-results.json)、完整步骤[run](windows-run.json)、[93源码指纹](source-hashes.json)归档；本地自建PG容器已停止并删除，未导出额外文件。真实浏览器/视觉0/BLOCKED，E14 DOM为历史旁证，本轮未新增浏览器/手机签收。只合成固定任务/退休旧内容子项，不提升完整P-B/AT10/Win11/F1/Release。0LIVE，无导出/额外恢复包或安全策略绕过。

本地完整聚合：[LinuxPG JUnit](linux-pg.xml)268PASS/1Windows平台SKIP/2警告82.16秒；[SQLite JUnit](sqlite.xml)254PASS/15平台/PGSKIP/2警告33.30秒。ruff/mypy18模块/JS syntax/diff通过。现警告为Starlette及并发FastAPI构造Pydantic alias警告，保留。不将SQLite15SKIP顶替真实PG专项。PG运行在测试专用loopback Docker postgres:17，实际17.11，镜像digest sha256:d74eeac9a635390a49bc21bd49fccd973de707e2a53a76ac49b552b8712ec46f；只合成账户，既有真实账户/环境安全策略未改。
