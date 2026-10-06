# E18 原 V5 阶段门审查（2026-10-06）

依据原始 [分阶段开发计划](../sources/V5/分阶段开发计划.md) §4、§11.2 及 [产品设计](../sources/V5/平台产品设计.md) P-A/P-B、生命周期。原文、历史 AT02 和原 AT05 均不改。用户允许 F1 未签收时独立安全 F2 工程，不等于 §4.2 正式进入条件已满足。测试数量是工程回归数量，不是完整 AT 签收数量。

本轮仅补 **AT17_SYNTHETIC_FIXTURE**：真实 preview 持久事务中注入 test-only SQL 写入，在新连接读回；成功、两次实际写入后的回滚、重试、并发幂等和显式 namespace/绑定拒绝，核对两个真实内部 instance 数据及所有生产表权限等原始存储值字节不变（仅排除允许变化的 app_previews）。不是数据库物理页字节检查。见 [E18 证据](../evidence/F2-preview-isolation-20261006/README.md)。生产 preview 仍只读计算，adapter 未注册为生产 ActionSpec/gateway；所以合成隔离子项可关闭，**原 AT17 正式写动作/发布链仍 OPEN**。

| 原门/任务 | 已核查的工程证据 | 最小尚未完成项及状态 |
| --- | --- | --- |
| F1 / AT01—08 | E3 真实书生操作及独立 oracle；E6 原生 Server 工程链；后续持久队列/权限/回归。详见 [AcceptanceMatrix](../F1/AcceptanceMatrix.md) | F1 未签收。AT01 Win11 NOT_RUN；历史 AT02 两主体两项目完整初态不满足，保持 PARTIAL，不能补写历史。AT03—08 工程子项不能替代逐项签收 |
| F2 正式阶段门 | 用户授权并行工程；目标卡、固定声明式候选、来源证明、内部生命周期/worker 已实现 | F1 正式签收前置未满足；AT09—22 全部正式验收尚未闭合。不能描述 R0-alpha 完成 |
| P-A / F2-T01、T02 / AT09 | 版本化目标卡/验收契约、授权 CSV 或可信目录、固定 MOCK 声明式候选、真实计算和历史 | 固定手工模板不证明从新目标自主规划/工具选择；不同目标生成、真实成果和发布链未完成 |
| P-B / F2-T03 / AT10 | E14 可核查成功 LOCAL_DECLARATIVE_TASK + 独立 oracle；拒绝 FAILED/UNKNOWN/PARTIAL 来源；最小证明/显式退休；冷会话新输入新结果。E15 [冻结合成子项](AT10Subitems.md)及 PG 锁序 | 固定合成任务族子项完成，通用提取变量/逻辑/模型节点及更多来源链未完成；源证明当前授权仍必要，不宣称撤权后复用。完整 P-B/AT10 OPEN |
| F2-T04 运行器 | 固定可信动作、严格声明式输入输出、有限现有步骤 | 通用有限 DAG/受控分支和不同任务族运行证据不足，不能以单固定模板代替 |
| F2-T05 身份/入口 / AT22 | user/project/app 当前权限交集；内部 instance 复用现 app runtime，不自动新增 Grant | 正式应用使用入口及发布权限/独立实例身份策略待明确；没有通用写动作的页面/API一致性证明 |
| F2-T06 真实成果/本地数据 | CSV 真实新计算、可回读结果；E16/E17 类型化 instance result 版本账本 | 通用业务记录写入、文件/受控视图组合及生产 writer 的 schema/授权未实现。E18 note 仅合成测试写，不能提升此门 |
| F2-T07 / AT13—15 | 既有固定对象/指纹；未提供原 V5 局部修改验收证据 | 原 V5 所列三类局部修改、依赖不确定扩大检查、人工 LOCK_CONFLICT 未验收；不延后到 F5 冒称完整增量 |
| F2-T08 / AT16 | [E16 内部生命周期](InternalLifecycle.md)：不可变 Release、精确一次性批准、版本 CAS、两个实例数据、兼容升级回退保留历史 | 内部 service 已验；正式批准 UI、发布入口/真实部署和通用数据迁移政策未启用。类型化 result 兼容子项不是完整发布验收 |
| AT17 | 本轮实际事务内受控 note + receipt SQL 写，独立连接读回/回滚、全部生产存储列字节不变、权限/namespace负例 | AT17_SYNTHETIC_FIXTURE PASS 以最终证据为准；原正式 AT17 OPEN。错误 namespace 拒绝为测试 adapter guard，不冒称已存在生产 writer 的隔离能力 |
| F2-T09 / AT18—21、AT20 | [E17 持久 AppRun](PersistentAppRuns.md)：实际 PG worker 子进程、提交前后崩溃、另一进程恢复、heartbeat/pause/cancel/fencing、未知 operation 保留 RECONCILING/取消意图、原子本地 result；本轮预览重试 | 纯计算/本地原子结果及注入未知账本子项已验。AT19 受控外部服务已完成效果但丢响应链未实现，故 AT20 在途外部效果核对未完整闭合；不宣称外部连接器恢复 |
| WindowsServerCI | E17 精确 8b14cee / CI37415214667 成功，PG340PASS/0SKIP；E18 精确源码 CI 另记证据 | Server2025 原生 PG/PS/Python 工程回归。admin=true、EnableLUA1，不替代 Win11 普通用户验收或浏览器 |
| Win11 | 目标明确，Server 原生工程证据已存 | NOT_RUN，需要真实 Win11 原生普通用户环境；不能借 WSL/远端 Server 代替 |
| 真实浏览器 | 早期 E8—E10 真实 Linux 浏览器有限流程证据；后续 DOM 检查另存 | E11 起受保护 Chromium 环境受限，后续渲染/手机/焦点视觉及 Win11浏览器未签收。E18 没有前端变更，也没有新增真实浏览器证据；不关闭 sandbox 伪补 |

