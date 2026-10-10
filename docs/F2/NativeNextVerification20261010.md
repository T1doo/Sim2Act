# 下一轮原生验证安排（尚未执行）

当前源码9002bf958f79972e576e831ebdf5e0d90fc44ea5，原生run38028553382按原15m预算取消。不是再次执行同样的默认顺序：先完成剩余11个确切目标的限定验证，再解决完整集合的容量。这里描述下一轮安排，不表示新的脚本参数已实现、已运行或验收通过。

实测工程pytest815.798s完成591/2234，589PASS/2SKIP/0FAIL；另1个活动、1642未启动。原26节点中的15已实际通过（14Node驱动和CSV哈希/回执用例），11仍需原生结果：[精确目标清单](../evidence/native-next-verification-20261010/remaining11.json)。这11个节点在已有SQLite/PG26日志中合计71.306/110.302s，最慢单例18.650/32.241s；Windows剩余11的成本仍UNKNOWN。原生已完成15节点的串行start→next-start区间合计73.889275s、最大9.444151s，这包含夹具/清理，不等于纯测试CPU时间，也不能保证剩余11的原生耗时。[测量及范围](../evidence/native-next-verification-20261010/measurements.json)

第一步拟增加显式、受原生CI限制的精确节点清单参数。当前WindowsCI.ps1只有Setup/Test/Report/Cleanup，Test.ps1只有Suite/CITracePath，并不支持现成的目标选择开关。最小实现为：WindowsCI的Test阶段可显式接收固定清单并传入Test.ps1；默认Engineering仍收集完整集合，禁止任意pytest附加参数、环境注入或隐式减选。目标模式必须标记DIAGNOSTIC_ONLY/非整体验收，核验清单恰为这11个完整nodeid、无重复或遗漏，实际收集集合与清单完全一致，结果逐项PASS/FAIL/SKIP/INTERRUPTED/NOT_RUN均输出。新接口及实际工作流入口先做独立复核，冻结新源码后一次普通推送触发原生运行；不手动重复盲跑当前完整模式。

这个目标运行沿用真正的Windows GitHub runner、原Setup/缺失venv分支、原生PG与运行角色、MOCK/LIVE0、锁定npm工具/实际owned-jsdom探针、完整Ruff和mypy、原工程断言和实际HTTP/DOM页面、总作业900s/Edge240s/Node150s、always Report/Cleanup。11个节点顺序执行，无xdist/共享数据库并发。必须11PASS/0SKIP且suite_complete=true才称“剩余11限定通过”；没有完成的节点继续未验收。若工程完成并有实际预算，按既有流程执行Edge并独立记录；Edge结果不从工程结果推导。局部通过不代替全套2234或Windows11验收。

第二步只收集同一冻结源码的完整原生集合，保存完整nodeid清单及hash，核对实际数量，按测试文件及夹具依赖建立分片。结合已有节点/phase耗时和下一轮11测量，优先将昂贵实际HTTP/DOM、升级/旧版本恢复、PG授权与普通API、纯逻辑/静态检查分开；每例必须恰属一个完整回归分片，未测尾部成本不得记0。某测试文件含共享module/session夹具或顺序依赖时整体保留；不重复同一昂贵组合来冒充覆盖。一次lint/mypy证据可关联同一SHA各分片，但各分片应独立保留原生平台、PG初始化/角色、节点结果、异常退出和清理证据。只有明证等价的重复准备成本才可消除；不共享可变DB/工作树，不复用旧角色或变更连接、安全配置。

分片必须在独立runner/checkout、独立JobRoot/PG端口/数据库/应用目录/结果目录中执行；初版max-parallel=1，每个工作树唯一写入者。汇总门核验冻结SHA一致、分片集合的交集为空且并集精确等于完整集合、所有必要PG/真实页面/旧版本升级例有实际结果、无意外skip/未执行、各套suite_complete、Edge实际完成且无失败。动态收集数变化或某片超过预算则BLOCKED，不自动删例、提高期限或增加并行。

最小必要决策是**900s约束究竟是整个串行端到端验收，还是允许每个隔离分片作业分别900s**。现有一次运行在591例及准备后已耗尽900s，尚无Edge成本，证明该次原顺序全套无法完成；剩余1642成本尚未知，不能凭线性外推声称确定总耗时或需要多少片。若900是端到端合同，多个串行900s作业会变相延长预算，不能据此验收；必须先证明足够的真实等价降本（含未知尾部和Edge余量），否则报告容量BLOCKED并请求最小合同决策。若允许分片作业900s，则可在明确批准的覆盖与隔离方案下测定片数/成本，并单列workflow总时长；仍不修改Edge240/Node150或冒充Win11通过。未得到这一合同决策前，不把分片设想当成既有验收支持或容量PASS。

Report GET idle6与PG resources-history Future10仍OPEN；HTTP200损坏响应/反馈入口限制保留，Windows900/Edge240/Node150 NOT_ACCEPTED。PROJECT PENDING/BLOCKED_PARTIAL，整体NOT_ACCEPTED，LIVE0，真实模型请求0。当前本轮仅证据收尾，无新CI、无上述接口/分片源码改动。
