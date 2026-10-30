# Post resolved archive：首个完整不可变事实族

生产源码 `f6c5e688584d1d9bfb649a7a3bc88074b1250196`，基线 `99c7e2749638ce7751ed8dbf362a5cadff7dff7e`。这是 post resolved archive 的生产者→全部默认消费者所有权迁移；不声称整个 source/accounted/journal/model cohort 已迁移，也不声称性能或产品整体验收完成。没有继续修改 C 比较器。

## 事实族与原子边界

`natural_source_archives._graph_resolve_trial_source` 在 post 的首次返回前，将全部18个receipt字段、两个完整7字段proof、四份原始请求/响应bytes捕获为 exact tuple packet。固定有界二进制元数据记录 dict/list/tuple 类型、完整插入顺序及容器/叶别名；全部原 str/bytes 作为不可变carrier强持，因此与未迁移source chains/NS reads的原叶别名仍进入完整graph pin。packet不持有旧receipt/proof/list、RowMapping、Pydantic模型或Graph/权限/PASS。元数据保存布局/引用及整数、布尔值，全部原str/bytes在同一个pin里，不是只保留digest。

捕获节点/边/深度/叶字节/metadata有界；schema未知字段或类型不能丢弃。仅真实Capacity可在任何packet发布前保留原完整旧路径。Capacity本身、codec、View、producer和consumer函数/默认参数/类namespace/MRO均有当前资格，异常类不从动态名称接收。没有启用`_cold_settlement_owned`实验。

生产者立即把同一packet登记为`cold-trial:owned-resolved-archive`；默认archive join一次读取metadata为深tuple只读view，逐项执行原完整Slot/Identity/Outcome、顺序、原始bytes及source join。每次原动态/完整图/typed guard之后再核view及callee资格，回调不能更换解码语义后继续消费。runtime graph output保存同一packet，身份检查以KEY存在为准，替换成None/legacy/坏tag或不同output均拒绝。没有在验证链解冻成dict。

非graph、pre及已有HTTP/controlled生产者保留旧`ResolvedSourceArchive`接口。`cold_accounted._archive_chain`、旧`_archive_chain_from_facts`、native `_resolved_shape/_archive_native`的实验消费路径明确拒绝新packet，不留下未迁移dict接口。

所有未迁移输入继续原完整graph/typed检查；权限/撤权、stop、Run版本/fence、owner/epoch和双时钟仍在原边界检查。五写、完整postconditions与最终SQL commit仍原子。30秒是writer admission/首次DML的原上限，120秒SQLite settlement覆盖G0+G1；即使未来某次G1低于30秒，也不能据此称恢复原30秒完整租约。本轮二者都没有扩大。

## 已完成正确性证据

最终冻结回归89项通过59.58秒；145文件软件资格pin `a0ea4d6cda488e68c278977229119bcf5b13b2aebc26cffcc77ce989bd41ef8a` 在独立新解释器通过。具体价值是：实际合成SQLite完整resolver及原archive join和旧接口逐字段对照、生产者原可变alias修改隔离、内部alias分裂/字典顺序及跨族bytes alias变化可检测、损坏metadata/cycle/carrier夹带拒绝、已发布packet不能降级替换、未知decoder/defaults/View/join/分类器/Capacity代码拒绝且未知回调不执行、原guard回调修改View后仍在访问前拒绝、未迁移数据变异/事务失效/原interval stop仍拒绝、实际SQL撤权后原GRANT_REVOKED保持。

fixture使用之前归档的项目合成响应与新的SQLite，不运行Worker/model/transport；这不是完整Worker整链，更不是实服务/PG/Windows/语义验收。完整大型运行单列。

## 公平同叶表示测量

同一实际SQLite resolver输出，测试端只在最终独立展示边界重建旧形状，使用同一批原始不可变叶和同一别名关系，将两种表示嵌入同一个未迁移完整图。没有在业务验证链thaw。

| 整图序列化 | 原表示 | 新表示 |
| --- | ---: | ---: |
| 完整编码字节 | 205659 | 206012 |
| dict构造节点 | 1185 | 1181 |
| list构造节点 | 505 | 504 |
| tuple opcodes | 69 | 69 |

新族metadata403字节，48个不可变叶。在该同叶序列化表示对照中少了4个dict和1个list构造节点，但完整编码**增加353字节**，没有压缩或整链收益结论。整图检查/编码调用没有凭此减少，未迁移typed cohort仍保留。此结果决定不能把该小族作为解决约7700次全图比较/3325 typed/1200编码的完成证明。

