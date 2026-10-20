# Cold codec 固定前缀缓冲：有限分配优化，非 G0/PB 修复

基线为 `78ed5bef2da3a175d819eb9a2f58b3bbf097f75b`，接续原开发分支。本切片仅在 `_cold_graph_bytes` 的全新私有 BytesIO 中先写入原固定前缀，再执行原样的 fresh protocol 5 Pickler，直接返回完整 `getvalue()`。它消除最后一次显式 `prefix + complete_payload` 拼接，不更改输入遍历或 reducer，也不宣称所有缓冲操作均零拷贝。

## 等价边界

CPython 3.12.14 的 `_Pickler_SetOutputStream` 仅取得 `file.write`；frame/output 长度与 memo 位于 Pickler 自身，不读取外部流的起始 offset/tell。BytesIO 从当前位置追加，`getvalue()` 返回整个内容（可能先调整缓冲区大小）。因此前缀之外的 pickle payload、帧、memo 和别名拓扑不变。参考 [Python 官方 `_pickle.c`](https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/_pickle.c)、[官方 `bytesio.c`](https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/_io/bytesio.c) 和 [Pickler 文档](https://docs.python.org/3.12/library/pickle.html#pickle.Pickler)。

所有数据/原始 SQL RowMapping 存储、隐藏位置、安全索引、完整 Limits、元数据可变别名和 import hook 可见变异仍通过同一新鲜扫描。没有快照、身份/版本缓存或 checkpoint 合并。check/add、SQL/serializer/deepcopy 后 pin、seal、最终实际时钟、fresh permission、ALLOW、原五写及拒绝事务语义均未改。返回的 exact bytes 不暴露私有流，后续输入变化不改变先前结果。

不新增 catch，不替换 reducer 或领域拒绝异常；CPython 既有 marker import 失败转换为 PicklingError 的行为保持。**资源耗尽异常时点不作等价承诺**：新小前缀写入发生在 dump 前，旧整段拼接发生在 dump 后，分配失败的位置可不同。这是分配优化的明确边界，不代表允许通过准入失败或改变正常领域错误顺序。

独立 reviewer 在开发前核对源码/API，批准该局部；开发后只读核对实际 diff、旧函数 AST、脚本、receipt、原始字节与实际测试记录。审查摘录见 [REVIEW.md](REVIEW.md)。

## 实际测试

定向命令：`.venv/bin/python -m pytest -q tests/test_cold_graph_fingerprint.py tests/test_cold_graph_row_storage.py tests/test_cold_trial_pure_cohort.py tests/test_cold_trial_guard_delta.py`，本次另指定新 basetemp 与 JUnit 路径。

- 首轮 **117 PASS / 1 FAIL，11.50 秒**。新测试错误地预期 import hook 的 ValueError 原样传出；CPython 原有 Pickler 实际将该错误转换为 PicklingError。产品未为此改变；保留失败日志 `initial-pytest.log.gz`。
- 修正 oracle 为与原无前缀 Pickler 的异常类型/消息对照，并补真正 reducer DomainError identity 反例后，**119 PASS，11.12 秒**。保留 `final-pytest.log.gz`。两轮均有 1 条既有 Starlette/httpx 弃用警告。
- 新测试覆盖 0/255/65535/65536/65537/579257 大小、独立 chunk-stream oracle、协议 opcode/多帧、共享原始行/隐藏数据/索引、完整 Limits、immutable 返回值及 reducer/import 错误。保留原 import hook 行间元数据变异、hostile 类型、sticky/root-backedge/错误优先等回归。
- Ruff：修改的产品/测试文件通过；mypy：113 个源文件通过；`git diff --check` 通过。

两份 pytest 日志均无损 gzip 保存，解压后保留原始尾随空格及全部内容；没有为通过 diff 检查修改原日志字节。

## 有界合成 codec 分配短测

实际脚本 [allocation.py](allocation.py)，记录 [receipt.json](receipt.json)。旧函数通过 AST 从上述固定完整基线提取；其余代码相同。两个独立子进程（每臂一个），各按固定顺序对三个合成向量分别编码一次，每向量重新 start/stop tracemalloc，每子进程上限 15 秒，无重试。向量构造及完整入参验证在测量区间之外；allocator 和顺序历史仍可能影响结果。HTTP/Mock 入口禁止；没有 Worker、DB、准入、模型或 G0 producer。

| 合成 bytes 字段长度 | 完整输出字节 | 旧编码 peak bytes | 新编码 peak bytes | 峰值减少 bytes |
| ---: | ---: | ---: | ---: | ---: |
| 6435 | 6864 | 16317 | 16346 | -29 |
| 65536 | 65974 | 132177 | 77154 | 55023 |
| 579257 | 579695 | 1159619 | 655090 | 504529 |

三组完整输出均实际逐字节相同，hash/长度见 receipt；runtime 源码前后 hash 相同。向量包含 exact RowMapping、quoted_name、隐藏数据/索引、完整 Limits、共享 alias，不是从不可加载的 pin bytes 反序列化。这里只量化单次编码阶段的 Python traced allocation 峰值，不能当 RSS、累计分配量、所有输入的普遍收益或耗时收益。小向量峰值略增；较大合成输出观察到峰值下降。未对 G0 提速作任何推断。

脚本为本次原样执行副本（SHA256 `c315b09afb477a728456b8af08aaacda9f83702d085b4382f6981ed2a4db3efc`）；实际准备目录 `/tmp/sim2act-envelope-20261020`，命令 `PYTHONPATH=src .venv/bin/python /tmp/sim2act-envelope-20261020/allocation.py`。脚本自行从 Git 提取旧函数，并拒绝覆盖已有 baseline 文件；后续若需复现，应复制脚本到新临时目录，此记录不授权额外执行。

没有新增或更新依赖，没有增加租约/TTL、权限、凭据、费用或真实模型调用。未执行完整 pytest、G0 对照、完整 PB、Windows、PostgreSQL、CI、真实语义/场景或真人验收。原完整 PB 仍 **FAIL_NOT_ACCEPTED**，W5/G1/finalguard 仍 **NOT_REACHED**；原 G0 超租约阻塞尚未解决，不能据此建议完整 PB。
