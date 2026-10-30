# Cold完整图比较：实际规模、逐字段等价与有界优化

产品源码 `4b2dc3cc0e06eae8e79c837562a1c55082706f07` 已正常推送开发分支；基线 `859d819a005bb06d55ff523fc6f36ab1319ad421`。本轮没有改 main、120秒合同、原30秒目标、权限/撤权/版本检查或最终五写原子性。**30秒仍未达到，也没有稳定整链提速结论。**

## 真正改动

C比较器仅内联当前一次完整比较中已经登记的节点及确定不可变原始叶边。每次调用仍独立分配、完整遍历当前结构，保留原递归walker、类型/顺序/值/别名双向约束、reducer、异常清理和原signal/work/depth检查。RowMapping、Limits和quoted_name仍走原完整kind/reducer路径；信号之后重新读取assigned，不依据可被信号改变的父引用计数。没有跨调用、SQL、callback、epoch或事务复用PASS，也没有用hash相等代替完整比对。原不可变Tree已经按scope捕获，当前可变对象仍需每次复核。

实际Linux扩展源码hash与C文件一致，144项精确软件资格更新，pin及二进制身份见source-identity.json。独立同编译参数的新旧C differential覆盖别名分裂/合并、叶值/类型、marker、reducer中的__class__变化、异常及重入；真实POSIX信号修改后续alias、在native调用内抛错/同cap重入均保留原结果及引用清理，深度/节点/边上界一致。差异检查29440组、105项生产回归通过；这些支持实现正确性，不替代下面整链。Windows新C未编译或验收。

拒绝的方向：通用refcount==2快捷方式可能被signal改变父引用而漏掉alias冲突，没有合入；仅kind dispatch的重建微基准收益约2%，也没有合入。最初安装C时与已审原件差一个空行，hash资格正确失败，修正精确字节并重编后才验收，失败记录单列保留。

## 实际大型输入热点

基线859d实际完整控制器，07:37:10–07:46:43 UTC，exit0，7次固定Mock、0真实调用，真实时钟、文件SQLite WAL。诊断读取实际capsule/current input，仅保存结构计数；每种shape额外做一次完整比较，开销计入业务时钟。完整原始结构计数见actual-baseline/actual-graph-shapes.json.gz，可按actual-hotspot-table.json复核。

| G1实际统计 | 第一笔 | 第二笔 |
| --- | ---: | ---: |
| 匹配比较次数 / shape数 | 7681 / 173 | 7766 / 182 |
| 单次节点最小–最大 | 3543–52216 | 3569–52759 |
| 单次边最小–最大 | 6556–113732 | 6601–114704 |
| 调用加权平均节点 / 边 | 38959 / 77091 | 39281 / 77748 |
| 累计逻辑work | 592145680 | 603795074 |
| 两个零数组累计申请字节 | 4787911408 | 4880933952 |
| changed map累计申请字节 | 338575360 | 342753280 |
| 平均原始指针节点 / 非原指针memo节点（含reducer表示） | 32164 / 697 | 32420 / 699 |
| 原始map平均探测/查找 | 1.648 | 1.642 |
| changed map平均探测/查找 | 1.458 | 1.453 |
| input_bytes完整编码次数 / 产出字节 | 1182 / 792280670 | 1236 / 849140180 |

map本样本没有退化成二次探测；单次比较预期复杂度为O(V+E+B+reducer实际工作量)，B含文本/字节内容比较，整体是各次全图工作量之和。随图增长反复全量扫描可造成很大累计成本，不把本次平均探测当任意输入最坏界。累计申请字节不是峰值驻留内存，也没有独立测出allocator所占秒数。input_bytes只统计该方法返回，不涵盖其他直接codec路径。native计时包含Python reducer，父子计时不能相加。

旧9523同一原输入的阶段证据见[前轮热点](../cloud-cold-deadline-20261030/README.md)：writer上界52.821/54.959秒，native比较17.726/19.053秒；**仅在其他耗时不变的假设下**，把native比较耗时设为零仍为35.095/35.905秒。因此本项常数优化不足以承诺30秒；这不是不可变IR唯一/绝对最小的证明，也不是机器性能下界。

## 同真实输入新旧配对，保留失败

4b实际capsule和当前input在每种G1 shape以交替顺序配对，710对均一致。第一笔call加权样本ratio0.92743（约7.3%），第二笔部分ratio0.89144（约10.9%）。额外配对/诊断实测4.397秒，Python观察开销另未分离；这是局部样本，不是整链净收益。重建合成pickle微基准约17%收益，别名与实际图不同，不能冒充上述实际对照。未公开含内容的pickle/DB/模型原始交换。

该带探针整链第一笔103.924秒提交（G0 38.940，writer64.983）；第二笔120.012秒回滚（G0 57.044，writer62.967）。原始异常和回退异常都是BUDGET_EXHAUSTED，未观察到被其遮住的其他异常；完整原失败日志/XML/traceback保留在paired目录。不能将此失败归零或断言全部由探针造成。

## 无额外剖析完整保存与重开

