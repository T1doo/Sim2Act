# 完整图比较热点与已验证的原生候选

冻结源码 `0b67d9c0a77a532725a63966def5db2054c6c95e`。fixture修复基线 `aabc58c454a4f1c9104dacf6e51ad0313e725739` 已推送；原15项失败的实际bee40/f41对照、逐项修复及17项组件回归见 `../continuation-fixtures-20261030/`。本轮继续核真实大型Cold，未缩减输入、完整校验、权限/撤权、版本、租约或最终原子写组。

## 实测热点，避免按假设改代码

`profile-run.json`：aabc源码，04:52:34–05:01:51 UTC，退出0，原大型正常流程全部断言通过，7次固定Mock，0真实调用。CPython局部函数事件只记录目标Cold epoch，callee、SQL、业务时钟不替换；callback显式注销，最终pending_frames=0。

两次G1合计的观测值：

| 函数 | inclusive秒 | 扣除其他观测target子调用后的秒 |
| --- | --- | --- |
| structure.select | 65.130 | 53.635 |
| typed.values | 13.832 | 13.832 |
| graph.input_bytes | 18.838 | 11.992 |
| graph.typed_parameters | 9.159 | 9.159 |
| graph.commit | 63.783 | 8.750 |
| typed.storage | 6.886 | 6.886 |
| schema.current | 2.013 | 2.013 |

这些是带监控的函数分解，inclusive相互重叠，不能相加；exclusive只扣观测target，不是真正逐指令self CPU。结构比较确为主要开销，但它仍承担完整当前内容检查，不能把53.635秒当作可直接删除的成本。schema仅约2秒，故未扩schema原生实现。

另按实际代码排除了一条假设：当前 `_trial_typed_guard.checked()`仅parent→outer cohort，不存在第二parent；default G1已有base/seed的late pin合并。相邻produced→pin跨cohort扩展/发布和不同模型集合，没有通用安全跳过条件。本轮没有按错误“2合1”假设删检查或添加复杂资格系统。

## 实际C修改及身份

只改变完整比较内部的重复工作：若当前节点就是捕获树强持的original，节点序号已知，仍先验证反向别名assigned，再直接登记本次引用，避免一次重复指针hash查找及临时INCREF/DECREF。clone和其他original节点仍走原映射；cleanup只释放本次拥有的引用。exact不可变int/float同对象才直接值相等，其余仍走原位模式/范围检查。

**dict/list/tuple/RowMapping/Limits及marker的孩子或reducer仍每次完整遍历**，对象身份不充当可变内容PASS。每次Compare独立分配工作区，未缓存授权、内容结论或跨交易Graph；原信号检查和子项临时引用保护保留。原两个区段的结算checkpoint数仍19175/19748。

旧C与二进制已冻结保全，身份见 `baseline-native-identity.json`。默认clang缺失时，可选扩展构建返回0却未重建；日志保留，嵌入SOURCE_SHA核对失败，因此未当成功。使用**已有**GCC14重建后实核：

- C源码SHA-256：`bcd95662169e4e92eefd6aa710971b95d5e94b6fc7534c6e7cb4bd56ba296b0c`
- Linux二进制SHA-256：`10f8c1aa9eb8ca7794344dd471bd4685eb207a06d09a200eadf03c62819344de`
- raw_snapshot二进制未变。
- 原144项资格校验通过，新pin `4a8942133c459844efd713868081c2d245e306ec7e52852f7c693d015c5958a7`。

未安装编译器或依赖、未改系统配置。新C必须在Windows重新构建并核嵌入源码身份；旧Windows扩展不能沿用为本候选性能证据。

## 正确性回归与失败原件

39项既有完整结构/别名、proof输入及原路径fallback回归通过；新增6项可变别名/混合original-clone、原地变更、引用释放及reducer异常回归通过；另54项continuation、元数据资格和纯段保护通过。各批日志/XML分别保留，不以合并数量代替下面的大型业务验证。

旧/新二进制与原canonical pickle做5832组差分，均一致；两版本SIGALRM异常退出后引用计数恢复、capsule可再次使用。交替小基准用真实controller的**结果JSON**，不是runtime Graph，median ratio约0.923且有噪声，不能替代整链或推导因果收益。初次新增Limits用例误用无参构造，在所需字段缺失处失败；修正fixture显式六项限额，未修改生产类型检查，该失败日志/XML保留。

