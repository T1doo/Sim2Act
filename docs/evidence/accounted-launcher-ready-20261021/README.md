# 首 G0 显式合成候选：launcher 冻结与待批条件

基线 `09b58a414a6db0665de759ff77dfb51bb2b735b7`。唯一源码写入者接续原开发分支；
两名既有 reviewer 仅静态读取代码与作者日志。本片完成配置／结果记录／保护核验，
**没有创建执行 grant，没有运行 prefix、完整 `_prepare`、真实两次 trial commit、
G0、第四 Mock 窗口、Cold2、W5 或真实模型**，不新增费用、凭据、权限或发布。
默认路径仍关闭候选；显式 `--candidate` 也不是执行授权。

## 冻结配置与选择

`g0_bounded --describe --candidate` 只读描述要求干净的指定开发分支、Linux
CPython 3.12、原保护能力，绑定实际 HEAD、全部 src/tests/diagnostics、依赖、
解释器及 SQLite 二进制摘要。描述、profile 与保护合同必须逐字段精确匹配新 grant；
canonical JSON 区分 bool/int，拒绝 nonfinite。child 在安装原 I/O 保护后才构造
exact `_NativeConfig`。未选择默认配置仍为 None，不新增账户替换或生产资格。

| 每 packet 的 Bounds | 冻结值 |
| --- | ---: |
| nodes | 60000 |
| edges | 120000 |
| depth | 128 |
| leaf_bytes | 8388608 |
| encoded_bytes | 67108864 |

| 同 scope Limits | 冻结值 |
| --- | ---: |
| resident | 536870912 |
| peak | 1073741824 |
| work | 5248228845274896823178226498375696 |
| integer_bits | 16000 |

`_Arena.classify` 使用两族 aggregate，因此 N=120000、E=240000、B=134217728，
`C = 8*(N+E+B+1)^4 = 2624114422637448411589113249187848`；本次 work=2*C。
额外 C 只是有限附加 fuel，不声称证明所有其他收费都能通过。没有使用旧 10^10
或任抄 10^40。resident/peak/work 是新增优化工作的逻辑账本，**不是 CPU、RSS
或物理内存上界**。没有证明完整输入落入此子域；例如 resident 不覆盖每种最坏
arena，合规输入可能在发行前选择 LEGACY，不能把这一结果当优化资格。

`profile.json` 是无产品导入的实际 profile/保护描述；`final-hashes.json` 绑定七文件。
最终干净提交之后只读描述的完整 HEAD／source-manifest 摘要在交付回执给出，避免
文档／提交 SHA 自引用。只读描述文件不含 grant_id/expires_at，也不可代作 grant。

## 结果记录与不完整证据

只为显式目标记录 OWNED/LEGACY/ERROR、选路原因、预算阶段及逻辑账本快照；
scope 关闭后记录 active/live/resident。记录不新增校验、读取 SQL 或重放 producer。
commit wrapper 仍调用原实现，只复制两次成功原 authority record 的期限；最终
deadline marker 仅在**原 context 完整退出**（原最终 hash、stop/clock 通过）后设置。
不是额外时钟检查，不延期、不授予写入能力。

父侧只接受完整两次原返回、完整 scope 返回、有限正期限及关闭快照的匹配证据。
OWNED=`G0_COMPLETED_NO_W5`；LEGACY=`G0_COMPLETED_LEGACY_NO_W5` 单独标记，
不认候选资格。缺失／观测异常／原拒绝均不能冒充成功。普通观测 Exception 被
隔离为 incomplete/UNKNOWN，保持原选路、返回、异常与清理；初审 P2 原件保留。
Boundary/BaseException 仍保留原工程中止语义，不伪装可恢复的观测故障。

## 保护与四项 skip 的实际对应

四项旧 skip 是独立编译 native VFS 的 local SQL、size/sticky cap、symlink，以及
先安装该 VFS 的 child-I/O 测试；当前解释器不具该可选依赖，本片未构建或换库。
监测版 launcher 不调用该 VFS。新增必需测试在**同一实际解释器的隔离子进程**
安装原 `install_child_io`，实测 guarded sqlite3/_sqlite3、URI、文件写入、
凭据读取、DNS/socket、subprocess、ATTACH 拒绝，以及 arm 后缓存 SQL／base
Connection 写入拒绝、SELECT/rollback/close 允许；预存 raw DBAPI alias 令其
子进程直接中止，不能继续半初始化 handle。均不导入产品。

