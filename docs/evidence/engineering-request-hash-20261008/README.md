# 请求内相邻 snapshot 指纹去重 — 2026-10-08

本轮基于 `48accbbea0fd90fc022abd049a92b2d6c16eeb52`，继续新实例的
`dev/pg-phase-diagnostics-20261008`。只改 `protocol_jobs.verified_pending` 两行：
在原 seal 字典求值处保存 `snapshot_fp`，紧随其后的 job/Run 指纹比较复用它。
它是这一函数调用的局部字符串，不复用任何授权、来源、查询或跨调用验证结果。
原实例、未提交 Engineering 计划和阻塞日志没有接触或复制。

## 调用链、成本与边界

保存的[前轮热点 profile](../engineering-pg-hotspots-20261008/README.md)显示：
普通图 GET 每请求两次 `load_family`，正常历史 GET 每请求七次，其中 REPORT load 五次；
报告 preview 两次 load 分处 enqueue 前后两个事务。
图链是 `current → load_family → state → build → load_family`。
第一加载在读取保护账本前授权，第二加载在账本读取后重验来源、授权和当前图状态。
不能删掉其中一次：项目锁不冻结授权到期时间，resource SELECT 没有行锁，PG 使用普通
READ COMMITTED 事务，同事务内也可能改变来源或封印。原23项
`test_report_validated_origin.py` 明确要求 origin 校验后 source/extraction/seal/grant/target
变更仍拒绝；这些是该边界的相关证据，不冒充针对图 state 边界的新并发试验。
[独立边界审查](independent-boundary-review.json)保存具体代码位置和限制。

可证明的冗余位于更窄的步骤：`verified_pending` 已取出的同一 snapshot，先与独立
PROTOCOL_ACCEPTED seal 比较，再与 job/Run 指纹比较。两次 `fingerprint(snapshot)`
之间没有 SQL、回调、await 或修改。`db.fingerprint` 只是严格 JSON 序列化与 SHA256。
原计算位置用局部赋值表达式，保持 seal 数量不为1时零次 hash、`job["kind"]` 先求值、
错误 seal 先拒绝的顺序。后续 namespace、contract、权限、result、completion 和
dependency 校验，`stop_only` 行为与全部查询/锁/事务边界保留。第二次函数调用仍重新计算。

## 可复算的同输入阶段对照

旧版原报告清单 DOM 的被动观察捕获7个自有测试 snapshot，按原字节保存并压缩。
同一 `db.fingerprint`、相同7个输入，旧步骤计算两次，新步骤计算一次并返回两处使用值；
各输入输出逐项相等。每输入9对、每变体每对300次，交替先后顺序，保留全部原始纳秒值。
输入文件 SHA、snapshot 指纹、中位数均可重算。
[输入](baseline/snapshot-hashes.json.gz)、[阶段样本](baseline/hash-stage-benchmark.json)、
[基准脚本](benchmark.py)、[核验](verification.json)。

7个样本的相邻双 hash 阶段中位数减少 **47.292%–50.858%**，每调用节省约
31.466–114.787微秒。旧DOM2254次有效 seal 校验执行4508次 hash；其中第二次累计
**143.371毫秒**。新DOM2246次有效校验执行2246次 hash。总有效校验差8来自后台
conditional-apps列表23→22次，每列表8次校验，不能把轮询数量差认领为产品优化。
固定的27次 app history 请求，两版均756次有效 seal 校验，hash **1512→756**。
这些数字证明消除重复纯计算；143毫秒仅约为旧call38.089秒的0.38%，不是容量瓶颈闭合。

|原节点阶段|旧版|两行修改版|
|---|---:|---:|
|setup 秒|0.321|0.347|
|call 秒|38.089|39.079|
|teardown 秒|0.014|0.015|
|pytest进程墙钟秒|39.490|40.551|
|snapshot hash 次数/累计秒|4508 / 0.349|2246 / 0.203|
|固定27次history的hash次数|1512|756|

两个原始 DOM 均1PASS，49项检查、7条MOCK wire、域外请求0、LIVE0全部保留。
相同测试/驱动和逻辑输入，但新建夹具生成的ID、端口以及后台轮询时序不同。
精确同输入对照限于上述纯 hash 阶段；DOM表是独立旧新样本，不能证明端到端收益。
实际上新样本call和墙钟增加，不能将纯阶段百分比推广到整体请求或Windows。
观察器记录、函数跨度和SQL跨度互相重叠；观察器总开销未单独测量。

## 必要回归与独审

