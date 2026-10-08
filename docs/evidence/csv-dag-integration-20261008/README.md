# DAG核心＋P2：开发分支整合证据

原dev基线16041ec，独立整合分支 `dev/dag-integration-20261008`；普通merge候选3b3534ca，合并SHA `71080ea81c850ccf08f4260837505e2823c923e0`。执行源码及测试冻结SHA **`1b65e94ebd81c1e31091b3078b8223328b726294`**。产品src与3b候选逐字一致，只新增真实升级测试/驱动及说明；旧断言、依赖锁、scripts/.github保持。无DDL、数据迁移、授权或凭据变更，不含接线966a25d。

父线程报告原第二审查者已限定闭合两P2；每端26PASS3FAIL的三项是旧源码完整依赖hash升级后409，符合既有失效策略，不是无缝升级通过。独审文件本环境不持有，作者证据不冒认人工签收或全功能验收。

| 同源20文件、424唯一病例 | PASS | SKIP | FAIL/ERROR | 时间 |
| --- | ---: | ---: | ---: | ---: |
| SQLite | 414 | 10：PG专用 | 0/0 | 295.022秒 |
| 自有PG17.9 | 423 | 1：SQLite历史NUL专用 | 0/0 | 533.338秒 |

实际collection、范围、跳过原因、终态时间以collection/summary/JUnit为准。范围为DAG/P2、列补丁/键、实际UI、共享契约/预检/Store/Worker/runtime/普通CSV/Report及协议/条件运行回归，不重复旧720/1591全量。各后端实际产品HTTP/DOM：DAG24、列补丁20、CSV29、Report29、ReportManifest49项，加载源码哈希吻合。Ruff全src/scripts/tests及mypy50源码文件PASS；仅既有Starlette TestClient弃用警告。Windows900/Edge240/Node150不改，原生Windows/Edge NOT_RUN，LIVE=0、MOCK。

真实升级病例在旧5a归档完整src（逐文件等于git blob）子进程创建完成DAG、检查过的列补丁和第二应用图。新源码读取同一自有测试库：旧计划/结果/历史/另一应用图409；旧接受重放409且全表无写；状态只返回NOT_VALIDATED、result=null、steps=[]。重派生新锚后旧计划INVALIDATED；新键计划拒绝旧确认，精确新确认另存成功quantity=15。原amount=30预览、quantity旧结果、Run/Operation/intent/events/请求/锚/来源版本/应用/资源原行保持，数据库JSON原始存储字符串及主键哈希也保持。见两后端upgrade-proof/old-source-proof与[升级说明](upgrade-behavior.md)。

源码依赖集合覆盖全部服务端Python模块（config.py除外），升级可能影响其他CSV/Report/agent图锚；不得缩小依赖集合掩盖409。保留旧数据，重新派生/新键/精确确认；不保证旧运行续跑、热部署或混合版本worker。两个夹具初次失败（授权快照准备顺序、错误GET路由）原始日志保留，最终冻结病例通过，未修改产品或旧断言掩盖失败。

每后端provenance记录冻结SHA与全部src/tests前后哈希，source_unchanged=true/returncode=0。原始阶段/最终日志和JUnit无损gzip，解压原字节哈希见raw-log-preservation。6个阶段/最终fixture目录已删除，PG test schema/role均0；因父线程显式授权紧接着接线整合，自有network-none PG、Node和旧源码归档暂留复用，最终清理在下一阶段结束核对，见phase-cleanup。

复现先使用锁定开发依赖与自有隔离环境：

```bash
mkdir -p /tmp/your-owned-old-dag
git archive 5a5543c902fbb78dd91c28c98386af51fb24dd67 | tar -x -C /tmp/your-owned-old-dag
SIM2ACT_UPGRADE_OLD_ARCHIVE=/tmp/your-owned-old-dag LIVE=0 SIM2ACT_MODEL_MODE=mock SIM2ACT_LIVE_ENABLED=false .venv/bin/python -m pytest -q tests/test_csv_dag_upgrade.py --basetemp=/tmp/your-owned-upgrade-test
```

20文件范围读取runner/collection；UI设置NODE_PATH为自己的jsdom30.1.2目录。PG显式SIM2ACT_TEST_DATABASE_URL仅指自己的隔离库，socket与basetemp分开。不得覆盖冻结证据或用用户数据库运行夹具。页面行为见[上手指南](../../F2/FixedCsvDagQuickstart.md)。

semantic UNKNOWN、owner PENDING、publishable=false，正式发布关闭，真实gold、通用P-B、人工签收、原生Windows/Edge未完成；不改main、不强推、不部署、不运行真实模型，无新CI。
