# F2-T05 自然应用入口：P-B 原完整合同执行证据

状态：**FAIL_NOT_ACCEPTED**。本轮最后一次有界原完整 P-B 测试失败，不能宣称整体功能或 Cold 完整运行通过；已按最新要求停止功能修改和重跑。

产品与测试源候选：`2b3846d0802ef2875d9665acc1280b949d1a4131`，普通开发分支 `dev/production-trial-stages-20261018`。此 SHA 已普通推送并用 `ls-remote` 核对。本目录证据提交只新增文档和原始包；交付回执另核 `src`/`tests` 树相等，不把证据提交称为已重新执行的源 SHA。

## 可见入口与范围

应用目录已列出保存自然 P-A/P-B，显示家族、定义版本和逐次 TXT/MD + 已保存 Goal 适用范围。显式打开后选择现有 Release/实例，再走原逐次预览、确认、提交；成果卡能打开同一 Run 的结果与人工验收合同。目录、账号/项目/实例选择、迟到回调和防重复提交沿用已交付控制器。

入口实现与此前有限 HTTP/JSDOM 证据见 [入口合同](../../F2/NaturalApplicationEntry20261016.md)、[已有入口证据](../natural-application-entry-20261016/README.md)。本轮相对原远端684的 web 字节未变，没有宣称重新跑过那些入口门。先前可见入口有限审查通过不替代本轮原 P-B 完整链。此前额外历史准备触发 SQLite 锁的失败原件仍保留。

本轮复用原 per-use、Worker、durable intent、当前权限、版本、租期、时钟和预算合同；未新增 executor、Grant策略、正式发布或真实模型许可；原逐次合同明确确认后的既有授权处理保留。

## 有界收敛

最新要求限定：完成Source定向核对及必要质量门后，只再执行一次有诊断的原完整链。若仍失败，封存真实 `FAIL_NOT_ACCEPTED` 及下一最小待定位点，不继续叠加微优化、通用缓存或外围矩阵。此最后一次为 `anchor-readback-full-pb`，实际2026-10-19T19:12:22.213064Z至19:25:29.869363Z，外层787.656746秒；标准pytest 1 FAILED / 773.48秒。

## 当前改动

- 完整 P-B 来源证明在同连接、同事务、同线程、无写入的受限读段内减少重复解码与查询构造；实际来源、权限和 Run 边界仍重核。失败清空证明缓存，写入、退出或身份变化使旧证明不可复用；不缓存公开 Binding/StageAuthority 或跨写授权。
- Cold 本地写后读回保留完整首轮与写后证明，再对同段实际读回补查当前权限、完整 Run 条件和时钟。新 continuation 的有效 Cold 路径只有最终完整运行实际经过时才能计为运行证据；单位 stub 不计为该证明。
- 自然模型预留的原配额等待保持锁外。原有受守卫同步续租保留在调用者原位置；预留事务在取得本次续租写锁后重新检查 fatal/stop/原数值截止，事务先结束再释放锁，后台仍可在配额等待时续租。这不保证等待后恰有新30秒；真实 Store.guard/preflight/预留门继续在旧租期不足时拒绝。未增加租期、TTL、Driver 等待、重试次数或模型额度。元数据 helper 本身不是新的 trialTTL/账号授权证明，原完整门仍负责这些边界。

- 最后改动只有 `goal_applications.py` 1+/3-：在重核实际权限后，复用刚完成的完整身份锚点读取；两次读取之间原只有本地比较和读段检查。保留首次完整证明、最新锚点比较、owner/项目/当前权限检查和写入失效；未新增范围证明缓存。

## 实际执行门

所有模型交换均为有限 `httpx.MockTransport`；真实模型/真实账号 IO 为 0。原完整测试保留 HTTP tripwire、原断言、原 30 秒 lease、300 秒 Run、1 RPM 与账本上限。旧 Run 均不重启、不续跑、不拼接。

