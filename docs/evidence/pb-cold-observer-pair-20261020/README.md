# 唯一原观察器两臂比较：没有实质扰动信号，候选否定

父侧单独授权本次只读有限因果候选。未改任何产品/测试文件；没有完整 PB、Worker 执行、模型、审批、写入口或 PG/CI。先核封存输入与方案，再取得精确脚本独审 ACK，之后只执行一次 parent invocation、两独立子进程各一次 dormant `_cold_first_binding`。每臂45秒上限，正常exit0，无超时、重试或补跑。

原完整失败 `f9dfcf319b1a5bd66246aaa07a4dd0a082d1bd98` 的37.279秒首绑定，与后来的 `78ed5bef2da3a175d819eb9a2f58b3bbf097f75b` 下5.909秒 dormant 观察存在输入、执行范围、环境等差异，原先不能直接比较。本轮没有相减这两个旧数字，而是固定同一原 f9dfcf 源码、同一封存闭库、同一内存 pin、同一 producer 范围，唯一实验变量为原深层观察器的有/无。

## 实际结果

| 相同 producer body 范围 | 原完整深层观察器 | 仅外层计时及共同安全断言 |
| --- | ---: | ---: |
| wall 秒 | 3.866211830 | 3.797118195 |
| thread CPU 秒 | 3.865326304 | 3.796848015 |
| producer / exit | 1 / 0 | 1 / 0 |
| check / input_key / add | 2028 / 2158 / 130 | 2028 / 2158 / 130 |
| producer SELECT | 2814 | 2814 |
| DB native total_changes / blocked | 0 / 0 | 0 / 0 |

去掉深层观察器后 wall 少0.069094秒（1.7871%），CPU少0.068478秒（1.7716%）。**这一个固定顺序样本没有实质扰动信号，否定本次有限观察器候选作为继续推进的依据，立即停止，不重复微优化或比较。** 不据此认定统计等价、总体无开销，也不以本次绝对秒数替代原完整 G0。

深层臂确实完整安装并激活原观察器：56项安装/56项恢复，secondary errors=0；DORMANT区间实际记录 codec.bytes2170、cgr.input_bytes2158、cgr.input_key2158、cgr.check2028、validator132、SHA构造3169、first_binding1，SELECT2814；公开祖先 verifier实际调用0。没有用未激活 observer 冒充对照，没有新增 typed-storage tap。

## 同一性和安全证据

- 当前开发基线 `2b48d8255102aefe3b1fe452eee34d60065a5858` 的产品/测试不变。两臂执行从 Git 提取的原 `f9dfcf319b1a5bd66246aaa07a4dd0a082d1bd98` 静态源码，不是恢复旧服务实例；151份 source/schema/配置/依赖及资产文件前后均与该 Git 字节相同，见 `frozen-source.json`。没有函数覆盖或产品 patch。
- 源闭库及两副本前后均1142784字节，SHA256 `9a9bdfcf0264a251670a2c59dcbd401e1e035656542413e032357a442802e4db`。仅使用 firstproof archive 的唯一已关闭 `phase/baseline-first-only/prefix-copy.db`；没有恢复正在执行的 Cold 或撤销窗口。
- 原 helper SHA256 `1714d223e667948a1d84a54abfdb8e35f2670c6384fc162581105da775cf6d8a`，原观察器 SHA256 `2209e9a71be5341cdac68abf314c991a51262a7ee61c5079ee87d3f7fdcc6c67`；后者与原完整运行 receipt.observer_sha256 精确一致，原样 `CostObserver.install_current` 安装全部 hooks/aliases。
- 同一初始完整 input为6435字节，SHA256 `5ee997454dcdbacd9b4bc219ddc2029899effde7dd2e8018cdba41ab91e23efe`；末 input为579257字节，SHA256 `2527810ece429e53fdf144010ceec456e152f69b15f90dc0e0f3a9a34845f5fa`。两臂初/末各自逐字节相等，完整原 bytes 均无损gzip保存；**不反序列化这些 bytes**。
- 两臂完整有序 SQL/原生参数各956105字节、2831行，逐字节相同，SHA256 `dc54565dcf8dee3a55f0662abb64b07cf01c70daf98a3dece119db52485e1189`。setup15 SELECT/1 BEGIN、scope_setup1 BEGIN、producer2814 SELECT；SQL门仅允许 SELECT 和原 BEGIN IMMEDIATE，DML0。
- 相同轻计数、只执行一次门、Worker构造/循环/claim、模型、审批/准入、journal、HTTP/Mock和公开祖先 tripwires，包括已知预绑定 aliases，先于观察器安装。原可变全扫描、权限读取、schema/pin和实际时钟保留；未改lease/TTL/Run/deadline或授权。
- helper仅建立未初始化Worker壳与未批准synthetic read-pin。为两臂相同，只临时替换helper自己的time模块绑定生成同一内存expiry，随后恢复；没有改全局/产品time.time、数据库时间或实际许可。此pin不算审批、真实准入或业务执行。
- 直接 dormant producer不经过原 `_cold_model_before`，故不伪造G0阶段：观察器明确标 `DORMANT_FIRST_BINDING`。timer停止后才停观察器、输出/哈希/IO。tracemalloc、trace、profile未开启。Python3.12.14，同解释器和依赖；固定先deep后outer、每臂独立进程，不能推断统计性能、完全冷缓存等价或原37.279秒的因果分解。

## 原件与资格边界

实际唯一命令：`.venv/bin/python /tmp/sim2act-observer-pair-20261020/observer_pair.py`。脚本SHA256 `76a11c066ac485ca65022f18ad0c6fcf5a01ad40de98101b49e17808f720dcbc`，与启动前独审ACK相同。parent receipt在首个child前持久化；已存在receipt禁止重复，首个失败会停止依赖第二臂。本目录保留实际脚本/原观察器/helper/全部输入与有序SQL原件、每臂result与stdout/stderr、原pin及独审报告；只供核查，不授权再次执行。

`MANIFEST.json` 给出原始及压缩文件的bytes/SHA256，`provenance.json`标出来源archive。未新跑pytest、模型、PG或完整链；仅脚本语法编译和这一次pair是本轮实际执行。独审静态设计、精确脚本及最终原件复核分列，其未执行producer/数据库，不能代称独立重跑。

原完整 PB 仍 **FAIL_NOT_ACCEPTED**；原G0超30秒lease，W5/G1/finalguard仍 **NOT_REACHED**。本次没有支持新的产品性能修复或完整PB重跑理由，不移除验收观察器。旧软件、Windows/native、PG、真实模型/语义、完整Stage/F2/R0和正式发布边界均保持。无main/强推/部署/新费用/凭据/权限或旧实例恢复。
