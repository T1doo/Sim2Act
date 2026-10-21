# Cold `_base` 固定纯段：完整内容出口收口候选

基线：`a8b0a0c5de75ae494d9fc77dae2c95a6a6645892`。本轮实现运行代码、严格合成
差分及反例，没有执行真实时钟 G0 launcher、真实模型、W5 或新的生产资格授予。
候选仅对既有默认关闭 native 模式中已发行且通过当前资格检查的 `_base` 生效。
常规未发行、默认和不合格模式保留双完整检查；没有新增启用开关。

## 固定边界

`_ColdGraphRead.check` 抽出原顺序的 header / connection / transaction / scope / epoch /
settings / source-read-token 等动态谓词。公共 `check` 仍固定调用这些原谓词，再进行
完整原内容校验；不能由实例遮蔽新增 `_check_dynamic` 方法来跳过动态门。原 stop 和
owned registry / binding / model / max-output-token 检查仍由 mode 在原两端执行。

合格 `_base`：入口原动态检查及 mode/links → 私有固定模型收集段 → 实际所有嵌套模型
的当前存储与 schema / compiled serializer / code 资格 → 全部原 typed 比较及原标准
序列化比较 → 出口原 mode/links 与动态检查、完整 frontier 编码。只有正常出口完整
检查通过才返回；不发布中间结果，不增加 SQL、授权查询、业务时钟、根、输入写入、
结果回调或外部调用。family / Run / stage / strict typed 谓词都执行，没有跨调用 PASS、
通用 skip 参数或重入状态，也没有跨 SQL 合并。

纯模型收集段从原 `_typed_parameters` 抽出，仍只构造本次局部 triples；不执行
`model_dump`。模型 DFS 覆盖 nested Any，逐次复用既有 `_fixed_schema` 完整当前形状及
原 compiled metadata 见证，不以 C serializer 类型或 schema 对象身份单独认定纯性。
未知 serializer / schema 在任何未知序列化前补原完整入口，再走原 typed bridge 和
完整出口。未知 helper、实例方法遮蔽或不闭合存储资格直接选旧双完整路径。

本次资格不是一次完整 raw 内容预扫描：只读实际纯段会使用的固定表/字段的 exact
表示、已发行 family 和本次 typed 模型。具体保护包含 root native keys、私有 inputs /
issued tuple(role, packet)、active bool、binding/header、scope frame、实际实例 method
身份及相关固定 helper 身份。`seal` 保存服务端当场新建两 proxy 的私有原始身份；
不对未知 MappingProxy 迭代或 getitem（它可包装 foreign mapping）。这些私有控制引用
不作为协议字段或替代摘要混入旧 raw/pre/post/origin/software 指纹合同及持久证明，
不解冻或裁字段。

入口已损坏时，所有新执行步骤必须无回调/无可发布副作用。固定纯 collector / typed
失败且 graph/mode 仍 active 时，在失效前补完整内容检查，保留原入口 raw 拒绝优先级。
已关闭 mode 的原异常直接传播；未知回调分支在原完整入口后抛出的异常不会被 finally
检查覆盖。原 `_base` 异常关闭 graph/mode 并置 INVALID；没有失败后重放、降级或续命。
这不声称隔离任意进程内改码、任意 profiler 或对 `require` 本身的替换。

单个 BEGIN IMMEDIATE、连接、原 SQL/完整读集、授权/撤权、来源解析、fence、stop、
Run、lease 30 秒、Run 300 秒、TTL 1800 秒及最终时钟门未放宽。其余可变根、独立公共
入口和 SQL/授权返回后的原 checks 保留。

## 完整严格合成差分

沿上一轮原 `configured` 三项资格替换（environment / account resolver / software），
使用本轮新建前缀和新 SQLite。Generate3 + Source2 后，每个独立副本 Cold1；真实
Store/Worker/审批/账链及原 prepare→首 commit→Cold receipts→第二 commit→原 scope
正常退出。原 pre 的 `audit_seed=None` 未伪造。虚拟业务时钟及原 heartbeat 同上一夹具，
运行产品时钟未改；两边 lease/期限和全部原门相同，不能把暂停业务时钟当性能通过。