下一步需要真实决定或接入，而非继续堆 CSV 邻接功能：

1. **首先补环境与 F1 签收输入**：接入获授权的原生 Win11 普通用户及能保留 sandbox 的浏览器环境，明确完整两主体两项目 fixture 初态并新跑，不篡改历史 AT02。当前真实模型预算 **0**；最多追加两次仍待批准，禁止 LIVE/models 探测/自动重试。两次也不保证全部验收。
2. **明确下一真实任务族与验收 oracle**：提供授权来源、未见目标/输入及预期成果，分别验 P-A/P-B；需要模型时先解决预算。固定 MOCK 模板不能消除这项依赖。
3. **若推进正式发布/写动作**：先决定受限 ActionSpec、preview/instance namespace、数据 schema/兼容迁移、批准 UI 和最小授权；之后另阶段实现生产 gateway/发布链并重跑正式 AT16/17/22。本轮没有开通这些能力。
4. **若优先完整可靠性**：另阶段接入明确标记的受控故障服务（非真实业务外发），观察已派发效果丢响应后的 oracle/幂等核对和取消意图，补 AT19/AT20 在途链。现有纯计算恢复证据不能替代。
5. **局部修改能力仍留在 F2**：按原 V5 三类修改及人工锁/不确定依赖冻结验收，再实现必要缺口，不移动到 F5。当前仅记录未完成，不自动扩大本轮。

这些是后续阶段所需输入/决定，不是本轮已获授权的生产写、正式发布或额外真实调用。E18 在合成隔离证据与阶段门审查后结束。

E18最终精确源码925e560dc1a196c6c4747cb349d558156a721c0f/[CI37416936441](https://github.com/T1doo/Sim2Act/actions/runs/37416936441)SUCCESS：PG353PASS/0SKIP；LinuxPG352PASS/1WindowsSKIP、SQLite332PASS/21PG平台SKIP；独立13PASS。合成隔离子项PASS，正式各门状态保持表述。全证据见上链E18目录。

## E19 内部入口增量（仍非正式发布）

依据持续开发授权，原F2T05/T08/T09现有只读service接入[认证API/UI](InternalEntry.md)：精确冻结snapshot批准、内部Release、独立instance结果版本/历史、持久AppRun及pause/cancel/resume/reopen。既有注册只读action/gateway，0LIVE/无新Grant/表，正式发布部署仍false。当前T05/T08表中“内部service”工程证据增加实际页面/API入口；正式发布入口/独立instance身份政策、通用writer与迁移仍未完成。27 actualHTTP/jsdom不替代真实浏览器/Win11视觉，AT22只增加固定只读链路工程子项，不签收完整AT22/F2。其他原门不提升；最终aggregate/精确CI另记本轮证据。

E19精确源码aaf07f49b3d32eeb360d8cd60a52a4fad22959fd/[CI37419363378](https://github.com/T1doo/Sim2Act/actions/runs/37419363378)SUCCESS：PG372PASS/0SKIP；LinuxPG371PASS/1WindowsSKIP、SQLite350PASS/22SKIP；HTTP/jsdom29PASS，独立18PASS/1PGSKIP与UI竞态/最终mainJS静态。内部入口切片交付结束，正式发布部署false；兼容switch service尚未接页面，通用writer/迁移仍无。首轮AT05启动失败未定位、原记录保留，单独及完整重跑通过；protected-browser仍BLOCKED、Win11仍NOT_RUN。下一必要原规格接入/决定保持上述列表，不借工程总数签收。
