# 受限接线：已审查源码的dev整合验证

独立分支 `dev/wiring-integration-20261008`，基于已验证DAG dev **da988723cba8295c492536f094162072b67e59d3**，普通merge接线候选966a25d。执行源码及测试冻结 SHA **`645d353142f6b443d0efe626170abd139445d181`**；产品src逐字等于独审源码645e494/候选966a25d。合并唯一冲突在回执构造，保留input_sources并保留严格fingerprint校验；没有实质产品行为变化、DDL、迁移、凭据或授权变化。相对新dev仅csv_dag.py、csv-dag.js、index.html三产品文件变化。

父线程报告同一第二reviewer限定通过645e494：SQLite/PG各32病例全通过，含真实HTTP、产品JS/DOM17项断言、语义拒绝、精确确认、撤权、两P2和并发冷恢复；未覆盖八组合、全量、原生Windows/Edge或通用P-B。原独审文件本环境不持有。本整合只增加测试/说明并核全部八组合，不把作者结果冒认为独立人工签收。

| 同源12文件、279唯一病例 | PASS | SKIP | FAIL / ERROR | 时间 |
| --- | ---: | ---: | ---: | ---: |
| SQLite | 276 | 3：PG应用角色子进程专用 | 0 / 0 | 272.354秒 |
| 自有PG17.9 | 278 | 1：SQLite历史NUL专用 | 0 / 0 | 476.814秒 |

collection、summary、JUnit、双后端provenance保存真实范围、nodeids、冻结SHA、全部src/tests前后hash，source_unchanged=true、returncode=0。此前DAG共享基础模块已在1b65整合20文件424病例通过；本次只重跑接线影响范围，不机械重复未变共享模块或旧全量。

每端八种端口选择分别从实际页面读取允许列表，选择来源，保存新计划，明确确认，调用自有测试Worker钩子，读回实际三个Operation回执。每组合10项页面断言，核quantity=15/两行/固定文本、preview屏障、report一或两个实际前驱指纹、全部input_sources、UNKNOWN/PENDING/发布关闭。Node只发自有loopbackHTTP，所有加载产品源码SHA256吻合。原DAG35、列补丁20、CSV29、Report29项原样通过，既有八组合API/Worker、46接线、24P2及严格类型、语义拒绝、撤权、UNKNOWN、冷恢复原断言继续通过。

真实升级各两种已执行旧源码：5a原DAG和1b65已整合DAG核心。全部旧src逐文件等于对应git blob，子进程实际导入旧模块生成无wiring_patch默认计划、完成结果、已检查列补丁和其他图。当前接线源码读取旧证明409/NOT_VALIDATED，拒绝不写；原存储JSON表示与历史行保持；新锚、新键、新精确确认的默认接线成功quantity=15。结构兼容不能作为旧证明跨源码升级兼容，新默认运行与所有允许端口选择继续支持。见两后端5a/1b升级proof与[升级行为](../csv-dag-integration-20261008/upgrade-behavior.md)。

源代码升级可能使同一完整依赖集合的其他CSV/Report/agent图锚失效，不缩小原依赖集合或改签旧证明掩盖409；旧数据不删除。跨版本混合Worker、热部署、不中断升级未验证。

Ruff全src/scripts/tests、mypy50源码文件PASS；仅既有Starlette TestClient弃用警告。原测试/候选断言和依赖锁、scripts/workflow保持，Windows900/Edge240/Node150不改。新增10项SQLite阶段PASS，最终两端覆盖全部新增病例。原始阶段/最终log/JUnit无损gzip保存，原字节hash与大小见raw-log-preservation。

两整合阶段所有自有资源最终清理：PG test schema/role均0，network=none/无端口，正常停止自有--rm容器，核匿名卷消失，正常移除自有镜像；本阶段10个临时路径含复用Node/PGsocket/旧源码归档已删除，前阶段6个fixture目录已删除，仅保留开发.venv，见cleanup与pg-cleanup-before。

## 复现

[页面指南](../../F2/CsvWiringPatchQuickstart.md)在原CSV应用/DAG区域给出三个端口来源和确认步骤。用锁定开发依赖、自己的jsdom30.1.2目录及隔离库，可只运行新增实际八组合：

```bash
NODE_PATH='/your-owned-jsdom/node_modules' LIVE=0 SIM2ACT_MODEL_MODE=mock SIM2ACT_LIVE_ENABLED=false .venv/bin/python -m pytest -q tests/test_csv_wiring_ui.py --basetemp=/tmp/your-owned-eight-wires
```

升级测试另准备自有git archive 5a完整src/tests/schema，以及1b65完整src/tests/schema，分别设置SIM2ACT_UPGRADE_OLD_ARCHIVE、SIM2ACT_UPGRADE_CORE_ARCHIVE，运行tests/test_csv_dag_upgrade.py。两个归档缺失时该专用病例明确SKIP，本轮已显式提供且每端两项PASS。PG只显式给自己的SIM2ACT_TEST_DATABASE_URL，socket目录与pytest basetemp分开，不使用用户/生产数据库。完整12文件范围见runner/collection，复制调整作者路径和输出，不覆盖冻结证据。

原审查候选966a25d与3b3534ca均保持冻结。semantic UNKNOWN、owner PENDING、publishable=false、LIVE=0；真实gold、完整P-B、人工签收、原生Windows/Edge及正式发布未完成；不改main、不强推、不部署、不改权限，不调用真实模型，无新CI。