旧对照仅令本次 `_base` 不进入新纯段，保留双完整检查；上一轮两个 policy wrapper
在两边都保持相同。新旧正例在内存中用 **`exact_output` 严格比较完整 authority outputs
和完整 SQL 序列及参数**，保留 bytes、bool/int/float、list/tuple、quoted_name 及 quote；
另有单测证明不能借 Python `True == 1 == 1.0` 掩盖差异。诊断编码不是业务指纹替代。

完整主测试 **1 passed / 289.74s**，含六个场景。原生产源码及测试在执行期间冻结。

| 收窄前完整 A/B：整个原 context 内实际计数 | 旧双完整 pin | 候选 |
| --- | ---: | ---: |
| codec | 8337 | 8062 |
| 累计 codec 返回 bytes | 4,894,540,040 | 4,682,215,371 |
| 被观测 `_base` 入口 | 569 | 569 |
| 正常返回 / 故意闭 scope 拒绝 | 568 / 1 | 568 / 1 |
| 合格单内容检查 `_base` | 0 | 275 |
| 原动态检查 | 1137 | 1137 |
| 前台 SQL 语句 | 7735 | 7735 |
| 原 Run 行谓词入口 | 2 | 2 |
| 两 commit、Cold receipt、原 scope 正常返回 | 完成 | 完成 |

动态次数精确为 `2 × 568 + 1`，额外一次是故意跨关闭 scope 的拒绝入口，不能把它
当作缺失的成功出口。原 family / Run / typed 谓词序列在无 Mock 的 issued SQLite
定向测试中相同，合格 `_base` 2→1 codec、两端动态、段内 SQL=0。

整个观察 context 的编码减少 **275 次（3.299%）**、累计编码输出减少
**212,324,669 bytes（4.338%）**。这是完整 first binding 至原 scope 关闭及故意跨 scope
拒绝的实际范围，不是仅局部纯段计数；没有测量未观察路径的收益。资格检查和模型
DFS 有实际 CPU/分配成本，本文不将编码计数降低当作 CPU 提速或真实 G0 期限通过。

原最终期限过期、frontier 突变、原 `check_source` 撤权和真实 SQLite CHECK 约束失败
均按原门拒绝并关闭 scope；原错误信息、实际到达阶段及两次 commit 输出保留。
写故障先成功 INSERT(1)，再 INSERT(2) 得 sqlite_errorcode=275，回滚后 probe 表 0 行。
**这只证明同事务测试 probe 回滚，不是 W5 五写组故障覆盖**；旧证据 README 已同样澄清。
两条正常路径最终仍用 BaseException 在 W5 前保留 RECEIVED，不能称完整业务成功。

本轮实际 **11 次 Mock 交换 / 13 次方法入口**，逐条日志一致；固定六个尾段各 1/1，
共享前缀 5/7。沿用测试类保护上限 13/15（含 Source 两个同步 delegate），没有自动重跑；
实际消耗未超过本轮计划 11/13。真实监督 `timeout --signal=TERM --kill-after=10s 300s`，
所有本轮线程退出、clients/Store 关闭，无 pytest/timeout 残留，无 SQLite sidecar。
新前缀从零生成，不使用上一轮 checkpoint 或失败 Cold DB。

## 定向与静态验证口径

- 最初现存 base/严格编码组合：16 passed / 20.25s。
- 新切片首次：13 passed / 1 failed / 24.13s；是负例误以为替换 child serializer 必须拒绝。
  实际原 parent compiled serializer 未调用该 child，正确兼容行为为原路径接受、两次
  完整 pin。纠正测试，没有为迎合测试修改产品接受域；原失败日志保留。全部 0 Mock。
- 六文件组合：53 passed / 61.04s；新增 unknown-member 资格修补后，新定向文件
  26 passed / 41.43s。其后默认 None 路径短路，避免提前导入 native 实现，补检
  8 passed / 3.23s。各自冻结清单保留，不把不同版本测试冒称同一字节版本。
- 反例包括 raw 入口损坏、raw+typed/raw+stop 混合拒绝顺序、新旧独立 epoch 比较，
  段内 raw/stop/settings/写入撤权/epoch/scope 变化；未知 dump/schema/nested serializer
  保留双 pin；实例 shadow、foreign key/role/bool/header/proxy/binding 无回调资格拒绝；
  未知 helper 及原异常对象、graph/mode/phase 失效。