## 同一大型输入的真实闭环

所有案例保持同一冻结源码/二进制，真实时钟、test_only文件SQLite/WAL、固定Mock；四个独立fixture合计25次Mock、0真实调用。没有业务延时或简化图。正常测量无函数监控。

| Cold结算 | 整个原子区段 | 完整G0 | 首次DML至关闭清理的写锁时间上界 | 原120秒合同余量 |
| --- | --- | --- | --- | --- |
| 第一次 | 94.319535秒 | 38.139683秒 | 56.178896秒 | 25.678408秒 |
| 第二次 | 102.511645秒 | 42.877256秒 | 59.633861秒 | 17.486988秒 |

原全部正常流程断言通过，结果保存成功。与前一无监控f58的写锁上界62.766485/59.839411秒比较，第一次较低、第二次近似；仅此运行不足以排除负载差异，**不声称稳定显著净收益，更不声称原30秒目标通过**。写锁值为上界，含原五写、完整G1、提交和尾部清理，不能叫纯G1耗时。

| 同版实际动作 | 真实响应/提交时间 | 完整终态 |
| --- | --- | --- |
| G0中loopback HTTP metadata读取 | 115.735ms，HTTP200 | RUNNING、content_access=false |
| 原cancel命令 | 69.138ms，HTTP200 | RECONCILING；G0约3.990秒、首次DML前回滚 |
| 另一连接改实际输入content | 11.629ms，在G0开放时提交 | 原G0约33.473秒后旧快照升级失败，WAITING_RESOURCE |
| 另一连接撤销实际resource.read | 21.918ms，在G0开放时提交 | 原G0约34.111秒后旧快照升级失败，WAITING_RESOURCE |

三条异常路径都保留RECEIVED/DISPATCHED、原typed历史及归档，无NS_SETTLED/NS_REJECTED或新成果。取消额外核全部资源、既有尝试逐行不变。修改/撤权失败DML的约0.00026秒只代表升级尝试，不代表取得写锁。SQL撤权不是UI撤权验收，G0读取旧快照继续内部计算后拒绝提交，不冒称即时观察新权限。

四条真实起止/退出0：05:19:25–05:28:28、05:30:08–05:35:33、05:35:33–05:41:26、05:41:26–05:47:21 UTC。完整流程、观察/取消、并发变化和回滚原件均单列，所有测量进程已退出。

## 新进程重开与WAL辅助检查

`reopen.json`来自独立新进程mode=ro：Cold SUCCEEDED、唯一成果v1、typed/output与已保存HTTP一致，Cold两attempt VERIFIED，整库3生成RECEIVED＋4执行VERIFIED。主DB、WAL和逻辑全表快照分别记录；最终这次实测empty WAL→empty WAL、主DB字节不变，没有依赖空文件豁免。

初次辅助脚本在严格 `wal_after==wal_before` 处AssertionError，其pre值当时未保存，不能倒推该次变化的确切原因。未对原数据库作修复或删除。独立SQLite backup副本实际复现：mode=ro可从无WAL创建0字节WAL，主DB哈希不变，见 `empty-wal-lifecycle.json`。辅助检查因此只新增“None↔空WAL且主DB不变”这一窄条件，**非空WAL变化仍失败**。这修正文件生命周期假设，不放宽业务或生产校验；主DB单独哈希仍不能代表任意运行中WAL状态。

## 剩余真实边界

G1写后区段仍约56–60秒；完整原子事务仍约94–103秒。进一步缩短需要拥有明确数据所有权的预期写后视图/完整依赖计划及新鲜提交复核，不能把实际VERIFIED行、operation/事件及动态验证搬到提交后，也不能直接拿旧Graph/PASS放行。本轮未伪造这份尚缺的等价证明。

新模式Windows/EXE/WebView2、真实模型、正式PG和像素未验。没有使用用户电脑、第四次CI、main、Release、部署或新凭据/费用/安全权限；506秒Windows CI预算仍保留。独立只读审查见 `readonly-review.json`。公开材料仅选定合成日志/摘要/XML/脚本，不上传DB或模型交换原包；已扫描配置秘密值及常见秘密格式。
