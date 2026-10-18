# 旧P-A完整页面长测：独立只读根因分析

源码基线 `475777cf0c4c23f83a50d9e957adb6cf9d374ca0`。本人只读源码、原中断日志及原合成SQLite元数据，没有修改仓库/原DB、没有运行产品GET/Worker/模型或重跑长测。外部元数据读取为SQLite `mode=ro&immutable=1`，前后原DB SHA均 `fd4f2e4ebcf4060ac28f250399165deefbfae38c576f78dbd7e2a24738868d45`。

## 可证结论与根因边界

**这不是“冷Worker还未运行”的停点。原业务Run已成功持久化；完整页面端到端证明未封存。** 当前可实证的性能根因是旧P-A原生成/绑定来源证明在同一个读取链中反复完整重建，再叠加页面刷新多个顺序读取；测试桥没有覆盖这些等待的整体期限。具体被SIGINT打断的最后RPC、是否已进入某个特定下载步骤，原件不足以确定，不能以新profile追认原请求栈。

父级独立做了原fixture上实际只读GET `/api/internal/instances/{iid}`，本人回读其原profile/stack/SQL/result：HTTP200/36.943s，原DB hash无变化，含cProfile观测开销。16,220,454调用；35,984 SQL执行（SQL明细求和）；SQLite驱动耗时约2.184s。`source_scope_gate`589次，`verify_origin`14/7、`model_source`7、`verified_candidate`14、`read_release`5、`verify_job`2。20秒栈正在 `goal_applications.history→verified_candidate→text_apps.verify_origin→pa_spec_apps.verify_origin→pa_material_bindings.model_source→read_release`，父级线程等待TestClient返回。它证明Python/SQLAlchemy反复证明开销可以独立造成几十秒GET；不是原现场的完整栈，也不是已证明的pipe死锁。父级执行的该GET不算本人独立执行。

目前没有前版本同一条件profile，不能把全部延迟归因于新local-record guard或断言它是新引入回归。新family的metadata排除查询确实增加每次scope调用的固定负担，但现有重复历史重建是主要已观测热点。也没有证据表明是SQLite磁盘I/O慢、真实模型网络慢或缺少jsdom。

## 原停止点证据

原目录 `shared-d5eadc70/test_natural_spec_page_actual_0/`仅有fixture.db和info.json，无results.json、driver.log、model-wire/runtime-wire或逐请求IPC trace。因此没有完整页面PASS结果，也没有精确最后HTTP证据。

原DB有两个Run：

- 源应用生成 `run_dc5bdcd639164c6fbb66cac021b2a9c5`：PARTIAL，3次请求/2工具，符合候选生成完成后待明确保存的正常合同；不可把PARTIAL误写为生成失败。GA_APP_CONFIRMED为04:08:40.596481。
- 冷材料运行 `run_1358a115f9164ca6a05533cf7f2247d2`：SUCCEEDED，2次请求/4工具；同AppRun SUCCEEDED/result_version1，实例data_version1；read_pick、duties_pick、qualifiers_pick、merge_pick、check_pick、save_pick六个Operation均VERIFIED，JSON资源存在。该元数据证明业务运行完成，不替代重新授权的内容/语义核查。

时间线原件为 `timeline.json`：04:11:03.060771接受，04:11:44.272475 CLAIMED，04:13:03.108984创建SPEC_COMMITTED事件，原DB mtime04:13:06.950522，停止记录04:14:17。确认源应用至接受冷Run已142.464s，接受至CLAIMED41.212s，CLAIMED至终态事件78.837s。

精度限制：SPEC_COMMITTED在 `pa_spec_apps.py:1321` 的保存事务内生成，之后仍有job_scope_gate、最终verify_job、current authority/lease/deadline等核验（:1323–1352），所以事件时间不能直接当commit或Worker返回时间。原DB mtime与约3.84s后落盘相符，也不是IPC回包证据。只能说停止前终态已持久化，并有约70s的文件mtime后间隔；不能把全部74s硬算为某个后置GET。

原SIGINT记录409.132s，pytest总412.405s（日志412.41s）。原批两个具名完成PASS；PA生成页面明确NOT_VERIFIED，后置CSVfullreport没在原批执行。后来的直接natural-owner/CSVfullreport回归不能永久代替这个页面闭环。

## 测试桥可证的观测缺口

`tests/test_pa_natural_spec_ui.py:114–168`：Popen将stdout/stderr都设PIPE；主循环同步读stdout行并逐个执行HTTP/Worker命令；stderr直到退出循环才读取。NODE_PATH `/workspace/node-tools/node_modules` 已解析为工程node_modules，require.resolve(jsdom)成功，且原DB已执行到冷Worker，排除启动缺依赖。

