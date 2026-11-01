# Graph版本事实索引：完整功能验证，原30秒与净提速仍失败

应用源码 `97f4c0af7932c21cb21b6498b642b1639ab050ca`；本轮匹配基线 `2c54f5fef7918f8cf5364eda651477f47cf10c0d`。两者正常推送开发分支并以官方GitHub ref读回。main、Release、用户电脑、Windows CI和凭据／费用／安全权限均未改。旧安装候选35eaa941完整保留，**没有把这份性能未达标源码生成或签成新版安装交付**。

[源码／执行身份](identity.json) · [工件大小与SHA256清单](artifact-manifest.json) · [配置秘密值扫描范围](privacy-check.json)。应用冻结身份与后续证据提交身份分别记录，清单不包含自身。

## 实质实现与边界

2c将默认结构资格检查迁入一次登记原始期望的C后端：每次仍完整读当前类namespace/MRO、函数code/defaults/kwdefaults、实际别名和copyreg有序项，未知表示回原Python路径。CPython3.12字典版本索引只复用“键全为exact str”的格式证明；不缓存Graph PASS、函数内容或权限。信号前先核支持域及原前置条件，信号后完整重读；guard-first导入在完整声明后才一次登记Source4。真实消费者调用别名纳入见证。新增晚期class替换反例实际复现后，修复C lookup的exact subject门及selector返回后的入口复核，零foreign方法调用。

97在首次**完整**capture后，仅对实际live inputs中、所有键值都由精确不可变scalar/text/bytes/pure tuple构成的原始dict记原版本：capture前后tag相同才启用；tag变／0／非312仍完整遍历，不更新旧期望。字典先参加原正反别名登记，全部不可变后代进入同一全Tree别名库存。每次signal后重查tag，handler异常原样传播；所有callback-capable清理后，再核本次使用的每个tag。Graph、Frontier显式传实际inputs，proof显式传proof.inputs；binding投影和reducer临时森林不启用。动态权限／撤权、owner／epoch／版本、stop／双时钟／最早截止以及原五写和完整独立G1均保留。

两名既有只读reviewer复核代码／生命周期与证据；静态审查不是运行验收。拒绝了“Source binding pin全为pure tuple”的错误前提：真实pin含Owned和可变anchors，原Owner本已opaque，未据此省略anchors。现实现也不声称signal／trace逐事件同序。

## 原30秒，单独负例

两次原TrialCaps都是真实墙钟与单调时钟、6次固定Mock、0真实模型；均无首次DML、无G1、无新typed成果，接收响应及已知用量保留，安全回滚。

| 源码 | Epoch耗时 | 实际耗尽位置 |
| --- | ---: | --- |
| 2c | 29.969873秒 | `cold.check→_base→_check_dynamic→checkpoint`，首次图commit后 |
| 97 | 29.946352秒 | 首次图`commit→_graph_resolve_trial_source→checked→_graph_trial_stage_parent_pin→Graph.check→_check_dynamic→checkpoint` |

因此97不能签成原30秒改善；不能用截断耗时近30推算提速。这里的Graph.commit是图校验方法，并非SQL提交。原件在baseline30／candidate30，观察器同为`63460fa737336465214b4048650eb19c7b897a4c60bb26de378e40f073d60a96`。pytest通过只表示安全负例断言通过，业务目标仍失败。

## 同环境两笔大型signed120：没有净收益

相同原fixture、真实UUID／时钟、固定Mock7次、test_only文件SQLite/WAL、0真实模型，无并发测量。两版详细观察器均为`4e8e38f2f87dc22c24ba0a88f484f79f975b8a101b605c789f3f89afed98c3b9`；97只额外在test前后读诊断计数。观察开销均保留，不能与前一份不同观察器的35成绩签为严格配对，亦非无观察SLA。

