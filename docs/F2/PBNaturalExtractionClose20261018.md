# P-B 未受理原提取 key 的安全关闭

本阶段从父级有限通过的 `3d1a3160fda6e9bfead96fae8a40935617270da4` 开新普通开发分支 `dev/pb-extraction-close-20261018`。仅 root 写仓库，测试草稿和独审在外部目录并行。默认 Git 网络可用，原远端 `8fc70cc` 是祖先，开始约25GB可用；不依赖旧满盘实例或旧 bundle。

## 可见路径和封存合同

原提取提交前已存17字段票据，但请求若尚未抵达服务端，原 GET 的 OUTCOME_UNKNOWN 会永久锁定编辑。本轮在同一成功来源面板新增明确按钮“确认仅关闭尚未受理的原 key，并拒绝迟到提交”。仅当前获权来源、合法原票据和同scope Web Lock允许调用。POST 成功仍保留票据和锁；用户必须另外点击原 GET，页面核对独立原17字段、完整CloseInput指纹和完整回执指纹，才清除此原票据、释放编辑。不会自动改key、重发、审阅或提交；新提取仍需用户重新审阅并确认。

新端点为 `POST /api/projects/{pid}/natural-spec-task-runs/{rid}/extractions/by-key/{key}/close`，输入只有 `{identity: 原严格17字段, consent: CLOSE_ONLY_THIS_UNACCEPTED_PB_EXTRACTION_KEY}`。身份中的候选应用/runtime与hash描述原意图，不提供权限。关闭前后完整重核原成功来源及Release/Run/结果版本/来源证明，保留原当前权限。未受理目标后来失效不妨碍关闭，也不重读其Goal/材料。

复用既有项目事务/锁和 `delivery_graph_requests` 双记录，仅写 `pb_natural_spec_terminal` 与 `_seal` 两行；每个来源Run最多64个关闭key，无新表/执行器/Principal/Grant/模型调用。服务端15字段回执namespace为 `pb-natural-spec-extraction-terminal.v1`，状态 `CLOSED_NOT_ACCEPTED` / `NOT_ACCEPTED`，钉原17字段和完整CloseInput/hash，自身以去receipt_fingerprint的完整对象计算SHA。`request_fingerprint`是原完整ExtractInput指纹；账本及 `close_request_fingerprint` 是本次完整CloseInput指纹，两者不混用。`metadata_writes:2`说明首次双行封存，重复关闭和GET不追加行。

所有原 `_extract` 调用（包括原trial转入）在相同项目锁及source_gate后、review/既有受理短路/业务写入前检查永久fence。先POST成功则关闭409、原结果和恢复路径保留；先关闭则原或改body的同key迟到POST409。任何单半封存、错位PK/独立wire锚或多余冲突封存都不能作为已关闭回执，但继续阻止原key再受理。

未受理判断同时检查原marker、独立账本半记录、派生应用来源锚、预期应用/runtime存在及项目可归属孤儿runtime；缺少marker本身不是未受理证明。发现仅用标量ID/header/来源锚。完整marker和原request双记录仅在既有目标/source scope_gate后读取；每个相关应用必须有唯一本人marker、恰好四份原PB账本以及全部原指纹一致。残留、未知家族、权限不足或扫描超过64应用/256账本时保守UNKNOWN，不写关闭凭据。已受理兄弟应用失去目标权限会阻止本来源其它未受理key关闭，这是明确的保守可用性限制。名称/Grant只是拒绝孤儿疑点，不能证明所有权。此有界检查不承诺发现所有独立锚同时被协调删除的任意数据库伪造。

## 冻结的必要验收

后端七个唯一SQLite/实际HTTP节点：未受理→双行持久关闭→冷Store原GET/幂等/迟到原或改body409；目标后来失效的独立关闭及读屏障；已受理不可取消；两个独立连接分别close先与POST先的真实事务重叠；本人项目/来源/权限/严格身份；单半封存、错位PK、受理残留/多余半账本与单行插入失败回滚。故障注入仅改命名的合成已实际受理记录，不伪造成功。

两条实际完整页面/JSDOM路径：控制的请求抵达前失败保留原wire→冷页原GET未知→明确关闭POST保票据→另GET核验清票据→fixture仅一次投递原exact bytes被409→用户另行审阅/确认新key成功；实际已受理201后控制丢回执→冷页关闭409→原GET/fresh app恢复，原应用保留。页面双击只产生一次动作；所有实际服务资产hash、原HTTP bytes、票据/回执独立hash、全表增量、Worker claim/clock及输入前后映射留证。页面控制的延后投递不冒充真实网络并发；真实SQLite双连接并发由后端两节点单独证明。

两个独立pytest进程各用正常生成3次Mock及来源Worker1次Mock的fresh种子，正常关闭SQLite后逐字复制到各case，不改lease/clock/deadline，不复用旧seed。预期共8个Mock请求、2次来源Worker；以原件实际计数为准。页面/后端case中不调用Worker或真实模型。执行前完整源码/测试冻结，最后独立源码与原件只读复核；原错误和中断不得覆盖或改签。

本轮不重复旧恢复故障矩阵、不做P-B后续版本/下载、不重试永久取消的旧安装digest并发窗口。Windows/native、PG、真实模型/语义/场景、远端CI与部署均未执行；旧exit139因果/产品关联Unknown及旧满盘独审未落盘缺证保留。实际结果和精确提交将在[本阶段原件](../evidence/pb-extraction-close-20261018/README.md)另附，不预写通过。

首轮冻结 `f0652b42c8c90c3363c8a2dd70b29d45f04b259b` 的后端5PASS/2FAIL/176.66秒，两条实际页面2PASS/236.50秒。POST先行的真实重叠中，关闭连接的SQLite默认5秒锁等待先到期，未完成BEGIN；原提取正常受理，未伪造关闭。另一个失败是测试把真实403 GRANT_REVOKED硬写为PERMISSION_DENIED。原日志、JUnit、HTTP及重叠原件保留。仅新关闭端点复用 `store.tx(wait_seconds=30)` 等待既有受理事务，finally恢复连接原PRAGMA；不改Store、原extract、业务lease/clock/deadline或PG策略。撤权断言精确改为真实错误码。修后重新冻结并复跑同9个聚焦节点；不把首轮7个PASS/2个FAIL改签为全绿。当前PrivateReadBarrier仅实际屏障resource/run等正文；完整账本正文必须在目标gate后读取由源码顺序独审证明，未声称动态journal-cell屏障。

第二轮 `ce407aaea9449cda7969d2457f1a60a11d4155d9` 后端6PASS/1FAIL/209.97秒，UI仍2PASS/246.09秒。close先行时普通POST保留默认5秒锁等待，在实际重叠中先500，close正常200且无重复受理。现将普通HTTP `extract` wrapper也改为相同有界30秒等待；共享 `_extract`、trial controller、Store、全部授权/版本/最终来源重验及PG策略不变。两轮输入各685项0漂移，原失败不覆盖。第三轮重新冻结同9个聚焦节点，预计六个独立正常来源seed合计24次Mock/6次来源Worker，以最终原件实际计数为准；不保证任意重负载永不超过30秒，超时仍不能清票据。

最终源码 `f7a48c062dfbcd3b9b515d893bb696eb65d69d9a` 同9唯一节点已全部通过；每轮685输入0漂移。六fresh种子共24Mock/6来源Worker、页面Worker0、真实模型0；最终页面118检查/226实际HTTP。三轮原失败及非作者源码/原件复核、正常dev推送和范围见[交付证据](../evidence/pb-extraction-close-20261018/README.md)。Win/native/PG/真实/CI门仍未执行。
