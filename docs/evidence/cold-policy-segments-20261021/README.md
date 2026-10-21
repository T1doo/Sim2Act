# Cold 固定 policy 纯段候选：代码及离线差分

基线提交：`a3ba16cf034f05ed1ba4602518b045bb359ca0c8`。本轮新增实际运行代码，
没有新 G0/Mock 窗口、Worker/model 构造或真实模型调用。原 G0 仍 UNKNOWN。

## 改动及边界

`_ColdTrialGraph` 四个位置改用两个固定私有入口：prepare/recheck 的 requirements，
首次 commit/recheck 的 RunCheck 构造。不是通用 runner、重入标志、skip_guard 或 PASS
缓存；独立公开 policy helper 和其 guard 行为不改。这四个 Cold coordinator 调用
在 native 和旧默认模式都会经过新入口，不限于已发行 native。

每次调用：完整 parent/typed pin → 当前输入的私有完整存储副本 → 原固定 policy
函数且 `_guard=None` → 完整 parent/typed pin → 发布成功结果。原核心只执行一次；
核心异常原样传播，不用 finally pin 覆盖，不重放或降级。runtime 包装将 scope
失效、phase 置 INVALID；native 的原失效逻辑关闭 mode。

副本逐字段保留 exact model/native 类型、全部 stored fields、独立 field-set、None、
list/tuple、bytes 以及 completed DAG 共享；活动 cycle 不合格。不调用 deepcopy、
model_construct、默认工厂、validator 或实例拷贝/序列化钩子来构建副本。副本是
仅供两个已审固定纯函数使用的私有可变值，不是递归不可变 packet 或发行权限。
RowMapping 的 policy 可见投影被复制；`guard.inputs` 中既有 RowMapping 的隐藏存储
仍由原 full pin 覆盖。复制这两个 policy 参数的可见投影不新增隐藏存储证明，尤其
不把 recheck 新 SELECT 返回、未直接加入 guard.inputs 的行冒称已编码隐藏域。

代码配置见证在 runtime 模块可信正常初始化时 eager 建立，逐次重读完整 live schema
形状/回调身份、原 compiled validator/serializer 对象、model_validate/init/post-init
及标准 dump 资格。schema 原位变化、重建或同 schema 重编译均不能借 C 类型资格
进入新路径。这是固定代码配置见证，不是输入校验缓存；不声称防任意启动前进程改码。
未知表示/钩子在核心执行前选旧完整路径；旧路保留内部 pins 并增加入口 pin，不声称
不合格输入的 helper 次数或错误时刻逐项相同。没有新增业务接受上限。

SQL/完整读集、授权和撤权、来源解析、业务时钟、Run/fence/lease/stop、连接/事务/
scope/epoch/settings、根增加和 `_graph_trial_produced` 都留在原位置。没有拆事务，
不延 lease/Run/TTL，原期限值及最终时钟不变。两端 pin 仍逐次完整编码 frontier，
包括可变 raw/model；没有因同事务便假定它们不变。

`_fields` 保留原路径：其递归 facts/dump 与源容器的别名、隐藏 RowMapping 和 owned
family 的作用域叶子尚未形成可发布快照闭包。`_base/check/_typed_parameters` 的
原 full pin、typed 内容检查及动态谓词不删；这次通过合并固定纯 policy 段里的多次
parent 调用减少完整编码，不声称完成七族 owned 迁移或整个纯尾段闭包。

## 实际验证

最终测试冻结文件 SHA256：

| 文件 | SHA256 |
| --- | --- |
| `_cold_policy_segment.py` | `9d328fd597fbcbc64e80bdfaaef01f829084afbae95861ad92c2daf05301e802` |
| `natural_spec_runtime.py` | `6f91a55bdfbb37fc1b9f571d030692087b664c078dcd9b043844c1e8b379dcc4` |
| `test_cold_policy_segment.py` | `ad2d6f2f14e7704c5ff46481aa57cd14b9a8fd0f7aa6a64a20e5da528a37f76c` |

