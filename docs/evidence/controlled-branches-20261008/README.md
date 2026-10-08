# 受控条件分支候选：冻结工程证据

独立分支 **dev/controlled-branches-20261008**，基于已发布 dev **5bbc462b4ce0027fe9349e4b42064fe75f1470f5**。真实执行的源码和标准测试冻结 SHA **041cf8ec5fbfeffde6ee3103bba8a4188eb08861**。候选仅普通推送供独审，不合入已验 dev/main；独审 **PENDING**，作者自查不是第二 reviewer。

依据 V5 F2-T04、产品 §5.3，在原三节点 CSV 运行区增加可选 when；没有新任务家族、平行运行器、Grant/身份/表/DDL/业务写入/发布。共六产品文件与 AppManifest schema 修改；其余原接口和历史保留。preview 必经，aggregate/report 各可有一个 eq/in/exists，读取已声明输入或已验证直接前驱。比较无类型转换；缺失 exists=false，缺失 eq/in拒绝继续。条件为假持久 SKIPPED；前驱跳过传播 DEPENDENCY_SKIPPED，不创建 Operation 或假输出。未产出必需报告是 **PARTIAL / output=null / output_status=SKIPPED**，实际产出并核验才 SUCCEEDED。语义 UNKNOWN、owner PENDING、发布false始终保留。

| 同一冻结源码、29文件、756唯一用例 | PASS | SKIP | FAIL / ERROR | pytest时间 |
| --- | ---: | ---: | ---: | ---: |
| SQLite | 741 | 15：隔离PG角色/平台专用 | 0 / 0 | 519.82秒 |
| 自有PG17.9 | 755 | 1：SQLite历史NUL专用 | 0 / 0 | 925.46秒 |

另有 **1个独立子进程重领病例，每端1 PASS**（SQLite2.42秒、PG8.23秒）。两范围合计每端757个唯一病例：SQLite742PASS15SKIP；PG756PASS1SKIP。外加病例文件及SHA见 child-summary，位于证据目录，不重复执行已通过套件。

scope、collection、JUnit、原始日志、summary、provenance保存完整实际范围和src/tests/schema/scripts/workflow前后哈希，source_unchanged=true、returncode=0。29文件覆盖共享契约/预检、CSV/agent/Report、目标候选、内部实例和持久AppRun、交付图、局部修改、DAG/接线、原真实DOM及新分支。59新标准用例在范围内，另1真实进程边界专项；不使用旧全量或旧版本结果证明本候选。两端并行运行，Linux局部耗时不作为Windows900容量判断。

每端新实际页面6场景、9个真实Run、99项DOM断言：同一确认计划的true/false不同路径，aggregate跳过传播，exists缺失/显式false，前驱count的in与column的eq。每场景实际丢失一个已接受响应，冻结输入/键后同键恢复；重新打开应用核同一持久证明。原Node/HTTP驱动与断言全部保留通过。actual-page-matrix和两端原results包含请求、真实计划/结果、已加载产品文件SHA256；测试仅自己的loopback，没有真实模型或外部业务。Node/JSDOM不是原生Edge/视觉验收。

独立进程专项：正常API冻结include_report=false，可信preview真实Operation后aggregate持久跳过；只将自己Run的旧租约置过期。新Python子进程真实Store.claim/Worker.process、实际导入本树csv_dag，核原机制撤销+领取使fence1→3；旧前缀逐字指纹保持、仅1Operation和2跳过事件、PARTIAL无假报告。旧fence不能再写，其他表全部保持。两个实际结果/模块路径/模块SHA已保存；自有子进程配置用后删除。不是旧token的新Worker对象冒认重领。

负例覆盖：常量/输入严格JSON类型、null/额外字段/未知引用/未来和自身引用/环/表达式拒绝、确认错指纹与同键改输入、撤权与来源变化、协调改签接受输入、跳过/终态/类型篡改、冷恢复、fencing/租约/截止/有效预算、并发。新增两个PG最低CRUD角色用例真实创建计划、运行和冷读；无超级用户、DDL尝试拒绝、Grant/Principal/app/resources保持。Agent预览明确拒绝条件，避免新schema被旧消费者静默忽略。项目所有权检查前移到计划请求账本读取之前，跨主体403且零写。

## 原失败与阶段范围

所有阶段raw/XML保留，无损gzip和原字节SHA见 raw-preservation。first：39P/2测试辅助limits参数错误；second94P和third47P只是未冻结阶段，third的“跳过也SUCCEEDED”已被更严格PARTIAL语义替代。fourth：52P/1驱动新增断言期间的混源计数失败，不能作冻结结果。fifth53P/2PGSKIP也是阶段。pg-first53P/2辅助误用不存在response列，修正为从源计划取app；pg-second58P/1跨主体期望403但旧入口先查账本返回409，已前移所有权门；pg-ownership3P复验含双角色。真实子进程首次执行正确，audit误把fence增量写成1；读原Store.claim确认两次增量后改为精确+2，首轮原记录保存，随后双端1P。阶段失败均不删除或改写，不与最终756冻结结果混算。

Ruff src/scripts/tests、mypy50源文件、Node语法、git diff检查通过；原241个tests/scripts/workflows/锁文件逐字保持，provenance列明。保护和Windows900/Edge240/Node150不改，无新CI。自有PG network=none/无端口；schema/role/public表均0后正常停--rm容器，核匿名卷消失并正常移除自有镜像。自己的Node/npm、所有fixture/DB/socket/编辑脚本临时路径清理见cleanup；开发.venv保留。

## 复现与未完成

[页面和API指南](../../F2/ControlledBranchesQuickstart.md)。标准新专项为 tests/test_controlled_branches.py 和 tests/test_controlled_branches_ui.py；全实际范围见scope.json。run_frozen.py记录实际参数/集合/来源；重新运行请复制到自己同层级证据目录并调整自己的路径，不覆盖本冻结证据。PG仅自己的隔离测试数据库，socket和pytest basetemp分开。

独立进程专项可用同一锁定环境运行（PG时另设自己的SIM2ACT_TEST_DATABASE_URL）：

```bash
PYTHONPATH=tests LIVE=0 SIM2ACT_MODEL_MODE=mock SIM2ACT_LIVE_ENABLED=false .venv/bin/python -m pytest -q docs/evidence/controlled-branches-20261008/test_cold_reclaim.py --basetemp=/tmp/your-owned-cold-branch
```

这里只是既有可信三节点的受控分支，不是任意DAG/通用R0、逻辑组合/循环、模型规划或新的业务写能力。人工锁公开入口未做。源码升级仍可能使旧来源证明失效，须显式新派生/新键/重新确认；旧数据保留，不改签、不承诺跨源码热升级。独审、原生Win11/Edge、真实语义/gold、完整P-A/P-B/人工签收与发布均未完成。LIVE=0、无模型预算消耗、main/dev已验基线未改、无强推/部署/凭据或安全权限配置。
