# Graph 完整版本生命周期

本协议已接入符合原有资格的默认 Cold Graph，不是独立诊断壳；当前阶段不声称原30秒转正或性能修复完成。W5→G1仍执行原完整重建、授权、写后条件和提交门，30/120预算未改。先前2ad Linux限制候选保留。

## 生产和消费入口、实际迁移顺序

| 入口 | 当前实现 |
| --- | --- |
| `_ColdGraphRead.__init__` | 原 `input_key` 同一次完整 codec 返回实际V2 bytes/key；已知codec才建立独立C Journal及首个Version。未知配置/缺可选API在发行前保留完整旧路径。 |
| `_ColdGraphRead.add` | 先原完整check，验证全部新边且不回指根；强持旧Graph/Frontier版本；只此发布点增加根并产生下一版本。重入导致旧版本变化立即拒绝。 |
| `_NativeCandidate.issued` → `_Frontier.__init__` | 原两事实族已完整核验之后，建立独立投影Journal。Graph和Frontier不共享版本；原调用栈未加wrapper。 |
| `_Frontier.added` | 原future-root/receipt生产者链及更新顺序保持，投影只在这里推进；`values/_refresh`始终是当前读取，不可重设expected。 |
| `input_bytes/input_key` | 保持fresh语义。`_snapshot_values=True`仍返回真实live alias域，供Source和manifest捕获使用；绝不替成历史复制。 |
| Graph／Frontier完整check | 每次原动态门仍执行；fallback新鲜完整codec得到同一次raw/key，与held Version原完整bytes比较，旧期望不从live重建。 |
| `select/select_frontier` | 校准前后仍完整pin及独立fresh比较；State额外持同一Version。命中不是授权，版本变化即拒绝，MISS不可发布或重定基准。 |
| `export_version` | fresh check后输出同一Version的原完整V2 raw/key；Frontier禁止冒充legacy Graph导出。 |
| `_model_settlement_read`／`_ModelSettlementRead.check` | G1仍新建post Graph并全量执行。proof保留完整raw/key及Version强引用，直到原live/settle/tail；不能只比较digest跨版本复用。 |
| Graph.invalidate／Mode.close／Candidate.release | 先通过独立C issuer登记关闭原Journal及Frontier；不得依赖已损坏的Python字段定位issuer。关闭幂等，不重放原callback。 |

## 期望值、身份与原子发布

Version是不可构造/改写的C对象，保存原该次codec输出的exact bytes、原SHA和递增序号；bytes覆盖原V2的字段、类型、顺序、位值、别名及RowMapping隐藏存储，不以相同hash替代完整比较。Scope另绑定Graph/Frontier对象、nonce、根容器、角色、Binding、连接、transaction、scope、epoch、phase、原driver和owner thread。Scope是身份锚点，不是冻结授权或可跨事务携带的PASS。

C issued登记仅持subject/journal弱引用；删除Python句柄、同bytes换Journal、旧版本、死弱Journal、重新mint都不能退回legacy或复活。Journal仅持当前Version；旧版本只因真实holder保留。旧Version仍连带scope/Graph，不能描述为只保留独立bytes；不应无界积累历史。

发布入口核真实固定helper/生产者code、globals、self和同一次`_pin_raw`。编码前强持predecessor；C分配后重新核完整代码角色、scope、closed及predecessor。旧key必须正是当前Version.key，替换前强持旧值；key/expected与journal.current在无Python回调的C段一起更新。错误不能从已变化图产生新“旧基准”。

Graph入口先核C issuer/Source见证，再动态调用新helper。清理入口嵌在不可变Code constants中，不是可覆盖的kwargs/default/module callee；封存先于RAW、结构和Source资格记录，后者捕获封存后的实际code。错误角色时C仍先关闭原issuer；foreign active不被替换触发析构，后续current始终拒绝。

所有C新增入口沿原源码SHA资格和完整源清单；Python Source witness加入新helper、内建角色、Frontier类和原生身份。旧raw-row freezer只在实际RowMapping分支引入运行时，使用一次绑定的原storage函数并核identity/code/default/globals角色；默认prepared编码无新增import回调。三个独立解释器入口顺序已核，避免集合运行掩盖循环导入。

## 验收范围

冻结源码 `4d0b16f2cce1d83363106aa00c05bc969e39ac23` 在 clean worktree 前后核验下完成：相关172项零失败／零跳过，另一次默认Cold模型步骤接收→原五写→完整G1 proof→SQL提交，新事务读回Attempt/Operation均VERIFIED，proof持有的版本与完整V2导出一致。6次固定Mock、0real、独立test_only文件SQLite；该次使用虚拟业务时钟，只验证协议语义，第二Cold及完整目标、首次新进程重开未执行，不能称30秒或真实模型验收。见[源码、完整日志与保留失败](evidence/graph-version-lifecycle-20261031/README.md)。

相关回归初次4失败中，新增跨Graph借用Frontier后的重复撤销已实修，原反例未改。父版也失败的3项fixture按实际边界修正，生产校验未弱化；扩大收集时遗漏的旧fixture导出已恢复。两位独立只读reviewer未发现新增mustfix；相关套件通过不等于全仓库或全产品通过。原Linux候选包哈希保持不变，未把新源码冒充已打包内容。

原普通30秒负例在首次DML前第二次校验拒绝、没有G1；此前76–81秒属于签120的另一选路，不是30秒完整时长或理论下限。本协议为完整数据所有权基础，尚未减少G1依赖检查或解决大型30秒目标。正式PG、新Windows与大型live范围不变；无新费用、凭据、权限或发布。


## 2026-11-01 默认当前版本后端

源码35eaa941以封存C `pin_resolve`完成一次fresh完整代码／模块／alias资格及无分配13锚点/current/issuer复核。创建前可选能力缺失仍走旧完整路径，已发行不得降级。真实清理归属改由C原child和mode/scope/candidate记录决定，分配失败先撤销且不遮原异常；GC覆盖新增引用，死弱child拒绝。原业务回调、完整内容、动态权限/撤权/期限、原子五写和独立完整G1保持。189相关回归、匹配两笔真实保存／首次回读及真实持锁取消已执行；原30失败与signed120效果分开，详见[本轮完整证据](evidence/graph-current-real-clock-20261101/README.md)。

后续97f4c0af将原始dict的版本绑定事实接入Graph／Frontier／proof：首次完整capture前后tag一致且值全深不可变才启用，dict仍参加原正反别名域；每次信号及callback-capable清理后重核使用过的tag。新投影和reducer临时森林保留完整遍历，权限和原W5→G1不复用。310相关／截止回归、真实信号反例及两笔保存／首次回读／持锁取消通过；但整体时间没有净收益，原30仍失败。详见[完整对照与未达标边界](evidence/graph-version-facts-20261101/README.md)，不据局部索引命中扩签性能或安装范围。

4e7b4443先对原30秒失败前缀做函数CPU／墙钟及C子段归因，未做低占比分配复用。原exact dict边在同一次work／depth／entry signal后，仍进行原正反alias登记和完整版本证明；若handler改tag，进入已计work的完整body，不重计或重放。共享证明和最终cleanup后tag复核均保留。313相关／真实信号回归及同规模两笔signed120提交／首开／持锁取消通过，本样本总时85.151／89.237秒；不是原30通过或稳定SLA。完整PB合同族仍可变，现有AppManifest所有权不覆盖它，不能缓存Graph的typed投影。见[归因、实际源码及全部失败](evidence/g0-attribution-edge-20261101/README.md)。
