# 通用目标卡与版本化验收草案工程证据

2026-10-05；原F2-T01共同前置切片，实施前选择与风险见F2/Plan。不局限CSV：项目内一般目标可分开记录已知/假设/未决项/硬条件/验收检查，绑定同项目授权TXT/MD/CSV/JSON。人工草案始终DRAFT/不可执行/不可发布，无模型规划或P-A/P-B生成验收。

每次保存追加goal_card_versions不可变快照及指纹，goal_cards只更新当前指针；旧窗口expected_version拒绝409，PG行锁/条件更新及SQLiteBEGIN IMMEDIATE保护并发，旧条件/检查保留，不自动降低要求。每次详情/修订复核项目所有权、近50个历史指纹以及相关材料user/runtime授权与实际hash；已撤回材料的历史保守拒绝，不恢复Grant。当前接口回读最近50版，旧数据库版本保留；列表只返回本人项目的手工名称/版本元信息，不能当作材料或执行授权。

新增两表仅既有显式migrate创建；现有运行角色需业务CRUD授权，不赋DDL，API不自动建表。F1GoalSpec/冻结Run、七Schema及V5/AT原文不修改。零新依赖/模型请求/Run/Operation/preview/Grant、任意代码或外部发布；只新增用户明确保存的草案数据。

14项工程检查覆盖一般目标/字段分离/材料hash/历史与冷API回读、空引用草案、跨主体/同用户跨项目、两种撤权、材料/历史篡改、闭合输入长度/重复引用拒绝、两个并发旧版本仅一成功。完整SQLite147PASS/3平台专项SKIP/1旧Starlette警告9.27秒，ruff/mypy15模块/JS语法/diff通过，sqlite.xml保留。首轮新测试误写既有DomainError400为422已修正精确契约；测试双客户端改用同一app避免无关并发建Schema warning，未更改产品错误码。

真实LinuxChromium/agent-browser、临时SQLite/合成身份7检查点PASS：通用文本目标分项创建、明确修订并绑定材料、旧硬条件回看、第二本地客户端新版本、旧浏览器窗口409且未保存文字保留、最新版本重新打开、页面重载后持久版本与人类可读历史。两客户端之一由固定合成认证的正常HTTP请求模拟，非模型/假响应。最初CLI参数/表达式错误纠正后完整断言通过，无产品绕过；browser-results.json及人工查看截图保留。浏览器与本任务localhost fixture已停止；非Win11/其他引擎通过证明。

正常开发分支push已成功，精确源码6bf5e0558e8436eb9a12adbc9d188d4b84878abb的[WindowsServerCI37322479923](https://github.com/T1doo/Sim2Act/actions/runs/37322479923)/job111804777471 completed/success（1m39s）。PG150PASS/0FAIL/0SKIP/1旧警告33.71秒，首次Setup/显式迁移/完整锁/pip check、现有F1应用角色API-worker原生smoke、ruff/mypy15模块、Report/Cleanup全通过，PG server stopped。14个目标卡工程API/事务检查使用隔离test-owner schema（含两writer）；不冒充Win11 UI或独立应用角色目标卡原生实测。windows-run.json/windows-results.json由开发方现有身份实际读取run/job/log，非独立复跑；文档追记不重复CI。真实模型预算0；AT02核心LIVE证据有效，历史脚本仅一owner/一项目，完整初态不能补证，额外预算尚未批，不调用。F1未签收/F2正式准入不变。