- class-list helpers 本身也被原完整 codec 使用，相关未知 helper 反例明确加原动态拒绝，
  不声称单有 raw 漂移便能保证旧 codec callback=0。独审较早过强描述已在后续 ACK 纠正。
- 最终七文件广回归：**152 passed / 78.74s**，使用 `freeze-final-regression.json`
  的最终源码/测试，退出后摘要相同。覆盖新切片及原 policy、admission/tail diagnostics、
  typed guard delta、fixed key dumps、typed stream。首次广回归 26 passed / 1 failed /
  44.15s，是旧 policy 测试写死旧 base 的编码数：已从 12/4 实际变为 6/2。改为同时
  验证原双内容与候选单内容 base（requirements 12/4 与 6/2，RunCheck 14/4 与 7/2），
  没有修改产品去迎合该测试。原失败日志保留，0 Mock。
- Ruff 八个相关文件通过；mypy 三个 source 文件通过。首次 mypy 一处 Optional 迭代
  报错，只加局部 `Any` 注解；与完整集成被测源码的 115 个 executable code objects
  均逐项相同（不含位置元数据），原 source、前后摘要及比较见证保留。未改运行行为，
  也未重跑 Mock 来掩盖字节区别。115 code-object 等价仅指这一注解中间版本，
  **不覆盖随后新增的最终资格存储头检查**。

## 最终资格存储头收窄及证据版本

提交前又发现并实际红测一个入口表示漏洞：从 exact Pydantic model 读缺失的 caps /
model / max-output 字段时，`__getattr__` 仍可能访问被破坏的 foreign extra。原完整
codec 的 `_trial_typed_storage` 会先以完整字段和 extra/private is None 拒绝它；原
较宽资格实现可能提前执行 foreign truth。`pydantic-header-red.log` 1 failed / 1.79s
确实到达 ForeignExtra.__len__，不是假设性警告，0 Mock。

最终仅收窄 `_base_pure_ready`：直接 object/type storage 读取合同和 caps 的完整
__dict__/fields/fields_set/extra/private 头，先 exact native keys/types 再比较，从 native
raw 取 caps/model/max-output。binding 的三个实例头也直接读原生 dict，init=False 的
version 则用 `getattr_static` 保留正常 dataclass class 默认且不执行 descriptor。
未通过只回原完整路径，不新增业务拒绝、不改变纯核心/动态/SQL/内容指纹。

首次收窄误把正常 class-default version 当作必须在实例 dict 中，首 positive 资格被
关闭，1 failed / 1.74s，见 `header-refinement.log`；最小修为上述静态读取，并同时保留
正常资格/单 codec、四个 Pydantic 损坏回调零执行及原完整拒绝的反例。
最终此三文件定向组合 **67 passed / 91.74s**，最终十文件冻结退出后仍一致，0 Mock。

**最终源码不是完整 Mock A/B 的同一 SHA，没有再次运行 Mock。** 完整 A/B 使用
`freeze-integration.json`，152 项使用 `freeze-final-regression.json`；最终存储头收窄使用
`freeze-final-header.json`。兼容推理边界是：原完整 CGR 成功出口已对合同和 caps 执行
同样的完整 storage 头谓词；已证明的固定纯段不写输入，因此每个原合格正例入口也
满足新增头。version 原正常 class/实例 exactstr 由静态读取保持。最终门仅收窄未知
表示、不改变既有正常纯段选择；同一真实 issued SQLite fixture 的新旧局部输出、
谓词、动态两端及 codec 对照再作定向验证。上表是原完整观察值，不冒称最终字节版
新性能测量，更不从中推真实 CPU 或 G0 通过。

原件、测试/源码冻结、失败日志、11 条 Mock、完整输出、结果、解压 SHA256 和阶段
独审在 `artifact-manifest.json`、`originals/`、`reviews/`。SQLite DB 不提交。
独审为只读代码/证据审查，没有另行运行产品、测试或 Mock。

真实时钟 G0、生产账户来源资格和 W5 仍未验收。本轮完成的是这个固定纯段候选及
完整严格合成差分；没有以设计/代码 ACK 自动授予后续运行窗口。
