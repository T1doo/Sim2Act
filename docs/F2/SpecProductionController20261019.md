# SPEC 默认关闭生产控制器接线

从本地 `a343c60a8446d697b684d47862d9a9f1c61d7182` 接续。用户授权工程实现，不要求先提供真实账户值；本片把已有字段和控制器接好，缺少有效事实继续拒绝。本轮不新增 executor、Grant、审批层、模型供应方、数据库表或费用凭据。

`ProductionTrialBinding` 只接受原 P-A TrialContract/TrialContractV2，复用既有闭合合同、精确账户及七槽 3+2+2 验证。Worker 的五个 `--spec-production-{user,project,trial,approval,account}` 元数据选项必须全给，才通过 `spec_production.install` 选择原已保存试验；没有自动发现或从候选 DTO 导入许可。原模式、live_enabled、application_generation_activation_enabled、provider/model、token、非 test PostgreSQL Store 及无替代 transport 都须匹配。未改这些配置或任何凭据，默认关闭。

固定 `production_evidence.resolve_account` 的函数体保持缺源 LIVE_BLOCKED，未安装任何生产账户事实。原软件 `_qualified`、合同批准、阶段批准、完整 Goal/材料、账户 quota、Run version/fence、租约与期限、撤销和 durable journal/CAS 继续校验。单独 preflight 的结果始终 live_allowed=false/dispatch_authorized=false，不是可复用发送凭据。

生成的 frozen mode 接续到同源应用逐次运行；模型 reserve、实际 Attempt、归档、计账及同 Run 的业务结果均保留独立生产 marker。公开两个 offline sender 入口在任何来源/账本读取前拒绝生产绑定；生产捕获历史以原 Run frozen mode 防止降级，旧无 Core Attempt 的 policy-only 合成历史仍可回读。已收到的 body/usage 不因准入撤回而丢失，原结算拒接受并停止账本。

沿用原同步读段证明复用，只加入 exact 三个生产 marker；完整首证明、owner/权限重核、同 Store/连接/事务/线程/写入 epoch 和失效条件不变。这项复用仍仅限原 test SQLite；没有非 test PG 性能结论。P-B 生产绑定和原离线来源提取限制未开放。

## 验证记录

本轮共 **7 个唯一节点最新 PASS，15 次节点执行为 13 PASS / 2 FAIL**，不是最终单批 7 PASS。

| 批次 | 实际结果 | 范围与限制 |
| --- | --- | --- |
| first-boundaries | 2 PASS，11.73s | 初始默认/缺源与收到后撤销；仅保留JUnit和工具输出，未保存raw stdout，期间源码hash不是严格事前冻结；received断言当时较弱 |
| qualified-first | 2 PASS / 1 FAIL，20.55s | 155输入无变；捕获来源重算漏传生产分支，生成第一响应后拒绝；原件保留 |
| qualified-second | 2 PASS / 1 FAIL，285.32s | 155输入无变；生成三次成功，Source无节点请求、仍RUNNING；当时无异常观测，唯一原因未证实 |
| qualified-third | **5 PASS，615.24s**，外618.716s | 156输入无变；默认拒绝、完整3+2+2至Source/Cold SUCCEEDED、公开offline前置拒绝、收到后撤销保body/usage及旧无Core Attempt历史回读。7+1+1有限Mock，真实0 |
| metadata-final | **2 PASS，170.86s**，外175.104s | 最终151输入无变；完整live/mock结果引用对象仅差零字段，原单节点自然应用生成3+节点1实际Mock并完成保存/回读。该批没有controller模块的autouse HTTP tripwire，runner沿用的旧标签已另存更正 |

隔离生产夹具仅在测试进程替换 environment、固定 resolve_account 和软件 _qualified，使用真实原控制器/Store/账本及有限 MockTransport，并阻断普通 HTTP。合成数据库的 LIVE 字段表示被测分支，不能证明真实供应方、免费权益、不可收费或语义验收。默认/缺来源节点在claim前拒绝，全55表相等；公开两个offline入口无SQL/来源/发送；在途撤销后实际body及已知usage保留、账本停止接受，只有一次Mock。

第三轮原完整链的7个Attempt均与原Run frozen live、独立生产marker、capture两镜像的完整identity及实际request/response bytes相符；账户间隔均≥60秒。生成PARTIAL，Source SUCCEEDED/v1，Cold SUCCEEDED/v2；人工PENDING/语义NOT_RUN。独审随后发现 `real_model_requests:0` 误报风险，最终仅从已验 frozen contract.mode 派生内部run_mode，LIVE省略未知真实请求数，MOCK保留旧0。该字段修正后 **没有重跑生产七请求整链**：归一化模块AST仅上述两处差异，原写入/verify调用不变；当前bound+receipts在本轮闭合复制库上的两Run投影都仅删除原0字段，55表不变，并有最终formatter与旧MOCK完整单节点回归。未迁移或验证兼容未发布WIP中旧LIVE零字段记录；不得把这项桥接写为最终格式完整七请求实测。

字段修正前执行源码还对同两Run做4个owner/artifact GET，均200且55表相等、Worker/模型0。Cold v2后Source v1 owner仅旧元数据、content_access=false/VERSION_CONFLICT，Cold可读且PENDING；不声称两版都可新鲜人工验收，也不抬为最终字段格式GET验收。

最终Ruff及源码/测试diffcheck通过。定向mypy实际FAIL：14个当前目标与13个HEAD已有目标均为同8条旧诊断（含继承Literal与旧Any/None/动态异常字段），无新增诊断；未声称类型检查通过。原始命令、JUnit、stdout/stderr、冻结输入副本、有限Mock正文、闭合55表、源DB与独审见[证据入口](../evidence/spec-production-controller-20261019/README.md)。

未执行 Windows、native/浏览器、真实模型或场景、PG 并发、远端 CI、部署或发布；旧满盘环境最后独审缺失不补签。保留既有本地提交，不做远端或 auth 探测/推送，当前远端 HEAD 与差异未知。
