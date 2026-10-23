# Cold 成本准入：当前无可实施的新性能方案

基线 `068aca324ab405d6a9cb275347ca8d0076a35de9`；仅复读已封存原版报告和已撤回 `0c36b88fbead2fe07f8a60cdc51cbbc4f2dafd62` 源码。本轮**零新测试、Worker、Mock、profile、CI、G0 或真实模型**，不改产品、C 叶子、缓存、Python 全图算法、事务或期限。本分析不重开该算法或完整 A/B。依据及源码定位见 [source-facts.json](source-facts.json)。

## 计时口径补充

`SemanticClock.__init__` 记录一次真实单调时钟 `started`；测试随后才构建 prefix，再跑原版和候选。`reset()` 只更新业务时钟值和线程集合，**不更新 started**。所以 `healthy()` 的300秒覆盖 prefix、两臂及中间准备，不是候选臂独立300秒，也不是生产 Run300 或 lease30。

监督器记录443.411774160秒，exit1、stop_reason=null、无监督器错误、自有进程组不存在。这是整个监督运行的异常退出时间，**非外层600秒强杀**。不能用443.412减原版43.599推算候选：两者计时起止不同，前者还含 prefix、恢复副本、准备、pytest及清理。候选在原 context 返回后的 `healthy()` 抛错；后续断言和严格 A/B 比较未执行。候选耗时、codec、选路、重建和回退计数均 UNKNOWN。此前全部[原件](../cold-frontier-fresh-compare-20261023/README.md)保持原字节。

## 原版观测的适用范围

| 已封存的实际值 | 可用于什么；不能用于什么 |
| --- | --- |
| Worker.once 原臂 thread CPU43.357651307s / wall43.598850574s | 这个合成臂的整个 owner 区间；不是G0租约区间、候选时间或纯codec时间 |
| 8062次codec、4,682,215,371返回字节 | 全观测区间的编码总量；不是新 Frontier 后端全部可替代的分母 |
| Frontier `legacy=2139` | 该 `_current()` 检查调用域；不含其构造/added直接key调用，也不提供该域字节或独占CPU |
| base调用569、正常返回568、qualified275、dynamic1137 | 函数/边界计数；动态检查数不等于完整编码数，不代表1137次可删遍历 |
| SQL7735、Run谓词2 | 原臂计数；不能把SQL逐条折算codec或省略查询/权限门 |

本轮不混入旧profile的不同版本/有仪器时间，不叠加 inclusive 父子时间。原臂报告SHA为 `68d8fdaee86b063bb4731ac53a1f378aaa5da03f2b34024103dadfb0cfc9c9c7`，从已封 tar 成员重读，非重执行。

## 边界必须支付的工作

记 `D` 为原连接/事务/scope/epoch/settings/stop动态门；`F` 为 frontier全根刷新及owned路径身份关系；`P` 为完整新鲜PB投影；`K` 为完整C Pickler图遍历（一个新memo）、RowMapping/Limits适配、输出缓冲及SHA；`T` 为原typed实际值/raw/schema/关系校验。`D` 不代替 `K`，`K` 也不代替授权、SQL或业务时钟。

| 原边界 | 当前应保留的工作 | 0c36没有消除或额外增加的工作 |
| --- | --- | --- |
| CGR建立/原独立 `check()` | 初始化完整校验及key；每个实际check先D，再完整当前内容。native域是F+P+K，非native域是原P+K | 比较器只挂native Frontier，未替换其余所有codec；没有把PB变成不可变源 |
| 合格 `_base` 固定纯段 | 入口D、当前mode/links、收集及新鲜schema资格、完整T、再次mode/links、出口D及完整内容pin，返回前不发布结果 | 已审代码对合格纯段已集中为出口一次完整内容。不能再删一个假想的入口全扫描；未知serializer/不合格仍原双完整pin |
| `_trial_typed_guard.checked()` | 原parent之后，仍完整检查自己的全部model/raw三元组 | rawA与parent rawB不是同一根；recheck还带新SQL/model，不能继承parent PASS。parent末端codec后不能假定child内容没变 |
| `_graph_trial_produced()` | serializer前、返回后、三元组入cohort后，原完整guards依次执行 | serializer/新根是边界；不能把三次调用计成三个同一输入且可删的扫描 |
| SQL、授权、来源解析、Run/version/fence/时钟的原返回点 | 各调用原位置查询、原guard及完整读集/空集/集合关系；at/end仍原单次采时钟及原期限 | 不跨这些边界合并内容验证，不由同事务推导Python对象不变；不同guard层次的次数不互换 |
| `graph.add()` | 旧域完整check，incoming完整验证/forbid-root，插入精确新边，whole-envelope新key：保留跨新旧根的memo/别名 | 候选额外计算pending旧域全key，失效旧baseline；不能把新根独立pickle后拼接 |
| receipts、第二commit、scope关闭 | 原回执方法和新根验证；第二次 `_recheck` 全部动态/内容/SQL门；退出再完整pin，关闭后原最终时钟 | 不以首次commit、局部codec下降或context返回推断全部终局断言通过 |

RowMapping适配读取原keys list、完整data tuple（含隐藏值）和安全index关系，foreign index仅遍历且不调用其hash/equality。Limits仍读六字段及extra/private门。一次pickle内部memo可以处理共享对象；跨调用保留旧memo/摘要/metadata结果不符合当前可变源合同。现有Source/Generate owned路径已排除的纯值不是待重复排除的新机会。

## 0c36的成本账和准入式

令 `Q` 为新选择阶段完整事件图构造（含预算、fresh memo、适配器和分配），`E` 为两个不可变事件图比较。以下是**正常等价路径的静态条件账**，不是候选实际计数：

