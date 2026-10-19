# 原两项集成失败的有界修复与验收

从 `96690a60591fc27c9c6aa35a6e10fd69f7f57539` 接续同一普通开发分支 `dev/production-trial-stages-20261018`，本环境为唯一产品写者。未返回旧满盘环境。08:11 UTC 本地 HEAD、08:13 实际远端均为该 SHA、工作区干净、可用磁盘 21,544,525,824 字节。云断连通知后 09:03、09:48 在同实例再次实际核执行、HEAD、磁盘和工作区；源码先后正常推送保存，未假定另有恢复实例。

原 MD correction Run 在工具写事务期间，后台遇真实 SQLite BUSY 后不再续期；仅加重试仍不足以防止连续前台写事务饥饿。修复复用 Store 原心跳和所有权检查，在业务事务边界外串行元数据续租，读取最近真正提交的原 lease，受原 Run 截止与有限次数/driver wait 约束。实际收到的回复保留 RECEIVED；已发布 fatal 后不再进入下一次发送/工具，未自动重发。

旧 V2 测试经普通 Worker 生成、手工记账且缺少实际控制器关联，原后端拒绝是正确行为。现在经原 submit_generate/submit_stage、真实 paired seals 和 PATrialBinding Worker、有限 MockTransport 完成实际生成、保存、Release/Instance、Source/Cold。关联标记仅在严格身份/冻结合同/双侧封印校验后被现有 context counters 接受，普通七键上下文不增加关联查询。三处已有只读 proof 复用入口接纳旧 PATrial 三次真实生成标记，原第一遍完整证明、同连接/事务/thread/write epoch/token、fresh Grant 与写入失效不变。没有造 executor、Grant 或改额度/资格证明。

实际 V2 隔离执行又暴露旧截止快照误杀：后台报 Original heartbeat interval ended 时，同一 Run 的前台已真实提交尚余约 20 秒的原所有者租期。SQLite natural 前后台现在用独立 renewal_lock 串行覆盖截止快照、原 Store 调用、提交后发布与 fatal 决定；原短 state 锁不跨 DB，业务事务没有反向取 renewal_lock。三个同步入口全部接入；原 PG 调用参数/发布分支保持。原 BUSY 特定恢复保持，没有新增 BUDGET 恢复或吞错误。合成时钟每次不超过 10 秒，与在途元数据协调后仍调用真实 heartbeat；30 秒租期、300 秒 Run/初审、3600 秒执行、900 秒 handoff、60 秒槽间隔均不扩大。

普通 Source 在 v10 的真实墙钟执行仍暴露长业务证明耗时问题：最后一次实际续租后 37.4286 秒报 Stale worker lease，已真实超期 7.4328 秒。保留该失败，未归咎为已证实旧问题或只加长租期。v11 只让无试用绑定的 test-only SQLite mock 运行接入原 SourceReads；普通资格要求三条实际 MOCK Attempt、parameters 完全缺少 pa_trial_binding 键、冻结 mock 自然生成且无 activation。原完整首证、fresh Grant、deepcopy、同事务/线程/driver/token/write epoch 和写后/退出失效均保持；绑定非 None 的既有试用分支、阶段资格与 _generation_accounted 不变。

## 实际结果

| 范围 | 结果 |
| --- | --- |
| v10 / aae3abd9 原 V2 七槽节点 | **1 PASS**，650.4557 秒 outer；实际 3+2+2 次有限合成发送，七槽 accepted、KNOWN，最小间隔 60.00037 秒；30/300/300/3600/900 原边界不扩大 |
| v10 / aae3abd9 其余 21 项 | **20 PASS / 1 FAIL**，273.9606 秒；原 MD、8 心跳、4 所有权、5 关联/资格、2 元数据检查通过，普通 Source 失败保留 |
| v11 / 08a966cf 普通 Source 原节点 | **1 PASS**，111.7964 秒；最终 SUCCEEDED，两个模型节点 VERIFIED 并保存唯一 typed 结果 |
| v11 / 08a966cf 普通读段保护 | **1 PASS**，18.8969 秒；真实三次 Mock 生成、完整首证/第二命中/copy 隔离、显式 null 退出普通资格、写后损坏拒绝、无写 Grant 到期拒绝 |
| v11 / 08a966cf 新 Store / 新材料 Goal Cold | **1 PASS**，171.2187 秒；两个 Mock 节点 VERIFIED，SUCCEEDED 保存，新材料/Goal 与旧答案隔离；不是 P-B Source 血缘验收 |
| 完整 mypy --no-incremental src | **PASS，113 源文件**，121.6604 秒；114 个源/config 输入前后稳定，所有产品字节与 v11 相同 |
| 改动的 9 产品模块及 4 个干净测试文件 Ruff | **PASS**；既有 V2 测试残留诊断另做全量对照 |
| 完整 Ruff | **FAIL，110 条**，对照原基线 117 条无新增；未做相邻历史清理 |

