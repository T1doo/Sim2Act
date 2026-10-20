# 真实纯函数离线剖析：无获批生产优化；修正替身实现

基线 `7da1c2a46b04d3e3e12f6d04acd0539b175a9bc2`。已核环境连接、唯一写入者、干净HEAD和远端一致，原main未动。没有第三个Mock窗口、真实模型、任何transport调用、Store/Worker构造或数据库打开；没有修改产品src、采样调度、预算、事务、租约或鉴权。

## 本次实际剖析范围

实际执行[原脚本](RAW/profile_offline.py)，原样保存[PROFILE.json](RAW/PROFILE.json)及5份原始pstats。使用已保存的完整contract JSON，以固定PBTrialContract只做本地schema构造；40个本地RowMapping含隐藏_data位置与共享别名、6份已存request/response bytes、真实Limits。Binding/CGR是仅填pure input_*所读属性的object.__new__无权限壳，不调用__init__/check/add/producer。完整input_bytes为 **61,657字节**，不是旧579,257字节或真实在途G0完整图。全部prohibited tripwire调用0，未导入任何业务tests fixture。

每任务预热1次，100次无profile wall/process CPU，再100次cProfile。下表是各独立任务100次总时间，范围重叠，**不能相加或外推历史5685次/G0**：

| 真实纯函数范围 | 无profile wall秒 | 无profile process CPU秒 | cProfile总秒 |
| --- | ---: | ---: | ---: |
| 完整 input_key（含全 contract storage、C codec 和 SHA） | 0.022939978 | 0.022937882 | 0.076064997 |
| 完整 contract typed storage | 0.011124489 | 0.011118374 | 0.048598862 |
| 完整 contract raw 复制 | 0.014092587 | 0.014091668 | 0.053460938 |
| 完整两模型 cohort（contract＋Limits） | 0.039194587 | 0.039192738 | 0.167442285 |
| 完整合成 inputs 初次 validator | 0.113069275 | 0.112972714 | 0.271244055 |

原始pstats与JSON的调用数、self/cumulative时间、total_tt逐项一致，独审亦独立只读重算吻合。cProfile的Python调用开销明显，本数据不可用来比较Python与C实现的收益；[Python官方profile文档](https://docs.python.org/3.12/library/profile.html)也区分剖析与基准，并提醒Python/C开销偏差。

## 有证据的定位与候选决策

- 真实input_key的profile显示 `_trial_typed_storage` 100次cum≈0.048902秒，`_cold_graph_bytes`100次cum≈0.023695秒；后者包含实际C Pickler的reducer_override/完整RowMapping及Limits读取。它们与外层input_bytes重叠，不能重复计时。
- 两模型cohort的profile中，`_trial_pure_data`200次cum≈0.058971秒、typed storage200次cum≈0.052609秒、typed_equal400次cum≈0.052568秒。可确定存在反复完整遍历/复制/比较；这些读验证当前具有安全目的，不能据占比直接删除、复用历史结果或改变错误顺序。
- 最小候选“同次roots名单复用”在实施前被独审否决：nested_classes中的from-import之后仍重新读取类名单，导入hook可改变schema绑定，复用旧名单会少一次新鲜读取。该项profile成本也小，不能据插桩比例承诺无插桩收益。**src没有实施此候选**。
- 当前没有获独审批准的生产提速补丁。不重做先前无实质信号的类型分派/前缀分配，或已否决validator/单删SHA；不减少pin、不缓存验证结果、不改变事务一致性与原finite期限。

完整G0仍是上次原证据31.125秒、超过lease约1.109秒；342秒整轮含原journal约60秒节流。本次不是完整G0/SQL/权限profile，不能由合成纯函数结果判断G0已解决。Cold RUNNING/RECEIVED是诊断BaseException保现场，不构成生产漏收尾证据。跨事务/CAS见证及原测试单谓词覆盖缺口未解决，本轮不依赖该方案，未扩大CAS测试或改事务。

## 实施的必要修复及回归

父独审指出旧 `cold_scan_standin.encode` 使用纯Python `pickle._Pickler`，生产基类则为C加速 `pickle.Pickler` 并含reducer_override；旧stand-in的serialize/SHA占比不能用于选择生产优化。旧测量/证据原字节保留，不能拿其数值与本次实际C profile直接对比。

该窄诊断修复先经[方案预审](PLAN.md)后实施：改用公共pickle.Pickler（当前CPython断言等于_pickle.Pickler及生产基类），保留header、协议5、每次fresh完整编码/SHA，明确primitive-only实现标签。实际纯函数profile使用真实生产helper，覆盖其真实reducer；替身自身仍不覆盖自定义reducer、typed或CGR资格。profile精确脚本/原件是执行后复核，不声称该精确脚本在执行前已独审。

[本地回归](STANDIN-UNITS.log)4项通过，含隔离子进程10个primitive/别名/多frame向量与生产完整bytes逐字节一致；Pythonfallback及业务/网络/transport tripwire封闭，子进程10秒上限，父纯测试不导入产品。完整[纯单元](PURE-UNITS.log)43项：39通过、4旧native案例skip；[ruff](RUFF.log)通过。[独立审查](REVIEW.md)另跑同4项并复核profile原件，未重跑profile或任何业务。

[PROFILE-SCOPE.json](PROFILE-SCOPE.json)与[CHECKS.json](CHECKS.json)记录边界、源码hash、命令及旧证据不变。[MANIFEST.json](MANIFEST.json)绑定本目录原件；最终提交及远端/未提交/未推送差异见最终回复。
