# 已有 Report 的编辑保护：限定候选证据

开发基线：`afb2f1f3813fc3a4744923f31bbcb4666b88cccd`。
首次实现：`501db575c06196259157e3ad5054456e2a830e2d`。
最终产品与测试冻结：`a567e08fcf0e2135bdd02bd62e0e8c2ceb842a47`。
候选分支：`dev/report-edit-locks-20261009`；本轮不合入 `dev/f1-foundation` 或 `main`。

F2-T07 / V5 §9.3(6) 要求人工锁冲突保留内容。原公开锁只接收 CSV；本候选在既有 load_family 完整验证之后加入已有 `bounded_report/intern.conditional_report`，使用原 manual-edit-lock.v1 和 graph/node/lock CAS、明确确认、不可变同键回执、冷读与 superseded 历史。锁变化后仍需明确重派生。实际原 decision→explanation 展示规划因锁拒绝，无展示写入；解锁、重新派生和新精确规划后才允许原有限归档文本检查。未新增 API、表、身份、Grant、执行器、预算、模型或业务写入、正式发布。

页面只对 Report 的 LOCK_CONFLICT 或精确 `Historical project graph/authority/lock membership changed` 历史错误保留单独验证的当前图，不把旧计划当当前证明。所有其他历史、授权、seal 或未知错误仍清除证据；Report 不读取 CSV column history，CSV 原错误边界保留。

独审发现并促成修复了真实 UNKNOWN 回归：服务端已接受规划但响应丢失，另一应用公开锁定并重派生后，原键重试可返回 LOCK_CONFLICT，不能据此删除先前意图。最终实现发计划前冻结先前未知状态，只有首次精确 `/plans` 的 HTTP400 LOCK_CONFLICT 且此前未有未确认接受才释放未发送的草案。计划形状和当前上下文验证成功且保存之后才清 UNKNOWN；已发送定义、晚回执、旧闭包均保持恢复边界。

## 最终作者验证

| 最终 a567、LIVE=0 | 收集 | PASS | FAIL | SKIP | pytest 秒数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| SQLite | 85 | 83 | 0 | 2 | 335.61 |
| 隔离 PostgreSQL 17.9 | 85 | 85 | 0 | 0 | 598.80 |

SQLite 的两项跳过明确要求 PG application-role：新增 Report 和原 CSV 的 CRUD-only 业务角色冷读/同键回执；PG 两项实际执行通过。两个矩阵独立隔离并行，进程墙钟为 336.668 / 600.269 秒，不能作为 Windows 容量或稳定提速结论。原 Starlette/httpx 弃用警告保留。

每个后端含 **10 个实际 loopback HTTP/jsdom 页面病例、178 个页面检查**：新增 Report normal/ABA/unknown-plan 三场景，以及原 CSV lock、Report presentation、Report manifest、四项晚回执同应用/异应用/身份恢复。加载原产品 HTML 和脚本；页面源码哈希与请求正文随 `*-pages-and-upgrades/*/results.json` 保留。新 Report 三场景分别17/19/10检查：明确精确确认、锁回执已接受丢失、同键恢复、锁后无修改写入、同页解锁新计划、安全归档 explanation 文本、PROJECT 不误验收、冷读无写入、项目 ABA 与真实 accepted-plan UNKNOWN。

每个后端还含 **3 个实际旧源码升级病例**：立即前驱 afb 的 Report 公开锁负例与历史逐字保存、新版失效旧锚并要求新精确确认；CSV DAG 旧 `5a5543c902fbb78dd91c28c98386af51fb24dd67` 与核心 `1b65e94ebd81c1e31091b3078b8223328b726294` 的旧源码子进程持久历史、过期证明拒绝、新规划确认执行。源码模块路径/哈希、JSON 原存储字节和历史不可变表均在 proof 中保留，没有拿当前 fixture 冒充旧版升级。