未再运行全量或已闭合的死锁验收。只执行共享校验函数关联的191项原PG测试：
protocol_jobs40、protocol_reviews43、conditional_run_bindings48、report_validated_origin23、
report_manifest_apps23、protocol_recovery14。**191PASS / 0FAIL / 0SKIP**，pytest报告
172.39秒、进程173.887秒；setup34.415/call134.794/teardown2.650秒。
原测试/驱动/页面/脚本/工作流/锁全部字节保留。284项源清单前后一致，旧版全匹配48accbb，
候选和回归仅 protocol_jobs.py 不匹配，且精确只有两处替换。
原1591全量结果仍绑定d85f6f5/48accbb，不冒充本轮修改后的全量回执。

规定 Engineering 检查 `ruff check src scripts tests` 与 mypy47源码PASS；新诊断辅助代码
lint也PASS。一次误用 `ruff check .` 扫入既有历史证据，返回3635错误，记录在
[quality.json](quality.json)；没有修写历史证据或改变规定检查范围。
[最终独审](independent-fix-review.json)与本轮JUnit、源散列、精确输入阶段复算共同供复核。

三轮顺序运行在同一新实例，Python3.12.14、锁定依赖、Node24.19.0/jsdom30.1.2，
已缓存固定PG17.11镜像；每轮一次启动独立自有localhost PG。首次认证连接均成功，
没有重启或业务重试。四采集文件在三轮启动前已存在，散列固定，见[环境](environment.json)。
三轮 census 前后 schema/role/public表均0；验证owner标签后清理自有容器/卷，均确认不存在。
清理前Running=true、OOMKilled=false；attach137来自明确的rm-f-v清理。
SQL观察40P01=0、观测HTTP500=0；这是本轮可见范围，不作为新的全系统死锁结论。
三个目录导出28+27+24文件，原始log/XML空白保留，大文件仅gzip，原始及压缩SHA均核验。
只清理本轮自有临时夹具，保留全部导出证据和/tmp原始阶段日志。

只读复算：

```bash
.venv/bin/python docs/evidence/engineering-request-hash-20261008/verify.py
```

相同7个输入重测纯阶段（仅写指定/tmp文件，不启动数据库或测试）：

```bash
.venv/bin/python docs/evidence/engineering-request-hash-20261008/benchmark.py \
  docs/evidence/engineering-request-hash-20261008/baseline/snapshot-hashes.json.gz \
  /tmp/sim2act-hash-stage-repeat.json
```

## 原生容量的下一最小实测条件

本改动有确定的局部CPU收益，但不足以高置信预测Windows900是否可完成。下一步需要
原生阶段证据，当前只保存方案，不启动新CI、不伪造平台变量、不修改任何预算。

最小成本探针应在另获明确一次执行授权后，使用真实可用Windows环境：记录OS/build、
CPU/RAM、Python3.12x64、锁定依赖、Node与nativePG版本、实际源码SHA、缓存状态、
原生本地测试数据库及隔离schema清理。选现有报告清单DOM与REPORT图DOM两个原节点，
保留全部断言，顺序跑并记录setup/call/teardown、原始JUnit、初始化次数、请求/SQL与
snapshot hash阶段；可使用现有被动Python/Node采集器，但不得把Linux/jsdom代替Edge结果。
另在相同输入上运行本纯阶段基准，以区分本次CPU小收益和原生请求主成本。

若选择既有GitHub原生harness，只能是真实获授权的windows-2025 job；它硬性需要真实
GITHUB_ACTIONS/RUNNER_TEMP、PGBIN、Python launcher3.12.10x64、可首次创建的venv、
正常已安装且Microsoft有效签名的Edge及官方锁定playwright-core。不得设置假平台变量，
不得通过禁用sandbox、换browser、加管理员权限、安装fallback来通过条件。
预算仍为整个job900秒、Edge步骤240秒、Node子进程150秒，准备/全量工程/浏览器/报告/
清理都计入总预算；本小探针通过不能替代这完整资格。当前固定harness Test是全量，
不能把其删节点版称为Engineering验收；有界探针需要单独标为诊断，不能擅改现有workflow。
Win11首次安装/普通用户使用还需要实际干净Win11，Windows Server资格不能代替。

Linux原1591全量墙钟1089.253秒且有观察器，不能推断Windows根因或节省189秒。
**Windows900/Edge240/Node150与NO_GO保持**。LIVE0/MOCK，无真实模型、部署、安全设置变化。
普通开发分支推送保留 `[skip ci]`，不main、不force、不派发新CI。