| 源码／笔次 | G0至promote | snapshot写入区段 | snapshot总计 | 终态 |
| --- | ---: | ---: | ---: | --- |
| 2c／1 | 35.020995 | 52.887629 | 87.909612 | COMMITTED |
| 2c／2 | 37.787230 | 54.503925 | 92.291693 | COMMITTED |
| 97／1 | 35.738815 | 52.845530 | 88.585218 | COMMITTED |
| 97／2 | 38.375503 | 54.954441 | 93.330577 | COMMITTED |

单位秒；writer区段不是精确SQLite锁获得瞬间，SQL计时与Python exclusive存在重叠，不相加。两笔净差+0.675606／+1.038884秒，不能称端到端提速；一次顺序配对也不足以把小差异全部归因实现或环境。完整图比较实际2c→97：G0 5.7933→5.0815／6.2095→6.0102秒，G1 8.0809→7.0658／8.4425→7.4622秒；局部减少未转化为总收益，完整编码次数833／869／820／853均未下降。原30与此显式120合同路线、时间不能互换。

97计数证明默认真实接线：pre约1981万、post约2320万flat-dict命中，capture全部成功；是整个测试的Graph phase、跨多次publication重叠计数，不是唯一字典数或每笔Epoch统计。约2.65亿logical immutable edges省略量是保守work单位，不是CPU指令、延时或权限证明。

两版本均完成原五写、完整post G1、SQL COMMIT、Run SUCCEEDED。各自保存后首次新解释器只读回读通过，HTTP结果、app输出、typed v1和两条Cold VERIFIED一致；主DB内容不变。WAL从absent变empty，明确physical identity=false，不改签物理文件完全一致。

## 取消、回归和失败原件

97真实G1持锁探针SQLITE_BUSY5且无变更；GET 0.028683秒、cancel POST 0.108049秒。G0 32.482514秒、写入区段3.343863秒后完整回滚，原history／接收行／资源／归档／typed不变，暂留RECONCILING。随后原数据库私有副本用默认Worker收敛CANCELLED，重复cancel 200/CANCELLED，新Store.once=False；只当前Attempt/Operation作状态迁移，正文与用量保留，0新模型尝试，原DB不改。合同仍显式120，不是普通30成绩。

最终相关／最早截止回归310项零失败零跳过；另3项真实Linux POSIX信号边界通过，不与前面重叠套件数累计宣称产品完整。原273、92和18项均是重叠阶段。覆盖完整类型／顺序／别名、撤权／取消／截止、临时投影、scope与重开；310项执行时是最终字节的WIP，之后只提交冻结，不能改写成当时已在97 HEAD运行。

所有中间失败保留：Source4捕获后旧fixture用替换代码模拟decline，改为真实未知copyreg配置并保留原拒绝断言；首次子进程漏PYTHONPATH；监控API准备错误；真实late-class窗口；冷启顺序；热身capsule计数fixture；GC回调实际延后到C返回后的错误同步假设；100μs信号也在C返回后送达的错误注入时点。最终信号把handler放到确实活跃的C capture／中段原reducer，保留原异常identity及晚期数据变更拒绝。没有通过删断言、省检查或扩大时限使业务成功。

三个metadata微测v1更慢、v4近似、v6较快，均为1df7／2c之前的WIP数据，不重签冻结SHA。raw-dict组件同一WIP backend、同样2000 dict、各100次三对，中位12.826→4.315毫秒；它不是旧2c二进制，也不预测真实整链。组件与失败原件均保留。

本轮0真实模型请求，正式PG、大型live、新Windows、任意目标语义及原30可用性仍未验／未通过。保留[旧Linux限制候选](../../../deliverables/limited-graph-current-20261101/README.md)：3,270,375字节，SHA256 `927501b0a87aee143ed152f998073be31631b4104cec642cfe697e8fdd49155b`；实际安装CSV保存／原键／停止／重开范围不扩签为97。卸载只移除所选环境内sim2act，保留工程、导出、日志和共用依赖。
