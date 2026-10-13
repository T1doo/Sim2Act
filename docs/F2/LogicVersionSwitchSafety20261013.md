# 有限内部版本切换：来源证据保护与既有业务实例采用

本切片承接原 F2-T07 有限列修改/确定性重验，补齐 F2-T08/AT-16 内部兼容版本采用中的具体来源依赖风险。已有业务实例可精确确认采用修改版逻辑；来源实例和 CHECK 证据实例不可切换，包括同 Release 的 no-op。旧 Release、业务结果、历史、Goal 和人工记录完整保留。没有正式发布、真实模型或任意 UNKNOWN PROJECT 修改。

合同文件：lifecycle.py 的 owned/immutable metadata pointer、logic_release_trace、logic_source_hints/pins、switch_preflight/policy、prepare/inspect/commit_switch；web/internal.js 的版本筛选、按钮及异步选择栅栏；tests/test_logic_switch_dependencies.py 的实际现有业务 Worker 与拒绝/回滚合同。

先按身份和项目授权元数据，再迭代追踪不可变来源指针，最多16个节点，当前或拟议循环及越界明确拒绝。这个元数据图并不替代完整来源/Worker证明；合成多层图测试也不意味着支持任意多层逻辑修改。CHECK/JOB/binding/immutable origin 是有限发现索引，主 seal 双缺失仍保留角色并拒绝不完整证明。Release审批和切换审批在正文读取前按真实身份/项目筛选，SQLite UDF 红绿独审证明没有私有 payload cell 泄露。

批准冻结当前/目标 Release、实例 revision/data version、完整来源与 pin 摘要。inspect、commit 写前与写后同事务重验权限、到期、精确批准、依赖摘要与历史/数据。指针 CAS 的后续失败回滚指针和 consumption。迟到撤权、批准改变或历史破坏不能留下部分切换。重复已消费批准维持原409协议且零写；页面不自动重发。普通业务实例不因目标是逻辑 Release 而一刀拒绝。

真实红例：I0→derived R1 原来可 commit200 后读取500；CHECK切换可 commit200 后旧 R1 proof409；双CHECK/APPROVAL索引删除可抹除角色；foreign Release/切换审批 payload 在授权前被SQLite UDF观察到。所有原失败/XML/DB/脚本与后续修复证据保留。business第一轮重用旧 intent key正确409，修正为新的业务intent后实际推进；不放宽幂等。mypy第一次8错中的新增3容器标注已修，最终仍有既有5基线错。

实际 Worker全部通过正常调度器、SQLite、冷Store/TestClient、原请求/token/lease/deadline预算。合成transport的两次模型wire用于验证实际修改recipe输入；没有真实/付费API。新成果从PENDING开始，独立合成review不能改变机器语义UNKNOWN，也不构成真实人工验收。

测试源冻结：73543253cdac76610a563209ad44efbac3e192ec；core a1afde85e991897a3ed8e736bc51605df70c1856；77 Python资格摘要 dc4c457189a88306d9bb61c41d0625bd25d976fdcb15b076f3455f9a2f721d0e。463个src/tests/pyproject文件在相关回归、完整业务Worker和完整页面路径前后逐字节相同。

| 最终实际验证 | 结果 |
| --- | --- |
| 有限依赖/事务与生命周期/资格回归 | 61 PASS、1 PG条件SKIP；41.52秒；该轮排除的完整业务用例另跑 |
| 既有业务实例采用修改版、实际冷Worker、新合成复审 | 1 PASS；434.39秒 |
| 实际HTTP/JSDOM既有实例、确认采用、新冷Worker、第三成果复审 | 1 PASS；261.09秒；38记录检查、57可见操作、20实际资产读取 |
| 独立精确role/审批隔离探针 | 5 PASS；4.91秒；不是把子观察计为pytest |
| 独立当前页面控制器 | 4唯一PASS、30内部观察；缺失/错身份revision策略和迟到prepare/detail/commit闭拒 |

作者最终唯一63 PASS/0 FAIL/1 SKIP；独审单列，不累加早期或重复节点。Ruff与JS syntax PASS；mypy78源文件仍只有既有status_report/tools的5个错误。页面控制器独审4唯一PASS、30内部观察，捕获采用真实API，独审控制器运行无Worker；与根任务完整HTTP/冷Worker路径分开。最终合计68个实际pytest PASS、4组独立Node控制器PASS、0终态FAIL、1SKIP（72个唯一验证节点），不把子观察、旧53e正向和早期重复节点累加。旧53e正向证据单独保留，其9222原成员重新核对零变化，归档6754ac8b287b570433077b75cfdec213e7e5602b5664db16f61a0b44a672a217，不合并旧PASS为本轮验收。

连接曾发生exec-server transport disconnected/pong_timeout，不是工具授权拒绝。父任务明确授权一次同环境只读pwd探测成功后，确认原Worker/pytest终结、单一写入者和Git/远端祖先，再执行新修正用例。未重启、换环境、提升权限、杀锁或重试已知拒绝browser/CI路径。

NOT RUN：PG应用角色/事务并发、Windows、native browser、真实模型/付费API、真实人工语义验收、真实旧用户源码/数据库升级、完整P-A/P-B/AT-13–15、任意PROJECT UNKNOWN依赖、source退休/任意链式recipe修改、远端CI、部署与正式发布。仅合成有限兼容version/data合同，本切片不宣称完整AT-16/总体验收。

独审封存报告见归档内 independent-final/FINAL_REVIEW.md 与 independent-ui-final/FINAL_REVIEW.md；审批旧红/绿与所有夹具、封存脚本失败原证另存各history目录。页面独审的app_id/source_app_id字段错误及一次封存字典属性错误均保留，实际4组Node终态全绿。

证据归档：[logic-switch-cycle-evidence-20261013.tar.gz](../evidence/logic-switch-cycle-20261013/logic-switch-cycle-evidence-20261013.tar.gz)。根SUMMARY/AUTHOR_FINAL/SOURCE_FINAL/MANIFEST及每轮原始XML、SQLite、完整source闭包、实际Worker wire、HTTP/资产hash、独审seal完整保留。最终报告/证据提交为测试源码的只含文档后继；源码字节与73543253完全相同。

归档SHA-256：`b0ee59d992cb06c8c887424d61c54a7399153a25d6546ff3f4bc26d0f3ea851a`；8998成员逐项大小/hash回读一致，压缩46749666字节。
