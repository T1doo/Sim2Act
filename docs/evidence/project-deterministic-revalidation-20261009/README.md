# PROJECT 确定性检查：最终限定验证记录

开发集成基线 `5fedb359eff076798782b99a5fd5748d76da5148`；隔离候选
`dev/project-deterministic-revalidation-20261009`。最终源码/测试冻结
`429a62a418748822d51d9e930ec05f8b560c5ef2`，348文件。作者及独审矩阵已实际结束，独审LIMITED_PASS仅适用下述范围；
普通推送与远端验证随后记录。不能当完整验收。

对应原F2-T07/V5§9.3(7)，实际执行既有CSV注册工具和canonical Report有限规则，
按原PROJECT精确计划、全部当前成员、逐应用输入/归档Run/version/fence/result
及确认生成新的独立seal回执。CSV独立Fraction核对真实读算；有限精度超范围
记NOT_RUN；Report实际读取当前原材料并重算有限规则，explanation NOT_CHECKED。
每个CHECK绑定ID/revision/content/check ref，遗漏图声明也逐项NOT_RUN。
所有成员完整权限/来源硬门先于遗漏处理；不可信来源/撤权不能降级省略。

新结果只追加现有delivery_graph_requests两行（结果+独立seal）；原plan/jobs、
候选、材料、归档Run、presentation及其它业务表不改。检查PENDING任务不自动
转完成；有限执行PASS并不消除未知依赖完整性与原PROJECT阻塞。

最终必要作者范围44例/库：新功能27 API、3真实HTTP/JSDOM、1实际旧源码升级；
原DeliveryGraph计划3、Report实际回读1、CSV人工锁页面1、Report编辑锁页面3、
晚回执lost_response两phase2、旧Report升级1、旧CSV两代升级2。SQLite **43PASS/1SKIP/0FAIL（366.52秒）**，仅CRUD-only PostgreSQL角色
1例明确SKIP；PG **44PASS/0SKIP/0FAIL（604.92秒）**，该角色例实际通过。
每库9个真实HTTP/JSDOM页125项检查，4个实际旧源码升级全部通过，无环境性跳过。
348冻结文件前后完全匹配。新版导入/Ruff/mypy54/JS语法及31新用例收集通过。
Junit及本轮source-command/退出/时间已实际核验，旧eafea同名终态不作本轮结果。

独审另写 **35 SQLite/API PASS（160.43秒）**与 **2真实loopback HTTP/JSDOM
页PASS（47.21秒，30checks，每页13加载文件哈希匹配）**；68产品源文件
前后逐字节与Git blob一致。老5fed66文件匹配，三新路由实际404/0写，独立
负例1PASS；这不是旧数据库升级签收。作者用例不计独审，独审未运行PG/角色/
两连接竞争/旧库升级/原生或整体。见[独立限定复核](independent/FINAL_REVIEW.md)。eafea阻断与作者harness错误、
最终修复归属参见[FailureLedger](FailureLedger.md)，修前矩阵不能代最终验收。

长期状态：LIVE=0、semantic UNKNOWN、owner PENDING、overall NOT_ACCEPTED、
正式发布关闭；PROJECT PENDING/BLOCKED_PARTIAL，dependency_completeness
BLOCKED_UNKNOWN。PG resources-history超时OPEN、HTTP200损坏响应人类提示
限制保留、Windows900/Edge240/Node150未验收。Linux HTTP/jsdom不能代原生。

完整作者私有日志/SQLite/旧源归档在 `/tmp/sim2act-project-checks-20261009`；
独审在 `/tmp/sim2act-project-revalidation-independent-20261009`。已保存命令、Junit、退出、冻结字节、实际页面source hashes及四旧源升级证明。
owned PG `be85119016f205d4da1e766f730dd82c56d3a22f2f13931c8a43843168c4dd08`
前后schema/role/public为0/0/0，按精确CID/owner/network none/ports无发布
核验后normal stop、rm-v，CID及1匿名卷确证不存在。完整容器日志留私有根。
独审三个阻断均已修复，限定范围内无剩余review blocker。
普通推送远端验证尚待；开发5fed、Report锁候选26ff及main6f688保持。
