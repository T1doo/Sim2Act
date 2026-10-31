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

最终冻结字节与结果以本轮证据目录为准。中间已实际完成：原Graph/Frontier及新生命周期反例60通过、零跳过；一次原Cold模型步骤的接收→原五写→完整G1 proof→SQL提交，6次固定Mock、0real、SQLite。该次使用虚拟业务时钟，只验证语义，第二Cold及完整目标未执行，不能称30秒验收。源在导入/兼容修正后需重新绑定冻结垂直验收，不能沿用早期字节。

原普通30秒负例在首次DML前第二次校验拒绝、没有G1；此前76–81秒属于签120的另一选路，不是30秒完整时长或理论下限。本协议为完整数据所有权基础，尚未减少G1依赖检查或解决大型30秒目标。正式PG、新Windows与大型live范围不变；无新费用、凭据、权限或发布。
