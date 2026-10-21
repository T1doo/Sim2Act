# Accounted 源码候选：已独审，尚未安装运行替代

基线 `df957ac17bef8e5e186980ea355f506f352b4a54`。本片实际实现 [私有发行器、固定访问器及四类纯叶子](../../../src/sim2act/cold_accounted.py)，并加入 [不可变值及领域比较](../../../src/sim2act/_cold_accounted_values.py)。独审结论 [ACK_UNINSTALLED_COMPONENT_ONLY / NOT_READY_RUNTIME_INSTALLATION](REVIEW/REVIEW.md)，不是仅提交文档，也不是允许运行接入、删除检查或新开窗口。

当前没有既有 runtime import 或调用 owned 组件；没有 feature 默认开启、旧模式 fallback 或 guard/pin 豁免。已有运行路径唯一改动，是将 `_graph_pb_archive_chain` 的原纯比较体原样抽成 `_archive_chain_from_facts`。独审 [AST 原件](REVIEW/STATIC-EXTRACTION.json)确认五条纯体相同、四个参数及 `_guard` 原样转发；将 helper 内联回新 wrapper 后，整个 wrapper AST 与原函数完全相同，保留原前后 guard、typed cohort、谓词顺序和 BaseException 失效处理。不声称相同私有调用栈层数或 traceback 行号。

发行顺序是原 `_graph_stage_accounted` 完整验证返回 → 完整业务值和 hidden storage 复制 → 新业务值逐值等于 producer 已 pin 的完整 raw → 原 full guard 和当前 scope 再查 → 注册私有 handle并完成全部 3/2 aid 关联校验后返回。调用者不能用 Packet、摘要或“已验证”布尔自证资格。registry 持有实际 handle 身份，读取绑定 graph、连接、事务、scope generation/nonce、source token、epoch、driver/实际事务、写入计数、thread、binding、pre 和 schema；失效/写入/跨阶段/关闭后原 handle 与已取 record 均拒绝。失败发行清空该 scope 的 handles，不操作外部进程或数据库。

记录访问只暴露当前 Run/Attempt 全列，以及 Slot/Identity/Outcome/Capture/BodyArchive 的固定全字段；返回标量、字节或受控 owned 视图，不返回原 RowMapping、Pydantic、dict/list 或测试 oracle。**packet 内容递归不可变且没有 raw 内容引用；scope 控制器有意保留 graph 生命周期引用。** 不能说整个 view/issuer 可达对象图没有原 graph。后续消费者闭合必须禁止绕过访问器回读 `scope._graph` 的 raw，当前尚未完成该迁移。

领域比较明确独立于 view/节点/packet 身份和 digest：完整类型、字段键集合及值比较，dict 插入顺序不影响领域相等，list/tuple、int/bool/float 区分；保留序列顺序和 multiplicity。单次 pair memo 避免沿共享 DAG 路径反复展开，不跨验证缓存。Node 与 record/view 的普通 `==` 不准用于业务关系；Node 的 `!=` 同样拒绝。四类叶子覆盖 stage usage、source row、source exchange 和完整 archive family/外部 ledger/receipt/private bytes 比较。

最终 [38 tests passed / 0.59s](RUN/PYTEST-FINAL.txt)，[Ruff](RUN/RUFF-FINAL.txt)检查新增两模块与新 test 通过，[mypy](RUN/MYPY-FINAL.txt)检查两模块通过（`--follow-imports=silent`，不是全工程检查）。[Tripwire 原件](RUN/TRIPWIRES.json)无触发。首轮 32、扩展 36 和修订后的 38 项测试原件均保留；本片没有 pytest 失败。首轮 Ruff 风格/未使用项及 13 个 mypy 类型标注/NamedTuple 问题已修正，失败检查原件也保留，不隐去。

测试实际使用已有第三窗口五组归档请求/响应字节、完整合成 native 行与真实固定模型类型。issuer 测试使用准确的连接/事务生命周期 double，实际执行原 `_source_reads_current` 状态判断及原 C codec pin；原完整 CGR check 和完整 producer **由离线 stub 替代**。因此证明的是组件绑定/复制/比较/叶子，不是原 producer、SQLite 集成、真实授权、G0 或完整 PB 的通过证据。旧 pure helper 直接执行，没有业务请求或新 Mock 交换。具体差分域与反例见 [CHECKS.md](CHECKS.md)。

当前仍有明确的安装条件：[生产规模边界](BOUNDS.md)尚未由所有 Run/Attempt JSON、固定模型和 hidden storage 的可达上界推导完；所有 occurrence/消费者要同时切换；新私有 manifest、pre/post/origin/software 协议隔离要闭合。候选 `_Bounds` 必须显式传入，无产品默认值；tests 中 20k/50k/128/4MiB/8MiB 不是运行资格。不能因此启用 owned 分支或从 mutable frontier 移除事实族。

原动态授权、撤权、完整集合查询、source-key/Operation、Run/fence/停止/期限、事务隔离、最终 guard、postwrite 和原持久签名保持现有路径。没有延租、拆事务、减少 pin/hash/签名/权限门、改 main、真实模型、费用/凭据/安全权限变更、DB 打开、G0/W5、旧实例恢复或第四个 Mock 窗口。未测量候选 G0 收益，未声称 30 秒过门。

复现命令见 [REPRODUCE.md](REPRODUCE.md)。[SOURCE-HASHES.json](SOURCE-HASHES.json)绑定源码/输入，[RESULT.json](RESULT.json)区分实际测试与未证明项，独审没有重新运行测试。最终交付 SHA、远端与工作区差异见最终回复。
