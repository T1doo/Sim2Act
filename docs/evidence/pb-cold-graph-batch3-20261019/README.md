# P-B Cold graph 第三批：严格 origin 与 Binding/per-use/Authority 事实叶

基线 `51db08400b5f01c45e66210e8d01d8ddb605856b`，普通开发分支 `dev/production-trial-stages-20261018`。本批只修改获批五个生产文件及一个必要短测试文件；没有接入最终 Cold 图、shadow、新 executor、Grant、公开入口语义或生命周期/Store/锁/错误序变更。

`apps` 新增 dormant exact 私有 origin handoff，在原 draft gate、own_project、source-family、compile 返回后以及消费前重核原调用 scope、完整输入、角色六维 Limits/None、controller/Settings/Store/原 engine、TX/token/write epoch/driver/thread。严格模式缺失/漂移/同 facts 重入/退出后使用直接拒绝，无公开 origin fallback；异常原样抛。每次重验 exact fact 形状，不能用等值 dict/list 冒充 Limits/tuple。普通 default/dict 原匹配与 fallback 保留。生产 factory 调用点为 **0**，它不是 fresh Authority，也不补读缺事实。

其余四文件抽出十二个显式事实叶，原公开调用仍在原位置执行全部权限、Release/frozen、per-use 材料+完整 Goal、全量历史/多重集/基数/唯一性、NS/controller 独立字节、accounting、clock/counters/audit。阶段字段叶只产生缺少权限指纹的部分 dict；实际 authorization_fingerprint 仍在原末位读取后构造完整 StageAuthority。未来生产者责任及不能省掉的前置/后续检查见 [CALLER-RESPONSIBILITIES.md](CALLER-RESPONSIBILITIES.md)。

最终 `focused-v5`：**24 PASS、0 FAIL、0 ERROR、0 SKIP**（20 个新单位项、4 个现有兼容项），pytest 40.54 秒。新测覆盖 legacy 匹配/回落、严格 callback 后漂移/变家族/类型/原 engine/nonce/完整输入/异常/失效、实际 SQLite no-op/失败写及 driver total_changes、queue/per-use 完整 frozen 输入、独立角色 Limits 与部分阶段 DTO。兼容项为固定 CSV NoModel enqueue/重开/实际 Worker 结果、接受输入损坏拒绝、默认 real adapter 零 Attempt、权限先于私有批准正文。新单位测显式 stub 原 authority/lineage gates，不能证明成功 Source/完整 trial。

最终 Ruff 六文件通过；mypy 113 个源文件通过；三项 receipt 的 before/after 源哈希稳定且与 candidate-v3 一致。fixture-smoke 和旧 17 项 PASS 不重复累计。前三轮夹具错误保留原 stdout/stderr/JUnit；第一轮还因测中源形状门变更而 sources_stable=false，明确 NOT_ACCEPTED，未改签。独审发现并修复 dormant exact-shape/原 engine P2，失败候选与修正记录保留。

独立有限审查：**BATCH3_STRICT_AND_FACT_LEAVES_ACK，无剩余 P1/P2**；24 项 AST 对照与哈希桥通过。最终报告位于归档的 `independent-review/v2-frozen-strict-and-fact-leaves/REPORT.md`，SHA256 `21b2378cf9289c1402bb6bcb4ad98649042c63e5fbf856cf131ac33ec4764628`；96 成员 manifest SHA256 `5a34cf46e6b6c1ec90e588eee9b15a12003426c7a6832f282563010d7b2570bf`。独审未替作者执行测试，也未核验其后提交/推送/打包；后者由交付桥单独记录。

原始日志、JUnit、runner/receipt、冻结候选/差异、失败尝试、最终独审原件和哈希桥封装于 [raw-evidence.tar.gz](raw-evidence.tar.gz)，完整文件哈希清单在包内，归档总哈希/成员数见 [RAW-SEAL.json](RAW-SEAL.json)。本机完整证据目录 `/workspace/pb-cold-graph-batch3-20261019`；测试临时 DB、缓存和 pytest 别名不打包。归档仅有限原始证据，不依赖旧环境 bundle。

未跑完整 P-B、Source 模型 Worker、Windows、PG、远端 CI、真实模型/语义/场景人工验收或部署；本批没有性能改善结论。历史完整 P-B 仍 **FAIL_NOT_ACCEPTED**；`ModelSettlementRead.check/binding_key/full inputs` 独占成本仍 **UNKNOWN**。旧满盘缺失最终独审未补回。下一批/最终图尚未开始。