| 情况 | 与原版相比 |
| --- | --- |
| 成熟且选中 | 原D+F+P+K变为D+F+P+Q+E。F/P仍在；只有K−Q−E可能成为收益 |
| 建立baseline | 首个F+P+Q后，仍做原K/SHA确认，再第二次F+P+Q和E。相对原check额外F+P+2Q+E；不是“构建一次后免费” |
| 新根 | 原旧域check/incoming/newkey保留；另付旧域F+P+K，且下一版本须重建baseline |
| 选择不适配 | 已付F+P+部分Q，再走原F+P+K。初次decline可避免本版本后续选择；已有baseline的临时不适配仍可能重复支付选择 |

因此必要条件为：

```
成熟选中检查累计(K - Q - E)
  > 基线额外累计(F + P + 2Q + E)
    + 加根额外旧域累计(F + P + K)
    + 不适配额外累计(F + P + Q_partial)
    + 管理/资格成本
```

同一回调/适配工作已包含于K或Q，不能再次叠加。原动态门及T全保留，不是收益项。每个图版本输入规模不同，不能按平均总字节或2139次调用均摊。源码允许的新增名字最多12个固定root＋2个receipt名字＋2个release-pointer；这只是名字数量上界，**非本轮实际add数、图规模界或重建成本证据**。

现原件缺该Frontier域的独占CPU/字节、各图版本输入量及候选Q/E、selected/baseline/fallback/add分布；候选无完整报告。小型SQL组件更慢也不能推算整链比值。准入式现在不能解出正净值，故**停止该算法，不补profile、不调整计时器、不重试A/B**。

## 唯一可具体描述的省工作项，仍不准入实现

若仅在私有SHA key路径让**原同一C Pickler、原协议、新memo、原适配器**输出到摘要sink，保持两层原envelope字节顺序，原始business/origin `input_bytes` 继续返回旧字节，则可针对性消除外部BytesIO的写入物化/扩容。它不删PB投影、图遍历、适配或SHA，不继承PASS，不需新baseline（baseline成本0），也不是此前被否决的“删SHA”。

这只是可审核的操作目标，**不是安全/性能成立方案**：

1. 不能声称删除了每次 `getvalue()` 的全量复制。[CPython3.12.14官方源码](https://github.com/python/cpython/blob/v3.12.14/Modules/_io/bytesio.c)的`write_bytes`确有缓冲写入；`getvalue`某些路径返回现缓冲的新引用，也可能缩容/复制。现原版报告没有这些路径的独占成本，4.68GB不是可恢复CPU。
2. digest分块等于连接后digest，只证明相同字节下的数学结果。直接sink可能把调度/失败边界移入图遍历；[hashlib官方文档](https://docs.python.org/3.12/library/hashlib.html#hash-algorithms)说明大于2047字节的hash输入可释放GIL。额外Python `write`封装也新增回调/分配时序。当前借用可变图、共享metadata和跨根alias未证明可跨这些新边界。
3. 必要净成本条件是目标域累计`BytesIO写入/扩容 + 原整块SHA成本 > 分块SHA + sink调度 + 选择资格成本`，并先证明输出、错误和fresh读取边界。没有这些证据，不能加C sink/新C叶子、做微基准试运气或安排完整尾段。

对typed cohort合并同样未发现新的可省切片：已审纯段已有单一出口内容pin；另行省child检查会漏独立raw根，跨parent末端codec又不能继承PASS。更大的不可变所有权/消费者迁移没有因本次分析自动获得证明。**当前性能方案尚缺；不据此断言30秒不可能。**

## 真实账户来源的最小外部条件

这与G0性能是两项独立缺口，不能用合成resolver消掉。`production_evidence.resolve_account`仍固定SOURCE_MISSING，`production_trial_source`的四角色只标记SYNTHETIC，`production_preflight`先原审批再拒绝，未发行生产发送资格。

依原V5[身份/撤权、用量、持久化、指纹合同](../../平台产品设计.md)及既有[真实source接线缺口](../../F2/CorrectionRunEntry20261018.md#真实-sourcecontroller-的独立核查)，最小接入依据是：

- 供应方/受审可信来源能绑定**现有同一账户**身份、provider/model/endpoint和唯一quota subject，不能把token存在、开发者JSON、issuer标签或内容hash当来源权威。
- 同账户当前**分别可用的输入/输出额度**、适用权益、有效期/撤销与核查语义，使原预算能保守占额；未知不填零。不是只给历史余额或宣传免费额度。
- 可强制执行的**零新增费用、paid-cap0、无付费fallback/自动转付费**机制及其官方接口/记录合同；与上面账户权益是同一有效范围。无需人为要求供应方每30秒续签，也不新增凭据、账号或权限。

一个可信来源可以同时提供这些事实，不额外要求某种签名格式或多个端点。取得依据后还须实现/独审固定server-side producer、当前授权/fence/期限联结与普通Worker的受审注册；当前代码缺失不能表述成仅缺环境变量。已有token不再索取、复制、回显或哈希，本轮不尝试该外部操作或真实模型。此处只报告最小条件，不扩大LIVE/provider/PG/费用授权。

## 本轮验证范围

仅Git/AST/文件哈希/封存JSON与tar读回、官方文档只读核对、独立静态审查。未导入项目模块、未打开业务数据库、未跑pytest/Worker/Mock/profile/CI，未创建grant。产品`src/scripts/tests`仍精确等于068aca（也等于fd73的这些文件）；旧24项manifest及原件不改写。最终提交/远端差异另核。
