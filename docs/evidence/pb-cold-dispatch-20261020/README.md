# Cold 完整检查的局部分派优化：未证明实质提速

从原开发分支 `f7e0d0b9922fedbb5730b4142d22d47a7c488171` 接续。本次修改两个产品文件，并新增两个边界回归；没有减少完整状态扫描、SQL、敏感回调后的 pin 或任何准入门。原完整 P-B 仍为 **FAIL_NOT_ACCEPTED**，W5/G1/finalguard 仍为 **NOT_REACHED**。不建议据此再次执行完整链。

## 安全边界与实际修改

调用链仍是 `check → input_key → input_bytes → 新建 Pickler → 全部当前输入`。`add` 仍执行既有完整 check、入参验证、插入和完整重 pin。没有身份/版本缓存、元数据 memo、Limits 快照、租约/TTL 修改、新权限、真实模型或新依赖版本。

- `_cold_graph_row_storage` 每行仍重读 `_parent`、全部 `_data`、`_keys` 和 `_key_to_index`，完整检查每个安全 index 的类型与范围；仅在条件失败时调用原 `require(False, 原消息)`，减少有效位置的纯 Python 分派。键类型、位置、coverage 的错误顺序不变；不碰外国 key 的 hash/equality。
- `_cold_graph_validate_inputs` 和 `_trial_typed_storage` 将固定类型集合的 identity-generator 改为同序 `is/or`，避免为每个标量分配生成器。动态模型白名单继续逐项身份检查。未使用可能触发陌生 metaclass equality/hash 的集合成员比较。
- SQL 返回、serializer/warning、deepcopy、权限/source 返回、seal、最终实际时钟、fresh permission、ALLOW 及原五写/拒绝事务路径均未改。

独立只读审查先认可上述子集，开发后核对实际差异。被拒绝的“同一次 dump 内复用行元数据”未实施：可变元数据无独占保证，而且 CPython 保存 reducer 的全局 marker 时会进入 import hook。新增回归实际在第一行与第二行之间改变共享隐藏 index，要求后行重新读取；另一个回归验证非法 hidden index 先于 coverage 失败且保留原异常对象。实现依据参阅 [CPython 3.12.14 官方源码](https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/_pickle.c) 和 [Python pickle 文档](https://docs.python.org/3.12/library/pickle.html)。

## 本次实际验证

| 验证 | 实际结果 |
| --- | --- |
| `pytest -q tests/test_cold_graph_fingerprint.py tests/test_cold_graph_row_storage.py tests/test_cold_trial_pure_cohort.py tests/test_cold_trial_guard_delta.py --basetemp=/tmp/sim2act-dispatch-units-20261020` | 111 PASS，11.63 秒；1 条既有 Starlette/httpx 弃用警告 |
| Ruff：两个产品文件及修改的测试文件 | PASS |
| `mypy src` | PASS，113 个源文件 |
| `git diff --check` | PASS |

使用仓库原 `requirements.lock` 在本实例 `.venv` 安装锁定依赖；未更新锁文件或系统环境。没有执行全套 pytest、Windows、PostgreSQL、CI、真实模型/语义/场景或真人验收。

## 一次两臂短因果回归

脚本与小型记录见本目录 `causal.py`、`summary.json`、`results.json`。输入是已提交归因 archive 的唯一闭库成员 `phase/baseline-first-only/prefix-copy.db`，不是恢复旧实例；helper 来自同 archive 的 `source-helper/repeat_cold_first_binding_v4.py`。每臂独立子进程、相同初始 DB 字节，各调用一次 dormant `_cold_first_binding`，每臂上限 45 秒，没有重试。旧臂仅通过 AST 提取并覆盖基线 SHA 的三个原函数，其余生产源码 footprint 与候选臂一致；独审另行逐项核对提取结果。

`causal.py` 是实际执行脚本的原样副本（SHA256 `fce13798fa4d76f89a69f89802b3dc00ebbc7828cc48b40f0b539c61465b411a`），不在本目录直接运行。本次准备目录为 `/tmp/sim2act-dispatch-causal-20261020`：从上述 archive 分别写入 `sealed-prefix.db`、`read_pin_helper.py`；从固定基线 AST 提取 runtime 的 `_cold_graph_validate_inputs`、`_cold_graph_row_storage` 为 `natural_spec_runtime-baseline.py`，以及 admission 的 `_trial_typed_storage` 为 `natural_live_admission-baseline.py`。实际命令为 `.venv/bin/python /tmp/sim2act-dispatch-causal-20261020/causal.py`；没有再次运行旧 first_probe.py。保留脚本是为了审查本次运行，不构成新 probe 或完整链授权。

未初始化 Worker 壳和未批准 synthetic read pin 只供局部连续性检查，不构成真实准入。为使两臂原始输入字节相同，仅替换 helper 自己的 `time` 绑定，构造后立即恢复；产品 `time.time` identity 始终保留。实际权限读取照常执行；SQL 只允许 SELECT/BEGIN IMMEDIATE，Worker 执行、claim、审批、journal、HTTP/Mock 和模型发送入口设 tripwire。

| 相同计时范围：仅 producer body | 原函数臂 | 产品候选臂 |
| --- | ---: | ---: |
| wall 秒 | 5.908685808 | 5.864404493 |
| thread CPU 秒 | 5.907745509 | 5.860985705 |
| check / add / input_key | 2028 / 130 / 2158 | 2028 / 130 / 2158 |
| SELECT | 2814 | 2814 |
| 实际 producer 次数 / exit | 1 / 0 | 1 / 0 |
| DML / 模型 / blocked | 0 / 0 / 0 | 0 / 0 / 0 |

最终完整输入 **579257 字节逐字节相同**，SHA256 为 `602f6085bab51007c9090974c0a3223a0f5f4d061039f0491f8b0225ce6f98e4`；SQL 与参数的有序累计摘要均为 `0e2ee3d39ace7437f58f782d3df63fc9b8ada0926054d780081b3b881dacae27`。源闭库与两臂副本前后 SHA256 均为 `9a9bdfcf0264a251670a2c59dcbd401e1e035656542413e032357a442802e4db`，helper SHA256 为 `1714d223e667948a1d84a54abfdb8e35f2670c6384fc162581105da775cf6d8a`。产品源码前后未变。

独审核了脚本、AST、上述原始文件和完整 bytes，确认有限等价结果；SQL 仅保存累计摘要/计数，没有逐条原始日志，不能独立重算每条 SQL。未为补记录重新执行。check/key 的计数不含 scope 初 pin 与退出，不能与旧探针的 2030/2161 混用。

观察到 wall 少约 **0.75%**、CPU 少约 **0.79%**。固定顺序、每臂一次，无统计重复；该差异不足证明实质改善，也不能与旧的 23.08 秒（不同观察器）或 37.52 秒完整 G0 相比。它是局部等价与边界回归证据，没有解决原 G0 超租约的性能阻塞。下一步仍需寻找可证明安全且有实质收益的源码局部；不得通过复用可变状态、放宽租约或跳过准入来取得通过。