测试退出后按证据独审收窄两行 RowMapping docstring（即上述隐藏域范围），helper
最终文件 SHA256 为 `ad7ee006d6596d41b3ed5511119609ac773a8eb75ccedf242ca74b0e9fb44751`。
与测试时版本去 docstring 后 executable AST 完全相同，原文及比较记录已归档；其余两文件
无变化。没有因此重复产品测试，不把文档修订冒称此前测试的字节。

- 最终组合 `pytest -q` 九个相关文件：**163 passed / 80.80s**（新测试22项＋相关回归
  141项），在上表最终冻结源码/测试上执行，运行后摘要仍一致。
- 九文件为 `test_cold_policy_segment.py`、`test_cold_trial_pure_cohort.py`、`test_cold_owned_settlement_closure.py`、
  `test_cold_accounted_native.py`、`test_cold_admission_diagnostics.py`、
  `test_cold_tail_diagnostics.py`、`test_cold_trial_guard_delta.py`、
  `test_cold_fixed_key_dumps.py`、`test_cold_typed_stream.py`。
- 先前两组为 **20 passed / 21.31s** 和 **141 passed / 61.10s**；随后独审发现两个
  wrapper 异常分支应先检查 guard exact type，再清理，避免 foreign guard 覆盖原异常。
  修复并加两反例后执行上述163项最终组合；不把重复执行相加充当独立测试数量。
- Ruff 三个改动文件及 mypy 两个 source 文件通过。现有 Starlette/httpx 测试客户端
  弃用提示保留在原日志，没有为此修改产品代码或依赖。
- 首次开发批次 **12 passed / 2 failed**：两个反例直接给 frozen Settings 赋值，先于
  被测门抛 FrozenInstanceError。改为显式 `object.__setattr__` 注入反例；原失败日志和
  当时 freeze 保留，不算作通过。无运行测试期间修改源码。

真实隔离 SQLite / native CGR / `_ColdTrialGraph._base/check` 下，相同输入依次执行
旧、新纯段，并正常关闭原 read scope；注册 SQL 观察器确认段内0次 SQL。观测到：

| 固定段（每次独立调用） | 旧 codec | 新 codec |
| --- | ---: | ---: |
| prepare-facing requirements | 12 | 4 |
| second-commit-facing requirements | 12 | 4 |
| first-commit-facing RunCheck | 14 | 4 |
| second-commit-facing RunCheck | 14 | 4 |

这四次合计52→16（减少69.23%），**仅这四个离线段的编码次数**。所有返回字段、
业务指纹、原 at、deadline 与旧函数相同。新副本及 schema 见证有实际分配/CPU成本，
没有整体 CPU/内存收益或 G0 提速测量，不能据此外推节省2.16秒或成功余程足够。

反例覆盖：跨调用原 model/raw 突变、settings/stop、授权撤销写入、scope 关闭、入口
后出口前突变、原 lease 过期拒绝、原核心异常对象与无重放、未知 serializer/validator/
function、schema 原位/重建/重编译、foreign metaclass 无 equality/hash 回调、DAG
共享及副本无外部可变别名。

## 尚未证明的完整尾段

这不是完整 prepare→首 commit→receipt→第二 commit→正常退出成功证明。当前真实
SQLite/native 离线夹具的 coordinator 明确 `trial/platform/audit_seed=None`，只验证
两个纯段及真实 base/check/read-scope；不能给它改名冒充完整 binding。已有
`synthetic_commit` 采用五阶段/SQL stand-in，也不充当这种证明。

完整 configured 合成路径仍是既有 G0 launcher 路径，需要其完整 binding、当前 source
和 Mock 前缀；本轮明确不执行新 G0/Mock，未把真实生产 SOURCE_MISSING 当成已授权合成
测试的拒绝理由，也没有为凑成功新增来源/账户替身。全链成功差分这一验收条件仍未满足，
不能把限定代码 ACK 当作通过。正常 read-scope 成功退出也不等于原两次 commit 的 scope
正常完成。原件及阶段审查回执见 `artifact-manifest.json` / `reviews/`，不归档夹具数据库。

官方 [Pydantic 模型文档](https://pydantic.dev/docs/validation/dev/concepts/models/)
说明拷贝/无验证构造不是重新校验；本实现的正确性来自完整前后 pins、明确私有复制和
固定纯核资格，而不是 `frozen=True`、`model_copy` 或 `model_construct` 名称。
