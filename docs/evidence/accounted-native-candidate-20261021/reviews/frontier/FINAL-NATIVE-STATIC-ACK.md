# Native 收口源码：最终静态有限 ACK

结论：**FINAL_STATIC_NATIVE_SOURCE_ACK_DEFAULT_OFF_ONLY**。此次来源、默认路径、安全语义与生命周期范围无未闭 P1/P2。前两轮报告保留为 earlier reviews，本文件仅签同名 JSON 的当前冻结 5 文件 SHA。预算数字、所有 allocation/work 上界由 monitor 独审；尚未核本轮最终回归原件，不宣称通过。不批准性能测量、G0/Mock/完整 prepare/commit、默认启用或产品资格。

独审仅只读源码/差异，以 stdlib AST/hash 对账；产品导入、测试、DB、Worker、Mock、PB/G0、prepare/commit 执行全部 0；仓库修改 0。基线 6570b7072e3cd415fbbcb3a130e8a80d9ad8be79。

## 已关闭的阻断

- CGR/frontier/candidate/mode 的 exact 类型、同 graph/scope 双向来源锚定仍在；跨图 frontier 不能豁免当前图，foreign 对象不能成为 callback 或跳过 oracle 的开关。
- `_Arena.node` 先 exact Packet、nodes exact tuple、ref exact int/range，后确认登记与索引；前两轮负 ref、bool、foreign __index__/__len__ 反例的门已齐。
- 发行前 `_Arena.seal` 把所有访问/标量/record/family/canonical/class 表转 MappingProxy，usage 变 frozenset，__setattr__ 在 sealed 后拒绝更换。构造期 backing 没有向调用者发行；release 仅将表替换为空只读表。owned_ready 后 mode 绑定 exact Arena 与原 ledger._native_arena 同指针，因而新读取不再信任可随意改写的发行后表。
- Source cache 返回前保留 `_source_parts` 的 Source role/aid/actual/read/chain 原归属；usage cache 同样先 family root/aid/actual 归属。只有 owned packet 的纯结果缓存。
- `_resolved_shape` 精确验证原真实 resolver 的 18 receipt 字段、每条7 proof字段、两请求/响应 bytes tuple，再作完整受控域遍历和原 Slot/Identity/Outcome/byte joins。未知或额外字段作为内部 producer 输出突变拒绝，旧 legacy 分支不变；未添加字符串长度 cap，真实 producer 输出域没有被更小 cap 代替。

## 新结构 class-ID 的语义

classify 只对 admission-owned immutable packet 进行一次完整结构 intern，以全原生 tuple key 比较真实结构，哈希碰撞仍执行原生完整 equality，不把 digest 当业务许可。字典键已由旧 freeze 规范为字符串，排序消除顺序；value tags 保留。list/tuple、bool/int/float、quoted value/str 不合并；float +/-0 与旧 _equal 的标量比较一致；共享 DAG/不同 sharing 依结构等价。全局 intern 在两 family 之间复用 class；equal 要求两 Node 属于同原 ledger/arena 且登记 ref 合法，跨 arena 不比较。

新测试源码包括与旧 `_equal` 的原生值双重循环对照、字典顺序、quoted key/value、共享、numeric tags、+/-0、list/tuple和跨arena拒绝；独审只阅读未执行。准入排序/哈希/原生键临时费用存在预费，数值充分性不由本 ACK 背书。

## 来源、frontier 与原阶段

- `_prepare` 的 Source 原 producer→完整 fields 校验→stage(Source)→原 recipe→原 versions SQL/backend gate→Generate 原 producer→原 fields/id 校验→stage/choose 保持。无第二 producer；upstream 完整 Run 比较在发行前 qualify，非发行后再冻结。
- 原 typed oracle 直到复制、arena/class/纯 Source canonical 完成仍保持，安装 frontier 前 `_assert_raw_before_owned` 最后检查原模型及完整 raw，再 seal/install/discard 令 owned_ready=True。复制后的原 typed mutation 不能在该窗漏检。
- 精确 frontier 仅替换两 accounted 专属根和 complete 的 source/generated/generation.run 三处；Generation/Source/audit/job、Cold job、metadata/raw/frozen/extraction 等其余根仍 fresh scan/typed。stage 9元组、binding/raw/metadata/frozen/extraction与 Source/Cold 分支 joins 原样保留于相应 helper。
- Future roots 是显式 12 名常量，新增根不在表内即拒绝。sizing Row 子深度继承，memo 复用检查最长后代，嵌套 Row carrier 是发行前 LEGACY 的 unsupported subdomain，不新增业务许可。
- native 默认关闭且只接受 test-only SQLite/pre。默认 constructor 参数 None，无配置/API 激活路径。原 `_freeze/_equal`、原 `_cold_graph_bytes/_cold_graph_validate_inputs` 完整 AST 及 live_admission/dispatch/archive 全文件字节对账保持基线。默认旧 bytes/raw/persist/origin 合同保留；candidate 活跃时默认 export/post 路径拒绝。

## 生命周期与证据边界

正常 helper 退出将 owned 资源留给原 graph scope：原末尾 check 先执行，再 invalidate 关闭 mode、ledger和arena。异常直接 close；递归 invalidate 由 active 防重入。离开 scope 后旧 Value 必须经过原 family/current gate，不能继续读 arena。SQL、实时授权、事务/线程/epoch、当前 Run/version/fence/lease、stop与所有期限仍保留，不能以class/canonical替代。

本报告仅静态有限 ACK。局部 synthetic SQLite/consumer 测试不等于完整 prepare/commit 实测，预算实验数值不等于物理内存/生产规模限制；最终实际回归原件待根侧完成后另核。