v10 的 12 个冻结文件对应 `aae3abd9c5c422b199f82e66570b4bd71be49621`，684 输入中 678 为提交 blob；v11 的 14 个冻结文件对应 `08a966cf5413295d49cdb942287e83d9f72ac6c7`，685 输入中 679 为提交 blob。两者各有六个生成包元数据，仅称独立字节归档及运行前后哈希证明。执行冻结工作树随后保存为源码提交，逐文件核对同一性；不把生成文件称为已提交内容。

各行按实际源码 SHA 分别归属，**没有单一新 SHA 的全用例 PASS 声明**。独审确认 v11 对已有绑定控制流和已知试用版本名单短路原样保留，因此未机械重跑 650 秒 V2 或已覆盖恢复矩阵；只补直接受影响的普通 Source、读段保护和 Cold。原 V2 实际通过仅属于 aae3abd9。独审源码/运行均为有界有限结论，受审范围无确定 P1/P2 或剩余待补动作。源码 seal 为 055e42213ecfb7f67766467c439997408ffcb45c50833711a65b867d707f0c85，最终运行补充 seal 为 5157620e4b222db10d9b69fd57b126f59bc1921939d156736cc9e172274a0da1。新 Cold 仅为 P-A，不代表额外 P-B Source 血缘验收。

## 失败与证据边界

原始失败和中间执行全部保存。9669+新增真实 writer-lock 复现用例确实 FAIL；retry-only 中间版原 MD correction 仍 FAIL。v7 批次中额外普通 Source 用例 FAIL，原 9669 隔离对照则 PASS，不能把它归为已证实旧问题；后续去除普通 counters 新增 SQL 并在最终冻结候选重验。

v8 的 20 项顺序执行发生原生退出 -11：592.9654 秒、14 个完成进度点、无完整 JUnit，78 字节 stderr 只在 300 秒诊断附近开始打印栈，原因未知；不能签 20 PASS。唯一同源码隔离重试关闭定时栈转储（fatal handler 仍启用、断言不变）实际 exit1/268.8551 秒，得到上述 Source FAILED 和后台旧 interval 错误。该失败有 JUnit 和原 DB/observer，不补签通过。v9 原子修复后作者 V2 预跑因新增 E701 格式诊断，在已核本人 PID 上 SIGINT 中断，exit2/73.6633 秒、684 输入稳定；修正仅一行格式后 12 候选 AST 全同，另冻结 v10 正式运行。

V2 唯一软件资格 stand-in 为 test-local _qualified，全部显式合成账户/MockTransport；账户/原始 Run/版本/关联/权限/额度 admission、reserve、capture、settle 仍实际执行。没有调用真实模型；合成账本不构成真实付费/免费额度实证，actual_paid 仍为未知。Windows、PG、真实账户/免费额度、人工语义/场景、浏览器新执行、全量 pytest、部署均未执行。原 GitHub Actions 元数据只读 GET 返回 Forbidden，未换凭据绕过、未手动触发 CI；自动 CI 状态未知。Git 正常推送成功不能推导 CI 通过。完整 Ruff 仍 FAIL，不称全工程全绿。旧满盘环境缺失独审报告没有补回。

证据入口：[原始归档与独审](../evidence/integration-regression-closure-20261019/README.md)。最终交付 SHA、实际独立远端核对、工作区/未提交/未推送差异另见交付回执；归档内源码 checkpoint 不自称文档封存提交。