原网络拒绝、独占进程组身份检查／清理、leader 先退出后的同组核验、未知／稀疏／
已 unlink 可写文件采样单测通过。必需 audit/authorizer/killpg/proc 能力缺失使
describe 拒绝，实际 child 保护安装失败在 prefix 前停止。运行时仍须报告真实
安装／采样／清理结果，静态 capability 或局部测试不能替代该证据。
64MiB 是父循环及收尾**监测预算**，selector 等待上限0.05秒；配置0.1秒不是
采样调度保证，不是 native hard quota。采样策略和预算未改。

## 实际测试与证据范围

| 批次 | 实际结果 | 版本范围 |
| --- | --- | --- |
| first | 127 passed / 94.01s | P2修正前，不能冒称最终版本 |
| closure | **131 passed / 95.99s** | final 七文件中仅新增测试随后有 import 排序变化；含4项观测故障反例 |
| final import | **11 passed / 7.00s** | 排序后新增测试文件的全部用例；其余六SHA未变 |
| closure guards | **29 passed + 4 optional VFS skipped** | 33项总计；必需 monitored-I/O/网络/清理通过 |
| static | Ruff七文件通过，mypy两源文件通过 | 原 Ruff import排序失败日志及修后通过均保留 |

重叠批次不相加计数。pytest保留既有 Starlette 弃用 warning。局部 SQLite 仅用
已存五 upstream 归档与真实原选择组件；测试哨兵禁止 Worker/模型/transport，
没有调用 configured、没有真实账户／账户门阳性或完整 prepare；保留原 resolver
拒绝反例。两commit记录测试用明确
stand-in，仅证明记录合同与故障隔离，**不证明实际两commit／G0／提速通过**。
原 runtime、dispatch、账户门、settings、guard、五阶段观测器与 configured 七文件
逐字节等于基线，见 `unchanged-protections.json`；本片不删除 pin/扫描/事务或期限。

原始 logs/JUnit、三次哈希清单、profile和独审原件在同目录。独审只静态核作者
实测范围，最终 closure 报告绑定 final 七SHA；设计 ACK／准备 ACK 不授权运行。monitor-closure-final 是 reviewer 最后补入11项
实际重跑及两处文档精度修正的终稿，较早归档的 closure 原件仍保留。

## 可供一次批准的具体窗口条件（尚未批准／尚未执行）

只批准最终回执完整 SHA、source-manifest/profile 摘要与本表匹配的单次窗口：

| 项目 | 不可扩大的条件 |
| --- | --- |
| 身份 | 新 grant_id／有效期，独立全新父目录及 SQLite；不续旧库／已消费grant，不自动重试 |
| 路径 | 原 configured 三项明显合成替换；显式 candidate；只首G0，两原commit后退出；禁Cold2/W5 |
| 计数 | 至多6 Mock交换（Generate3+Source2+Cold首1）、8入口（含Source2同步delegate） |
| 时间 | prefix480秒、G0120秒、总work600秒；TERM5+KILL5，共10秒清理 |
| 原更严门 | lease30秒、每Run300秒、TTL1800秒、原60秒reservation节流及全部授权/fence/stop不变 |
| 资源 | 64MiB实际采样监测超限停止；上述固定逻辑Bounds/Limits；不宣称物理硬配额 |
| 外部 | 0真实模型、0费用、0新凭据／权限，不动外部进程，不改main／不发布 |
| 终态 | OWNED/LEGACY/UNKNOWN分别报告，含真实G0进入、时长、计数、两commit、最终期限和清理；失败不自动再开窗口 |

完整输入资格与原期限内首G0能否完成仍待这一新获准窗口才能得知。历史第三窗口
成本与局部小样不作成功预测。真实 account resolver 的来源实现缺口仍如
[原接线路线证据](../accounted-explicit-mock-wiring-20261021/README.md)所列，
本片不伪造账户事实、不接生产成功门，也不把首G0完成当完整PB交付。
