# `input_bytes`：复制复用候选的实证筛选

基线 `b9a6bfaad5212c0a8f799975afa4893d613b3308`。本轮未产生满足安全与收益
条件的运行替代，产品 `src/`、`scripts/` 保持原字节；交付实际 PB 合同上的四项
字节/别名回归及候选成本证据。没有重做全链 profile、运行 G0 或用窗口赌时间。
这不是断言所有优化不可行，也没有将新的设计视为已实现的优化。

## 当前结构及四个真实反例

`_ColdGraphRead.input_bytes` 每次调用原 `_trial_typed_storage(PBTrialContract, ...)`，
随后用原 C Pickler/protocol5 编码全图。storage visitor 的本次 `seen` 已使每个
唯一非标量源节点仅复制一次；active 在 seen 之前检查以拒绝 cycle。原模型和原
dict/list/tuple 源可以与 `inputs` 共享引用，输出投影则有自己的 fresh 容器及 DAG
别名。直接复用源、持久保键或提前浅拷贝不是等价的分配省略。

新增 `tests/test_cold_typed_storage_alias_contract.py` 用原 `prepare_pb` 创建实际
PBTrialContract，走原 storage gate 与原 C Pickler，无 Worker/model/HTTP/Mock。

1. 原 `caps.__dict__` 也被 inputs 引用时，投影 caps 是独立 dict。复用原 caps 即使
   完整值严格相等，也会合并跨图 memo 别名，原 pickle bytes 不同。修改原 caps
   run_seconds 后，新的原投影读取新值，旧投影仍保留原值。
2. 当前源键是 equal 但不同 identity 的新 str，并与 inputs 共享时，保留上一 dict
   键再 update 当前所有值仍保旧键对象。键序及完整 typed 值相等，原 pickle bytes
   仍不同；不是普通 dict equality 能证明的等价。
3. 在提议的 `dict.copy(raw)` 与原序 DFS 之间替换 quota_subject，若仅在
   `visited is not child` 时回填，会留下旧的、未被本次 DFS 选中的值。实际原新投影
   bytes 已变化，该错误替代的 bytes 却仍与旧 pin 完全相同，会掩盖新鲜变更。
4. 改成无条件回填当前值仍无法修复早期快照保留的旧键身份及顺序。通过同大小
   删除/重插或替换实际原生 dict，可使原 visitor 的当前键序/键对象发生变化，错误
   替代仍保早期顺序，原 bytes 不等。

后三例的错误算法只在测试中作为被否决的本地草图，不接生产；所有值仍经过原
visitor。显式 interleaving 表达复制与后续读取之间的可变窗口，不声称隔离任意
进程内猴补丁。第3例也验证比较最初副本槽可修复该 scalar 漏洞，但不能修复其余
键身份/顺序问题。没有把异常顺序或任意回调行为凭空增加为产品要求。