`tests/pa_natural_spec_ui.cjs:8` RPC Promise没有期限；`:21–27` gesture等待所有实际handler Promise；`:10`的15秒wait仅保护个别DOM轮询，不约束HTTP/RPC/Worker。Python `process.wait(timeout=20)`在stdout循环和阻塞stderr.read之后，不能限制整个场景；没有活动请求日志或提前finally封存。这些源码足以解释“测试超过上界仍无可定位原件”，但没有原stderr内容/管道占用，不能实证stderr堵满。CSS仅6171字节，未发现该driver/web中的持续console输出；不能据此彻底排除所有pipe风险。

## 页面与后端重复证明路径

CJS`:160`在冷Worker命令后执行 `click(internal-refresh)`；`web/internal.js:410`依次：

1. `refreshInternal:181`：GET `/api/apps/{aid}`，再同时发releases/instances目录两GET；Python桥仍逐行串行处理。
2. `showInternalInstance:225`：GET `/api/internal/instances/{iid}`。`internal_api.py:331`先lifecycle.inspect_instance（:798→instance→read_release、data_rows→verify_instance_records:1120→verify_job:1036），随后route另开事务再次read_release，再对每个Run调用inspect_job。后者经过app_jobs.inspect_job:608→frozen_contract/source_scope_gate→load_binding，再verify_job。
3. 同一个showInternalInstance接着 `renderPBUse:1095` GET `/api/internal/releases/{rid}`；然后 `openNaturalLogic:1189`再次GET同一Release；两次都走完整来源证明。这里是确定的重复HTTP，不是推测。
4. 若原Run仍选中再showInternalRun；然后CJS`:173–188`读取同版清单、两个独立授权artifact GET并下载JSON/Markdown，核cold材料与条件/例外/未决项、PENDING、无旧源内容、精确一次提交及最终资产SHA。

热点内部：`pa_spec_apps.verify_origin:604`→model_source→`pa_material_bindings.model_source:129`先verified_candidate；随后`:138` load_draft(original)→apps.validate_frozen_candidate→pa_spec_apps.verify_origin→text_apps.verify_origin:152再次verified_candidate。后者history:303逐次重建初始消息/三次原请求/反馈与封存响应，内部反复frozen_contract→source_scope_gate。原生成证明不可删除，但同一安全读段不需要重复构造同一个已完成证明。

## 建议最小安全闭合片

1. **先补观测与期限，不以延长总timeout替代修复。** 每个RPC在执行前后追加BEGIN/END的id/command/method/path/耗时，finally保存已完成步骤和正在等待身份；stderr直接写有界独立文件或并发持续drain。全场景watchdog要覆盖stdout、HTTP和Worker等待并抓堆栈，仅操作核实自有进程。测得热点后再定预算，不机械给全部RPC15秒导致正常但慢的证明被误判。
2. **UI同次刷新只取一次fresh Release供两个纯渲染消费者。** 给renderPBUse/openNaturalLogic传同一新响应，只在同一次showInternalInstance调用栈、当前identity/connection/workspace/app/instance/generation及精确release_id/fingerprint下复用；不把response变成跨refresh缓存或写授权。所有后续明确业务写/成果读仍各自后端当前授权。
3. **instance API消除再次read_release。** lifecycle.inspect_instance已经在该调用中完整验证release，可从同一已验证结果返回release_fingerprint元数据，route不再为了该标量另开事务完整重放。保留typed/Run完整证明和返回前当前authority检查；不向HTTP暴露“跳验证”参数。
4. **有界传递完整原生成proof，而非通用缓存。** model_source的两次verified_candidate，以及load_binding已验证Release后verify_origin重复，优先使用内部服务器新建的同call proof packet；要求同connection、active transaction、thread、write epoch、exact user/project/runtime/app/run/draft/limits，完整原Goal/材料/independent seals/head/tables/hash均已核实；复用前重验收集到的全部逻辑authorities。任何SQL写、callback、事务、请求或范围变化立即失效。先窄定普通P-A绑定自然规范成功读取，复杂correction/logic/PB保留原路径。

现 `apps.validate_frozen_candidate(_reuse_origin)`仅核connection/transaction/user/draft/limits，不能原样当通用安全proof；缺epoch/authority/thread绑定。`pa_spec_apps._bound(_source_origin=True)`另有test_only+SQLite+SUCCEEDED限制，不能简单去掉限制扩大其权限语义。应复用既有proof_authorities/source_proof_write_epoch及严格原scope-segment设计，禁止全局、跨请求或只按fingerprint命中。

最小资格先对原DB只读profile iid、release、run、artifact及目录热点，比较结果byte/fingerprint与授权拒绝门保持不变；故意同call写epoch/authority或scope改变必须失效。然后只在全新合成fixture运行原valid一个页面场景，仍为3次生成MockTransport+2次自然步骤MockTransport，真实模型0，保留原check与下载/冷页/资产证据，不降低oracle、不扩十种故障矩阵。只有实际完成该原valid端到端资格，才能将这项NOT_VERIFIED关闭。

本报告未实施优化或运行长测；未调用真实模型、网络provider、Windows/PG/远端CI/部署。原始未完成场景维持NOT_VERIFIED。