4b冻结字节，08:42:07–08:51:20 UTC，原完整控制器全部断言通过，exit0，7次固定Mock、0真实模型。没有替换业务callee、SQL或时钟，SQLite原120秒合同不变。

| 实际区段 | 第一笔 | 第二笔 |
| --- | ---: | ---: |
| 完整结算 | 92.911678秒 | 111.245202秒 |
| G0读快照 | 34.201495秒 | 50.004693秒 |
| 首次DML发出到清理上界 | 58.709071秒 | 61.239672秒 |
| 原合同余量 | 27.086674秒 | 8.753319秒 |
| 结局 | COMMITTED | COMMITTED |

writer为首次DML发出到事务清理的上界，不是VFS精确锁回调。此前9523带不同监测的52.821/54.959秒不能与本次作为受控整体提速对照；本轮第二笔仍只有8.75秒余量，保留性能风险，不反复同样盲跑。

独立新解释器只读重开，严格绑定4b和exit0元数据，唯一v1、SUCCEEDED、HTTP保存响应=应用输出=typed结果；7个attempt中3个generation RECEIVED、4个Source/Cold VERIFIED。main前后字节完全不变，WAL由不存在变为正常空文件，按原已审None/empty规则记录而非宣称物理文件完全相同；身份核验见reopen.json。不修复/迁移数据库。已审前轮重开helper只替换source SHA，调用传齐参数。

## 同一大型输入G1真正持锁时取消

同冻结4b串行验收，08:51:20–08:57:36 UTC，exit0，6次固定Mock、0真实调用。完整G0自然结束47.895秒，G1自然运行3.133秒后，独立timeout=0连接BEGIN IMMEDIATE精确得到SQLITE_BUSY(5)，探针未写数据，随后状态读取及取消前均核同一首个epoch仍在G1。

owner真实loopback HTTP状态读取190.681ms，取消283.249ms，均HTTP200；完整区段52.156秒、首次DML到清理上界4.260092秒，ROLLED_BACK。最终RECONCILING，原attempt为RECEIVED、operation仍DISPATCHED，五条既有attempt、target完整row、typed history、所有resource和归档行完全不变，无NS_SETTLED/NS_REJECTED、无新typed或部分VERIFIED残留。未逐DML记录取消前已执行条数，不根据G1时间推断五写必已全部执行，也不承诺任意同步C/SQL段即时中断。详见g1-cancel原件。

本轮没有重跑大型材料修改/撤权场景；前轮9523实际并发SQL提交及旧快照升级拒绝证据仍单独保留，105项当前回归检查这些生产边界。本轮四次大型运行合计27次固定Mock、0真实调用；包含一个明确失败的配对完整链，不把它计为通过。

## 下一结构边界及保留条件

本轮已落地上述安全常数优化；没有启用不完整的owned实验。要减少重复全图工作，需要先把待豁免的纯区段数据收拢到无可变别名外泄的真正不可变IR，再迁移并证明**全部消费者**只读消费它，包括原始storage/raw dict/hidden RowMapping aliases、完整模型字段及序列化类型/顺序。现有Python frozen dataclass/model copy不足以构成这个所有权证明。_cold_settlement_owned虽有实验接线，默认链没有安装完整consumer迁移；其捕获时点也没有消除之前生产重构成本，不能直接启用来豁免guard。

提交前/提交中仍独立验证完整SQL依赖和ABA、Run版本/fence、权限/撤权、owner、stop及原双时钟期限，变化则原完整路径或明确失败。五写预计postimage必须与实际完整postconditions等价，并保留最终原子性；未知callback、trigger、schema必须保守回退。不能传递旧Graph/authority/PASS，不跨事务复用授权或只比digest。该迁移尚未实现/验收，本轮不假称30秒闭合。

## 范围

本轮仅合成输入Mock+文件SQLite，模型真实调用0。已有免费Intern授权仍有效，token只核注入布尔；正式PG连接及principal/project/trial/approval等具体配置边界见[正式连接说明](../../ProductionConnection.md)。不把缺正式输入写成缺费用授权。UI和桌面宿主未改，Windows目标机、新C原生库、PG/live/自然语义/整体产品验收未完成。第四Windows CI未启动，506秒保留；没有访问用户电脑、main、Release或部署。

独立只读审查核过实现、源/二进制身份、正常保存/重开及本轮G1取消原件，修正两处统计措辞后无证据交接阻塞，见readonly-review.json。历史诊断脚本保留固定baseline及scratch路径，不能作为当前源码的安装入口；重建微基准依赖未公开合成pickle，不冒充公开自包含复现。当前生产回归位于tests/test_graph_edge_compare.py等已绑定冻结源码。公开文件经当前两枚实际注入secret值及private-key标记扫描，gzip逐个解压检查；具体范围和hash见publication-scan.json、SHA256SUMS.json，不把有限扫描当通用脱敏证明。

将扫描器源码加入清单后，第一次扫描命中了该脚本自身的完整PEM规则字面值（非实际密钥），原FAIL记录保留initial-scanner-self-marker.json。把同一检测规则按两段构造后对所有文件重扫，没有排除该脚本或放宽规则。