| 门 | 实际结果与限制 |
| --- | --- |
| 新预留串行与原续租串行 | 标准 pytest 6 PASS：配额等待期间真实 SQLite heartbeat 提交、预留提交后后台才能进入、等待后 fatal/stop/数值到期拒绝、错误请求家族先拒绝；自然 recipe/journal 和配额调度为显式单位 stub，0 模型。 |
| 最终质量门 | 最终新增改动 Ruff 1 文件 PASS；mypy 113 源文件 PASS。之前预留修复 Ruff 4/mypy113也实际通过。首轮 mypy 一条上下文管理器类型错误的 FAIL 原件保留；补类型注解后通过。 |
| 原观察器组合与源桥 | 原 `observe_reservation_reads` 函数/断言未改的组合用例，单独标准 pytest 1 PASS；真实 SourceReads/Store.guard/SQLite预留，资格及recipe/journal为显式unit stubs。前6项在2caf通过，仅追加该用例到d4，产品src完全相等；2,118个输入各运行前后稳定、719 Git文件核对，1,399未跟踪JS依赖仅有哈希。此前69dirty/f993/866类型修正桥作为历史证据保留。 |
| P-B 来源 SQL 形状 | 7 个旧/新实际 SQL/参数/结果或错误完全相同，752 条记录；6 个完整 bound/audit 值相同，11,045 SELECT/臂；这是结构相等证据，不是30秒耗时保证。 |
| 原写后 continuation 边界 | 分次标准 pytest 15 PASS、17 PASS、1 PASS、2 PASS，保留设置/控制器来源、sticky drift、实际尾部权限撤销等原件；不能合称一次19项 pytest。 |
| 最后改动定向门 | Cold6完整值相等、SELECT11045→10487；实际Source6完整值相等、SELECT4010→3680。4个结束副本helper边界通过（非pytest）：同段复用、实际NoOp写后重跑完整首证、锚点own_project回调实际NoOp写导致失效拒绝、当前权限回调实际撤权拒绝且不fallback。0传输，三个注入SQL写入只在自有副本，原库未变；不续任务或改变Run的lease/版本/状态。 |
| 最终原完整 P-B | **FAIL_NOT_ACCEPTED**：1 FAILED，6有限Mock（Gen3+Source2+Cold1），真实模型/账号IO 0。Source SUCCEEDED/2 VERIFIED Attempt/6 VERIFIED操作；Cold RUNNING、result null，1 REJECTED_KNOWN Attempt，读取操作VERIFIED、模型操作REJECTED_KNOWN。2,118输入前后一致，719 Git blob与源2b完全相同。 |

本轮原完整链失败原件均保留：9b Cold 写后超租期；44 Source 首次预留前失败；57 Source 预写前到期；962 Cold 写后重复证明长尾失败，77.54秒具体原因 Unknown；368 Cold 第一组预写前到期；69 Source 第二次预留 `BEGIN IMMEDIATE` 被本次后台 heartbeat 持锁阻塞，Cold 未创建。69后台事务持锁20.585秒/该段线程CPU9.386秒，原 guard 比较时刻 Unknown；后台 worker heartbeat UPDATE 最终回滚，不能计为 Run 续租提交。866另一次完整链实际在Source首次预留前触发原观察器tokenNone断言，3Mock/0SourceAttempt；这是移动renew到reserve内产生的组合缺陷，已恢复原位置并补原观察器组合单位门。d4随后完整链首败推进至首次Source发送守卫：预留已提交，原始33.156秒事务3583SELECT/0写，进入时仍有29.930秒lease，首次predicate晚3.223972秒；后续归档中的第二次predicate晚7.745238秒不能误称首因。Source有STARTED Attempt及PREPARED模型操作，只有生成3Mock，Source没有实际传输，Cold未创建。另进程只读剖析不足以解释原活运行CPU/heap长尾；入口再次renew不能解决这个已满租期的事务。失败没有被单个成功读段、局部用例或时间测量替代。

静态审查和中间终态审查分开封存。v18 明确 `INTERMEDIATE/NOT_ACCEPTED`；v19曾漏审移动renew与原观察器的交互，v20新增P2更正并保留旧seal；v23独审d4发送守卫真实失败，v24只核最小冗余读取设计，v25核2b源码/结构/边界/质量；[v26最终终态独审](final-review.md)已封存，结论为 `FAIL_NOT_ACCEPTED`，不沿用旧静态结论作运行通过声明。原旧环境满盘未落盘的最后独审没有补回。

## 最终失败边界与最小待定位点

Source为 `run_a5492d323be841d4bc9963d846653fd3`，Cold为 `run_dc0aa608b5684471b1f6ed4523372b0d`。本轮越过先前Source首发送守卫失败点，完成Source、提取、目录NATURAL_PB、显式Cold review/提交及同key去重断言；但并未完成Cold、最终两次Cold模型/7槽和完整结果验收。

Cold第一次本地读取确实进入一次有效写后readback continuation：stamp present=true，consumed=true且输出清除，实际尾部权限8项。它不是模型响应结算路径，也不代表Cold完整通过。