其余涵盖新 Report 的真实锁→原修改拒绝→解锁→新计划/归档检查、旧定义拒绝无写入、冷 Store、12字段/CAS/确认/类型负例、7权限/来源/撤权/材料/seal/锁篡改/同键冲突负例、两个连接真实竞争，以及必要原 CSV/Report 回归。

`sqlite-final-command.json` / `pg-final-command.json` 是精确命令与 LIVE=0 条件；`run-frozen.py` 是当轮运行脚本。`source-freeze-final.json` 的341个运行源码/Schema/测试/脚本/依赖/工作流文件前后相同；`*-final-run.json` 记录匹配与退出0。文档/证据提交不改变这些字节。Ruff通过，mypy53文件通过，改动JS语法及手写代码/说明的diff空白检查通过。此为相关矩阵，没有无目的重跑完整 Engineering/native 集合。

## 独立审查

[FINAL_REVIEW.md](independent/FINAL_REVIEW.md) 与 [FINAL_REVIEW.json](independent/FINAL_REVIEW.json)：**LIMITED_PASS**，没有剩余本切片阻断。

- 501：独立 SQLite/API 17病例全部PASS，75.91秒；最终60个Python/Schema文件与501字节一致，17病例不追认为在a567重跑。
- a567：原产品磁盘HTML/JS、真实服务端封印fixture和受控API故障，42独立JS检查PASS；同最终驱动在精确501归档中仍预期FAIL于UNKNOWN保存。
- afb：两个新增公开Report锁API负对照均预期HTTP400 UNSUPPORTED_CAPABILITY；15明确deselected。
- 最终73个src/Schema逐字匹配Git冻结；实际accepted-plan→peer锁→同键拒绝且accepted历史保留的独立API证明存档。

独审没有代签作者PG、实际HTTP、旧源码升级或native。合成fixture每个Report仅原4次MockTransport模型形状交换，新增流程无真实provider调用。不能用合成输出证明真实材料、语义或整体P-A/P-B。

## 资源与失败保全

[FailureLedger.md](FailureLedger.md) 列全部中间失败和修复、故意旧版本负例；原日志/JUnit保留，没有覆写失败。私人数据库与旧源码archive保留在 `/tmp/sim2act-report-edit-locks-20261009` 和独审目录，不放入仓库。

PG只使用本轮标签与完整ID核验的容器、network none、Unix socket、零公开端口、自有合成数据库；结束测试schema/role/public表均0。自有容器和匿名卷已移除并读回验证（`pg-clean-counts.json` / `pg-cleanup.json`）；未碰未知资源。没有记录运行前计数，不能追认前后计数都已观测。环境状态变动后重新只读核验 HEAD、冻结字节、日志退出和进程，无重复启动。

`remote-before.log` 实际读回 main=`6f688e4dd80b5c81d41aecde90e360d3629f9c21`、dev=`afb2f1f3813fc3a4744923f31bbcb4666b88cccd`，原候选f540与bf939均未改变；新候选此前不存在。证据提交后普通推送与最终远端HEAD、无本地未推送差异在最终交付回复及私有 `remote-verification.json` 中精确核验，避免文档循环宣称自身SHA。已知空 `.git/codex-index-refresh.lock` 留存，未处理未知锁或僵尸进程。

## 持续开放的原边界

PROJECT `PENDING/BLOCKED_PARTIAL`、semantic `UNKNOWN`、owner `PENDING`、overall `NOT_ACCEPTED`、真实材料 `PENDING`、正式发布关闭、`LIVE=0`。PG resources-history/全量与探索超时 OPEN、HTTP200损坏响应提示限制、Windows900/Edge240/Node150未验收均不关闭。main不改、不强推、不部署、不改凭据/安全/网络配置、不调用真实模型。

下一步依据 [原方案关键路径](../../F2/DeliveryCriticalPath20261009.md) 继续实际 F2 功能闭环。计划用于立即推进和识别依赖，月底仅最晚底线。另一个参赛项目尚无可核验名称/源码/原方案与负责人，保持UNASSESSED，不宣称双项目已保障。