最初测量误用另一pre segment重新读取的旧叶，会把对象共享差异算成约7KB收益；该数字明确作废并保留原件。修为同批原叶/别名后得到上表，不用前一个有利数字。原解析助手还曾把项目pickle envelope当opcode失败，业务对照/join已过但整项测试仍是失败；修助手前缀后重跑通过，原失败只保存hash/本地路径摘要，因为完整日志含合成原始内容，不上传raw图。SQL-only fixture最初没有真实settlement会建立的有限interval，stop负例未抛错；只补同120秒双时钟fixture前提，生产checkpoint未改，原失败记录保留。

## 同一大型完整链终态

冻结f6c5源码，09:45:04–09:54:30 UTC，exit0，7次固定Mock、0次真实模型，文件SQLite WAL，真实业务时钟。只安装被动return计数，不替换callee、SQL、数据或业务时间，也没有额外重复图比较。源码最终仍f6c5、working tree空。

| 实际区段 | 第一笔 | 第二笔 |
| --- | ---: | ---: |
| 完整结算 | 97.415693秒 | 118.616410秒 |
| G0读快照 | 39.094705秒 | 43.860274秒 |
| 首次DML发出到清理上界 | 58.319883秒 | 74.755344秒 |
| 原120秒合同余量 | 22.582257秒 | **1.382032秒** |
| 结局 | COMMITTED | COMMITTED |

writer计时是事件上界，不是VFS精确持锁回调；监测开销计入时间，未与历史不同监测轮次建立受控整链加速比较。第二笔只有1.38秒余量，风险明显，不能作为30秒完成或稳定交付证明，不能以这次刚好通过替代架构修复。

实际每笔G1 archive capture/read/bound各1次，metadata403字节、48叶，证明新生产者和consumer确实进入默认链。原typed.values仍各3325次；native成功比较7679/7764次，累计边work约5.919/6.036亿，根本规模仍在。graph control检查19176/19749，较原样本各多1次，不是少校验。新增pin还产生校准变化，不能把native成功次数小降当全部工作下降。

G1 input_bytes实际返回byte总量798157260/855069282字节，较前轮同类原样本792280670/849140180增长。**本轮探针将dict投影返回和bytes编码返回的调用数混记为9041/9189；没有独立编码次数或投影次数，不推导或冒称编码频率下降。**这两项在large-count-summary.json中明确为null。原始probe和计数完整保留；后续分开计数探针另存、标记未运行，不拿修好的脚本冒充本次执行，也不为补一个数字盲发另一轮模型请求。

独立新解释器只读重开绑定本次f6c5/exit0，唯一v1、SUCCEEDED、HTTP保存响应=应用输出=typed结果；Source/Cold四个VERIFIED及generation三个RECEIVED保持，main数据库前后hash一致。WAL由不存在变为空文件，按原已审None/empty生命周期规则记录；不冒称WAL物理字节身份完全不变。见reopen.json，未修复或迁移DB。

本轮没有另跑大型HTTP取消/并发修改/撤权。当前归档族的alias/stop/事务失效/真实SQL撤权/未知代码回调拒绝由前述最终89项覆盖，历史完整大图取消/并发证据仍属其原版本，不能挪成f6c5新增验收。

## 下一结构缺口

完整source/generate accounted仍含原Run/Attempt、Slot/Capture、parsed、BodyArchive、hidden RowMapping storage及模型fields_set等跨族aliases；不能把当前仅适合fixed archive schema的packet直接套过去，也不能只在_prepare结束后追加捕获。下一族必须从首次producer输出开始迁移全部consumer，并保留完整raw/typed/hidden-storage及跨族别名，完成后才能从重复pin中移除旧对象。G0完整不可变事实与五写预计postimage、G1完整实际依赖/ABA/rowcount/events/postconditions等价证明尚未实现；未知schema/trigger/callback继续原路径或拒绝，不能先删post检查。

## 交接范围

免费Intern授权保持有效，没有再次询问费用。本轮真实模型调用0；正式PG及principal/project/trial/approval选择仍与[正式连接说明](../../ProductionConnection.md)相同。Windows新源码/原生库与目标机、PG/live及自然语义未验。main、Release、部署、用户电脑未操作，第四Windows CI未发起，506秒预算保留。

独立只读审查的已修问题及整链/重开范围见readonly-review.json。公开前对全部选定文件及解压后的gzip扫描当前两枚已注入secret值及private-key标记，见publication-scan.json；该有限扫描不冒称通用脱敏证明。SHA256SUMS.json绑定每个选定原件，原DB/raw模型交换及含原始图的失败日志未公开、未删除。