本轮首错在Cold首次模型响应结算：`natural_spec_runtime.advance_model:1025 → settle_verified → check_commit → _admission` 最末时间检查，原报错 `VERSION_CONFLICT: Production admission expired during verification`。结算TX从1792437887.7868092到1792437918.1254194，30.338610秒/线程CPU30.233703秒，33,334条SQL（33,329 SELECT、5次写入全部回滚）。入口仍有29.993279秒租期；最后原Run谓词在1792437916.5787017返回时尚余1.201387秒。随后完整 `_pb_source` 到1792437918.0804036退出，已晚于已提交lease1792437917.7800884约0.300315秒；最终require的精确时刻未采集，只能界定在来源核查退出与TX body_end之间。

已知模型响应归档和接收保留；失败结算的VERIFIED写组回滚，随后另事务持久化REJECTED_KNOWN，不重发。最终Cold Run仍RUNNING/result null，不能伪称成功、已终结或已恢复。原数据库SHA-256 `831e5047760e9d134f3d3dd03e4154f7c6923612f9e32297db3564f5d75a02de`，只读导出前后相同。

下一最小待定位点是**同一个Cold模型响应结算事务内的完整绑定/admission重复核查、写后完整证明与后续读回/settle_verified链**。这已是满原租期开始的事务，不是入口再加续租即可证明解决的缺口。写后证明仍必须完整，不能跨epoch99→104携带旧证明；本轮没有继续实现缓存、延租、改300秒Run、跳真实source门或开启外围矩阵。原活运行耗时波动原因仍未完全解释，SELECT减少不是整体交付价值或性能因果证明。

## 原始证据与限制

归档已包含原命令、stdout/stderr、JUnit、执行前后哈希、结束行只读导出、22份提交源码快照、独审报告和 manifest。1,881个成员的名称集合和逐成员 SHA-256 已全量验证。原始目录封存后不再写入。

完整包为 106,322,404 字节，SHA-256 `8b82b64e8359204fa60db653c44b1ec100ef6cbf5a32b3c8226b747ef12f7d3a`。因超过普通Git单文件限制，交付为[第一段](pb-cold-local-read-raw.tar.gz.part01)、[第二段](pb-cold-local-read-raw.tar.gz.part02)、[第三段](pb-cold-local-read-raw.tar.gz.part03)，按该顺序拼接即可恢复同一完整包；拼接流SHA-256已验证。完整原包另保存在本指定环境的自有交付目录，未使用Git LFS或新增付费存储。

- [原包校验回执](package-receipt.json)与[分段回执](multipart-receipt.json)。
- [原始清单](RAW-MANIFEST.json)：SHA-256 `fbc12d2bcf3a8fb7f4f75dc5180130aed4c3f29e760269f2ee0c953060110eb1`。
- [不可回写封印](RAW-SEAL.json)：SHA-256 `7dba87a9e0052add625ba1e08fb5c16d167a6cec8ceb50c172b811475ff5aa70`。
- [全部实际阶段结果](phase-results.json)、[输入身份及局限](input-identity.json)、[源与断言桥](source-and-assertion-bridges.json)。
- [最终独审报告](final-review.md)：SHA-256 `5c7716773a062b12614cd3497716a5f3eeda1f22accc98ffa6aa86b8ea3ddd09`；[独审清单](review-manifest.json)：SHA-256 `169e8b2ff3dfed1da66c2b971962497a64af94f3bb153ae33bb7263c22f2591f`。

19:32 UTC 环境恢复后命令成功。原执行会话为99964，终态已于19:25:29 UTC写入；恢复时没有存活的该测试Python/pytest进程。启动器没有持久记录数字PID，不能事后补造。未重发测试、终止未知进程或删除锁；原件中的 `environment-recovery-1932.json`记录核验与该证据限制。

Windows、原生浏览器、PG、部署、真实模型/真实材料场景、真实用户与语义验收均未执行。远端CI执行结果未核验，旧Actions API403未绕过；普通推送可能触发既有workflow，不宣称任何远端CI通过。本轮没有重复已有 Worker 恢复或相邻故障矩阵。既有合成合同中的 `owner_acceptance=PENDING`、`semantic_status=UNKNOWN`、`semantic_goal_acceptance=NOT_RUN` 不升级为真实语义通过；本次Cold没有结果，也未达到最终owner断言。

Source定向A/B脚本继承了旧 `audit_cold`/`ENDED_COLD`标签，实际按 `probe[stages][source]` 和原DB760e…读Source；原件未改，另有 `anchor-source-structure-label-note.json`澄清。所有执行门哈希稳定不代表Python/主机环境密封，时延波动和原活运行CPU原因仍未解释。
