# 受控条件分支候选日志 — 2026-10-08

父线程授权 V5 F2-T04 /产品§5.3，独立 dev/controlled-branches-20261008，基线5bbc462。语义、缺失/严格类型、跳过与下游/环规则先记录ControlledBranchesPlan；实现并在冻结前将未产出报告收紧为PARTIAL，原失败和混源阶段保留。执行源码/标准测试041cf8ec5fbfeffde6ee3103bba8a4188eb08861。

冻结29文件756唯一：SQLite741P15S、PG17.9 755P1S，0FAIL/ERROR；source前后不变。新59例含6实际页面/9Run/99DOM断言每端、授权/篡改/并发/预算/租约、最低CRUD角色；原接口和断言保持。另真实Python子进程失联重领每端1P：旧fence1→新3，跳过前缀保持、无重复、旧worker拒绝；该独立审计不是重复全套。总757唯一每端，SQLite742P15S、PG756P1S。Ruff/mypy50/Node/diff通过。

候选语义：when仅eq/in/exists、schema输入或已核直接前驱；条件假SKIPPED，前驱跳过则下游SKIPPED，不执行/伪造输出；必需报告缺失PARTIAL而非验收成功。同一已确认计划允许新的显式boolean输入，新Run/旧Run分别冻结。复用原Run/Worker/Operation/事件/API/UI，无表/DDL/Grant/身份/业务写/模型/发布。Agent旧消费者拒绝条件，读计划先检查项目所有权。人工锁公开入口不做。

证据含真实collection/JUnit/raw/source/proofs和失败过程，见[归档](../evidence/controlled-branches-20261008/README.md)，用户见[指南](ControlledBranchesQuickstart.md)。临时资源仅自有隔离，全部清理单独记录。普通push候选供父线程独审，不合已验dev/main；作者自查不冒认独立审查。LIVE0、原Windows900/Edge240/Node150/依赖/旧断言不改，无新CI。Win11/Edge原生、通用运行器、真实语义/gold/P-A/P-B/人工签收/正式发布仍未完成。
