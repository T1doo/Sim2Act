# 精确版本 owner 逐项签收有限合同

本切片对应原 V5 §4、§5.4 与 F2-T01/T08。只接纳已有 `goal_application` 来源、`text.literal_evidence` 执行器的完整 GoalCard 应用。CSV、Replay、DAG、未知依赖、一般语义执行器没有扩展签收支持。旧 CSV 使用页的 PENDING 保持原义。技术结构及字面证据通过不等于业务目标通过，正式发布始终关闭。

## 人工声明与冻结条件

本人先手动选择 1–8 个不同的真实成功新输入 Worker 任务。任务输入必须区别于 Release 样例，绑定当前实例 revision 和 Release；任务及 AppRun 都成功、无错误、取消意图或 UNKNOWN operation；该实例不得有未结束任务。沿用现有 worker、来源与字面检查器，不新增模型请求或执行器。

PREPARE 追加待签收快照，冻结身份、项目、应用草案/Release 精确指纹、实例 revision/data_version/历史、当前 GoalCard 版本与内容、材料及授权版本、所选运行/合同/绑定/输入输出/结果记录/真实操作回执。目标正文以及 known、assumptions、unresolved、constraints、acceptance_checks 的每一原始项形成稳定条目；标题、resource_refs 等完整来源字段也展示。目标正文必有一项；空列表不能产生自动签收。

人工逐项明确 ACCEPT 或 REJECT，逐项填写非空依据。条目次序、数量和 ID 必须完整一致；不能删除未解决项、调换/复制条目或用技术 PASS 代替选择。所有项 ACCEPT 才记录此精确版本的人工 ACCEPTED；任一 REJECT 记录 REJECTED。两者都是 owner 的声明，技术语义仍 UNKNOWN，原生成任务 PARTIAL/goal_acceptance NOT_RUN 不被改写。测试中的人工选择为 SIMULATED，绝不代表真实用户语义验收。

## 原子性、版本竞争与不可变回执

POST `/api/internal/instances/{iid}/owner-review-requests` 接受 PREPARE、DECIDE、CANCEL、REVOKE。每次显式操作有唯一 request_key 和 expected_sequence；提交事务锁项目；PREPARE/DECIDE 重验当前内容条件，CANCEL/REVOKE 复核本人控制元数据、序列和独立 seal；记录与独立 seal 同事务追加。PREPARE/DECIDE 在取得当前内容授权后，还须核验全部历史 payload，任何较早记录损坏也不能追加。实例内序列唯一、用户/实例/key 唯一，最多 256 条记录；PREPARE 留出决定和停止的两格，DECIDE 留出停止的一格。PREPARE 有 15 分钟提交有效期；到期不能 DECIDE。已有决定也必须持续匹配当前全部条件才能作为当前签收显示。

DECIDE 指定精确最新 PREPARE ID/指纹；并发决定、迟到旧预览、目标版本/材料/权限/运行/新结果变化、实例切换及切回均不能提交。新 PREPARE 使当前签收重新 PENDING，不复用旧选择。CANCEL 仅停止精确最新 PREPARE；REVOKE 仅撤销精确最新 DECIDE，均要求依据并保留原记录。不更新或删除签收历史，不变更既有草案、Release、实例结果、来源、权限或执行状态。seal 和全序列检查拒绝单侧删除、重签 payload 或篡改元数据；不宣称能抵御同时任意改写两张表的数据库管理员。

GET `/api/internal/instances/{iid}/owner-review` 返回当前状态及元数据历史。附 `request_key` 仅读取原操作回执；历史 ACCEPTED 回执与当前签收分别展示，不能复活撤销、较新预览或失效版本。不存在原 key 时返回 OUTCOME_UNKNOWN/409，无写入。相同 key/相同请求只回旧元数据，相同 key/不同意图拒绝；浏览器未知结果只 GET 原 key，无自动 POST 重试。

当前授权检查先于读取受保护条件/结果。GET 当前状态在材料撤权或版本失效时隐藏这些内容；本人仍可读回记录元数据并按精确 ID/指纹 CANCEL/REVOKE，不恢复授权。其他身份不能读写或停止本人的实例签收。

## 页面与验证范围

页面展示完整精确快照、未解决项、真实新输入输出和操作回执，默认空选择、未勾选人工确认。读写响应绑定身份/项目/应用/实例/工作区选择代次和人工输入代次；输入或导航 A→B→A 仍使晚到响应失效。晚到结果不得清空较新选择、依据或夺取焦点。冷页面仅读取，无自动提交。

所有新脚本必须由固定真实 HTTP 静态路由返回 200 后才装入离线 JSDOM。验证使用 SQLite、进程内 HTTP、正常 Worker、明确 synthetic provider fixture 和实际 DOM 手势。JSDOM 不是原生浏览器；输入/导航 ABA 是受控 DOM 事件，不是系统 Undo 验收。完整256条历史耐久/性能资格、PG、Windows、旧源码部署升级、原生浏览器、真实模型和真实 owner 人工语义、完整 P-A/P-B、远端 CI 均需单独证据。本轮未运行的项目明确 NOT RUN。

实际测试、失败历史、独审源码指纹与 HTTP 资源凭证存于 `docs/evidence/owner-version-acceptance-20261011/`，最终运行后再填入结果，不以设计审查代替实际执行。
