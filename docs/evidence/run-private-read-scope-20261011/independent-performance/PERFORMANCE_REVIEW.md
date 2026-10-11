补充性能只读审查：在实际 cold material/report SUCCEEDED 路径中，新 namespace SQL builder **没有执行**，不能把该处 DOM 超时归因为它的 SQL 性能回归。已定位到既有嵌套来源/权限/回执验证放大，但没有证明原 UI 超时的完整因果。原59检查报告/归档字节未改，不累计此性能采样为新的产品验收病例。

证据来自原 current-isolated post-True 失败的 SQLite fixture，以 SQLite 只读连接备份到本独立 /tmp fixture。它保留已实际成功的 units Run 和同一身份、版本、来源、实例；原 fixture 没有被打开为写连接。测试使用当前 frozen source 的真实 TestClient，依次 GET instance、source Run、material plan、source Run、material plan、instance plan，全为200，并核每个响应完整 fingerprint。

| 采样 | 六次 GET 总秒 | instance GET 秒 | namespace 调用 | SQL |
|---|---:|---:|---:|---:|
| current-A1 | 10.721 | 9.595 | 0 | 26995 |
| 2b-B | 10.002 | 8.660 | 0 | 26995 |
| current-A2 | 9.472 | 8.360 | 0 | 26995 |
| current-profile | 21.017 | 18.045 | 0 | 26995 |

A/B/A 只在独立进程内替换 protocol_run_ids 为从精确2b源 AST取出的原函数，再恢复；没有写源码，没有在 Worker 或 mutation 下启用旧oracle，而且禁止 baseline unscoped 调用。四组实际 oracle 调用数均为0，所以切换未影响任何权限判定。它不是完整旧源码UI性能对照；仅直接排除这里的新namespace函数调用。SQL中 namespace谓词0，每组26987 SELECT和8 BEGIN，所有回复 fingerprint完全一致。24 GET检查完成无报错，旧业务/历史表全部原串值保持、原fixture数据库 SHA保持、401冻结src/tests/scripts字节保持。

正常三组进程CPU与wall接近：CPU9.47–10.71s，而SQLite execute总wall仅0.38–0.43s。cProfile独立第四组有测量开销，21.017s不得对比10s DOM预算。实际热点链为 internal_api.inspect→lifecycle.inspect_instance/check_instance_records→csv_dag_instances.inspect_job/validate_binding→lifecycle.read_release/source_snapshot→csv_dag.load_plan/build→csv_material_reuse.plan_origin/recipe→delivery_graph_apps.current/load_family。profile六GET组合发生read_release46次、source_snapshot46次、load_plan100次、validate_binding148次、graph.current132次、authorize4224次。四个修改范围的 claim/protocol_jobs/protocol_recovery/protocol_pool 函数均未出现在完整route profile。热点模块lifecycle、csv_dag_instances、csv_dag、csv_material_reuse、delivery_graph_apps、apps以及csv-dag.js和原csv_material_reuse.cjs与2b逐文件hash完全相同，见unchanged-hotspot-source.json。

实例GET本身8.36–9.59s，随后还有两次source Run/plan验证和instance plan、JS seals/真实HTTP；这说明原10s DOM窗口余量很小，正常浮动即可越界，但本探针没有运行原JSDOM/socket驱动，不能据此将历史UI FAIL变成PASS或确定这就是唯一原因。root提出的page全局计数器旧窗口跨代污染理论也仍未实证：driver的w.fetch finally及event-action then访问全局page，新boot替换page；若有未跟踪的旧窗口async返回，会改动新计数。核过showApp调用的openDeliveryGraph和其openColumnPatches/openCsvDag目前是同步初始化，不能据此证明存在跨窗口残余async；showApp结尾await openInternal。原失败文件不保存page.requests/actions和每请求耗时，因而不足以判断是否实际发生。应以原预算串行UI最终结果和准确请求/计数状态判断，不能自动归为缺editable。

建议的后续定位方向是同一读事务内重复来源/权限/回执验证的调用树；任何复用必须保留当前身份/授权、来源graph与完整Run/receipt seals，不能删除检查、使用跨请求缓存或扩大预算来取得通过。此次没有修改产品或测试、没有提出先执行优化。

完整证据：first.log、result.json、summary.json、sql-trace.json、六个原生cProfile pstats、profile-source-functions.json、instance-only-profile-functions.json、unchanged-hotspot-source.json、frozen-before.json。profile文件可用pstats工具继续核caller。原probe.py可复现但需新的目标目录/SQLite copy，避免覆盖已有证据。

NOT RUN：原JSDOM/socket UI整例和超时完整因果、PG、Windows/native/browser、真实模型、旧源码升级、完整回归。使用进程内HTTP，没有调用浏览器或重试已拒路径、网络权限升级、模型、部署或推送。