保键池因此不等价；clear 后重建虽可恢复本次键对象，却不保留 dict 的内部 entries
存储，不能假称它省掉了主要分配。依据
[CPython 3.12.14 PyDict_Clear](https://raw.githubusercontent.com/python/cpython/v3.12.14/Objects/dictobject.c)，
clear 替换空 keys 并释放旧 values/keys；本轮没有把这项源码事实冒充成本实测。

## 仅字节输出缓冲区的有限实验

合同投影完全不变，只在离线原型中 seek0→写同前缀→fresh 原 C Pickler/memo→
truncate 当前末尾→getvalue，所有输入每次仍完整遍历，未缓存摘要/PASS。先检查
长短交替与持有旧返回 bytes 后的不可变性，再交替六轮计 owner-thread CPU。
此原型不含未来产品所需的全部 code/factory 资格和 scope/异常/重入生命周期措施，
未进入产品；不声称这些措施已通过测试。

| 实际输入与范围 | 每轮次数 | fresh CPU 中位数 | 原型 CPU 中位数 |
| --- | ---: | ---: | ---: |
| 原 prepare_pb 合同投影，4311 bytes | 2000 | 0.0150812345 s | 0.0150928610 s |
| 上轮正常完整合成链的只读 SQLite，225行，原 SQL RowMapping，736577 bytes | 50 | 0.1210591950 s | 0.1201837690 s |

合同样本没有收益；较大行快照约减少0.723%，尚未计产品资格/管理成本。后者是真实
已存合成数据，用实际 C 编码器，不是原 G0 的完整 guard.inputs 图；不能外推完整
流程收益，也不能从小差值证明所有输出池方案无益。本轮证据不足以采用此候选。

原 SQLite 通过 mode=ro URI 读取，前后 SHA256 均为
`0d65862f50aa545fb93aa31e15d3f78c74bcca09e57976c3b65e0b04d1fc6b36`。
未改已有数据库、恢复 RECEIVED Run 或调用原 producer。

[CPython 3.12.14 BytesIO 实现](https://raw.githubusercontent.com/python/cpython/v3.12.14/Modules/_io/bytesio.c)
的 getvalue 将内部 bytes 收至当前长度并可共享返回；旧返回值仍被持有时，后续写入
要复制原内容。它不是稳定保留过量容量的零拷贝池。原型末次数据还会驻留于私有
buffer，不能称无跨调用驻留或 RSS 必降。

## 本轮结论与最小后续技术方向

当前已评估的投影容器复用不安全，原生输出缓冲复用没有充分收益依据，因此保持
原实现；没有合格候选可进入同输入最终全链 A/B，未为未变的路径追加完整链。
所有原授权/撤权/SQL/事务/scope/fence/stop/期限及原协议继续由原代码执行。

一个明确的后续方向是**原生 fresh typed projection visitor**：仍构造原隔离容器、
原每次 seen/active、原键对象/顺序与完整字段及None omission；将逐节点 Python
执行成本移入原生后端，继续调用原 C Pickler，不重写 pickle 或改变协议。必须先
闭合 exact类型、模型字段/selected/extra/private 元数据访问顺序、共享DAG/cycle、
混合错误和异常所有权，使用保留当前 key/value 读取语义的迭代 API；然后处理
CPython ABI/构建及后端资格，未知或未资格环境在动作前选原 Python 路径。该方向
不是已证收益或唯一解，本轮没有新增后端/依赖/权限。不能以全局 GIL 自动证明
整个原 DFS 不会发生并发 mutation。

另一方向是把该具体根及完整消费者迁到服务端拥有的不可变领域快照，但它涉及
原别名/指纹合同、完整消费者及可变前沿证明，不能将既有局部 owned 组件直接当作
该合同的运行资格。这比单纯复制器替换更广，本轮没有扩张此路径。

## 实际验证、清理及版本

- 最初三反例：3 passed /1.36s；补入直接源 caps 复用反例后，最终 **4 passed /1.84s**。
  最终测试 SHA256 `cdc7f22c43e9233c2b3f691c235dfd55cbf59c51f4d794b57bf8ddcf27f4a9c9`。
  两版源码均存原件；最初版复原后精确匹配阶段独审的 `ac1182ee…`，不拿旧日志
  冒称四例已运行。
- 输出原型：合同1 passed /1.16s；只读行快照1 passed /1.92s。CPU采样均在无
  profiler 进程内；原型源码及六轮原始值保留，不向G0推广。
- Ruff 通过。每个命令真实上限60秒+10秒清理；API仅本地 ASGI，fixture 禁止
  Worker/模型及全部真实/Mock transport。**实际0 Mock、0 Worker、0真实模型、
  0 G0、0完整尾段对照**，没有新技术 grant 或费用。
- 原 clients/Store 关闭，最终无 pytest/timeout 或 SQLite sidecar。工作目录约
  5.28MB，是实测占用而非原生硬配额。源/scripts diff为空，最终源码清单与
  postrun 原件保全；本次只提交回归及证据。

`artifact-manifest.json` 记录 `originals/` gzip 原件及压缩/解压 SHA256。SQLite不提交，
实验原型不作为生产组件。`reviews/` 独审只读，未运行产品、测试、DB或Mock；较早
三例回执与最终四例/文档回执分别保留。
