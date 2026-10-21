# 必要离线反例与证明范围

| 实质性质 | 实际测试/静态证据 | 边界 |
| --- | --- | --- |
| 发行 provenance | 原 producer 调用、复制、逐值 raw 绑定、full guard 后才返回 handle；第 3 Capture 在 copy 前意外变化拒绝；producer BaseException 后旧 handle 失效 | issuer wiring 的 producer/full-CGR-check 是纯离线 stub，未证明实际 SQLite/原 producer 集成 |
| 生命周期 | 同 graph/事务/scope generation/token/epoch/写计数/实际事务/pre/binding/thread/schema，关闭后已取 record 也拒绝 | fake 连接/driver 状态，实际 source-token 判断代码执行；不是实际 DB commit/rollback 试验 |
| handle 与固定 wrapper | forged、cross-scope/role、post、wrong packet、foreign family/node/schema/role/handle/ref，以及节点普通 ==/!= 拒绝；未知属性/eq/hash/serializer 回调零执行 | 不主张防任意进程内代码替换整个 gate；控制器有 graph 生命周期引用 |
| 全记录领域比较 | 不同 packet/node、共享/复制 DAG、键插入顺序；所有字段/嵌套值、精确数值及 list/tuple；checked↔actual 完整比较 | 不用 identity、digest 或普通 view equality 替代领域值；pair memo 只限本次比较 |
| 所有 aid | Generate 3、Source 2，duplicate/swap aid、wrong run、第 3 checked 改动、NS aid 不一致均拒绝 | 没有“只看当前 aid”；原 producer 所有 SQL/授权证明仍是前提 |
| stage usage | 与原 normalize_usage 对照；known/partial/unknown/None、bool/float token、总数不一致，保留未知 | 原请求级使用量/结算及累计预算没有减少；None row usage/response 受控拒绝而不是 AttributeError |
| source row/exchange | 两个明确 provenance mode，原 wire/payload bytes、UTF8 字符数与字节数不同、raw 与 canonical 不同、完整 canonical 输出和旧业务指纹相同 | 原 source helper 的 slot 来自外部 ledger，新叶子取 family.slot；差分以它们是同一已验证 slot 为前提，未来 wrapper 仍须保留外部 ledger 关系 |
| archive family | 与原纯 helper 差分；外部 ledger 的完整 Slot、halted、七个 receipt 字段、私有 request/response 下标/顺序，不只公共 SHA | 新叶子复制仍受原保护的 ledger/Resolved 输入，不签发其权限；原 scope/keys/Operation/最新授权不在这纯函数内证明 |
| 持久兼容 | owned fixed Identity 的 Capture request fingerprint、完整 BodyArchive fingerprint、原 canonical 结果相同 | 私有 packet 协议没有接入旧 post_graph/origin/StageAuthority/receipt 签名 |
| 引用与规模 | 原源 buffer 变化不改 packet，下一 scope 重新捕获；完整 hidden row 字段/转义 surrogate 保留；显式各限额拒绝 | 仅 packet 内容递归 immutable。没有从生产接受域推导 aggregate bound；不以测试数字安装 |

一个有意明确的非法域差异：旧 Python 数值相等可能接受 receipt 中与 int 同值的 float，新 scalar/domain 比较拒绝。本片测试保留该差异，不声称对任意损坏 Python 对象都逐行为/异常次序等价。合法 producer 的该字段来自实际 int 字节长度；不能把其宽松比较当业务合同，也不能因此删除实质拒绝用例。

旧 archive helper 提取通过父侧与独审两个 AST 证明：内联后整个旧 wrapper AST 相同，包括 guard 次数/顺序、typed pins、所有原谓词及异常失效。没有运行完整旧业务 fixture 或依赖新的 Mock 窗口来确认它。

本片实际检查：最终 38 项纯测试通过；此前 32、36、38 项原件保留，均无 pytest 失败；Ruff 和两文件 mypy 最终通过，初始失败检查保留。tripwire 在纯模块 import 之后的 setup/body/teardown 生效，Store/Worker/InternModel、DB connect、Mock/HTTP transport、socket connect/getaddrinfo、subprocess 无触发；不冒充 import-time 系统沙箱或原生 hard quota。
