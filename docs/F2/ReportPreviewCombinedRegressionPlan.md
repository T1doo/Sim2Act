# Report PREVIEW combined full regression — implementation before tests

2026-10-07，父授权产品/预算并行后的后续精确整树验证。准备基线`e828c066ec63689fe5de5d66f650eda33c0086e8`，新专属`/workspace/Sim2Act-report-preview-combined-regression` / `dev/report-preview-combined-regression-local`。父将合入三testfiles不可变fixture复用ff58011与canonical ReportManifest PREVIEW桥接（contracts/preflight/apps/api/UI）；当前基线不是最终候选。父明确freeze/GO之前不跑collection/full/长测试、不初始化任何产品fixture/权限/模型，不能把e6或其他线旧结果作新源证明。

依赖与来源：三个新的隔离venv（controller、SQLite、PG）各仅localpth本树src优先、共享现有site-packages路径次序；不处理共享editable pth/finder、不安装修改包或sharedvenv。Node/jsdom从既有只读NODE_PATH=/workspace/browser-tools/node_modules:/opt/codex/runtimes/cua/lib/node_modules。准备阶段只读模块origin probe，不调用script main/testfixture/模型/Store.initialize。最终freeze时全tracked src/tests/scripts/.github hashes与精确Git相等，controller和clean-env child sys.executable/prefix/关键模块均当前src，完整collection保存一次；预算优化改变tests执行复用，不能隐藏失败或缩小全集。准备源与最终源分别记录。

专属PG17仅cached image/local随机端口，container`sim2act-report-preview-combined-regression-20261007`、label`sim2act.report-preview-combined-regression=20261007`；URL/password仅mode0600私有state、只经本PGcontroller env传。准备只建空测试database，schema/role/publictable0，不提前Store.initialize/seedpool/Grant。最终各fixture独立UUID schema/runtime业务CRUD角色与显式owner测试setup，完整PG锁/进程用实际PG、不拿SQLite分支冒充。其他owner运行中的CPU服务/DB/schema/role/容器不能被停止或清理；只清本标记明确归属资源。

父freeze/GO后唯一正常串行完整验证：整树`python -m pytest -q -ra --durations=30 --junitxml=<owned> --basetemp=<unique>`，先SQLite自然终态，exit0才启动PG，不并发两个fullcontroller、不自动循环或改timeout/guard/覆盖。记录精确source SHA/full argv/开始结束时间/全集collection/原-ra所有fail&skip/durations30/JUnit/exitcode，源码与import provenance绑定。失败立即报父并保留原日志；未决功能缺陷必须先停止仅owned当前controllers、审计清理再由owner修源/新freeze，不边跑边改或旧结果重标。最终新源结果不能相加任何旧分线成绩。

结束后只owned schema/role/publictable/controller/children0→检查精确label删除ownedcontainer→remaining label0，移除本私有URL/rawPG日志/XML及明确fixturetemp，公开sanitized日志和证据先检查实际秘密0。Plan/Log/manifest/commands/summary/cleanup仅本地docs提交；无push/CI/LIVE/真实身份/Grant/激活准备器/系统安全改动。完整工程PASS不等于整体P-B、语义/owner签收、正式App发布或未跑原生像素。

当前状态：PREPARING，FINAL_SOURCE_UNFROZEN，collection/full NOT_RUN。等待父精确SHA和明确GO。
