# PB 默认所有权迁移与限制候选

本轮完成生产接线和功能验收，**没有证明整链性能改善，原30秒大型目标仍失败**。产品源码 `3c0f1ee4d5200ae500756bb7998fbaa86fdc8ae4`；候选源码 `5af351804a33171ca06b8136c56047cb677265b3` 仅额外修诊断和测试，二者 `src` 树同为 `f48e290521339aeb800ff977ad84f746fa0f7d5d`。证据提交不冒充验收源码。旧35e限制包保留。

## 30秒的准确含义

`config.py:23` 的默认 `lease_seconds=30` 是后台执行者租约；`natural_live_admission.TrialCaps.lease_seconds` 为 `Literal[30]`。`db.Store.claim` 持久化领取时间加租期；`guard` 拒绝过期／旧fence，`heartbeat` 只续仍有效且同拥有者的租约，并保护提交尾窗。

`model_settlement.original_interval` 在已接收模型响应之后、同步续租之前记录墙钟和单调钟，取得实际已提交租约后，以其、Run期限和原操作期限的最早值限制普通结果校验到最终提交。续租等待也消耗窗口，不允许过期后复活。G0、首次写、五写、完整G1及SQL提交共享剩余窗口。SQLite snapshot promote另有至多30秒的writer排队／首次DML边界，并不能为G1重开一个30秒预算。

这是内部有效性／并发安全协议，不是模型回答时限或整个产品的30秒响应承诺。显式签署的 `SQLiteSettlementCaps` 120秒是另一合同，不升级普通TrialCaps。大型原30失败会拒绝新成果，保留已接收响应、已知用量和旧历史；不会伪装完成或自动付费重试。小型CSV及有限逐字文本流程独立验收、交付。

## 生产者至消费者覆盖

| 边界 | 实际默认接线及仍执行的核验 |
| --- | --- |
| 首次生产 | `ProductionTrialBinding.__post_init__` 先原 `_checked_trial_contract`，再 `publish`；PB完整27类模型域与原canonical dump共同进入深不可变Owner；非PB／缺可选扩展保留原路径。 |
| 所有者／版本 | `_owned_pb_contract` 固定callee和schema；原构造帧私有checked来源、weak Binding、approval/account/fingerprint/version及Owner/ref身份逐次核对。pending和completed注册分离；重入不能覆盖已完成绑定，失败只撤自己的pending。 |
| 数据完整性 | 保留完整字段／类型／顺序／alias、模型隐藏存储及原JSON／fingerprint；导出为独立副本。Recipe、Step、FieldSource保留模型身份，字段ref不误派发为View方法；exclude_none只省模型字段，普通dict原值保留。 |
| binding／source／evidence／policy | `spec_production`、`production_evidence`、`production_trial_policy`、`pa_trial_dispatch`、sender继续原账户、软件、批准、当前状态检查；不可变数据不承载许可或PASS。 |
| typed／Graph／proof | `_graph_trial_produced_legacy` 和 `_trial_typed_hold` 使用同Owner canonical View，原三处parent guard保留；非PB mutable cohort仍完整扫描。`_ColdTrialGraph._dump` 只在PB图内返回同Owner View，Manifest顺序和返回前base检查保留；SQL JSON协议未改。 |
| caps／deadline／settlement | `natural_trial_budget`、`model_settlement` 用显式schema分类区分普通30与显式120；不伪装Pydantic类型、不扩大租约、保留最早截止。 |
| archive／runtime／app／恢复 | Source archive、PB提取Recipe、runtime／apps／worker／cold_accounted消费者接收所有权表示；数据库仍存原JSON，新进程原parser生成新checked／Owner，不复用旧Graph或授权。 |

原17类Source域保持独立。所有Graph／Source动态权限、撤权、版本／owner／epoch、stop、回调和完整W5→G1仍执行。原生Binding READ只检查当前不可变schema和Binding边界；install/make及Python入口仍执行完整固定来源核验，不复用授权结果。

只读独审发现并推动修复了构造checked来源、外来dict key、重入注册、退休字段析构回调、嵌套类型冒充及admission canonical View问题。末次接线独审未发现新增阻断。确定触发的真实析构回调和LINE重入已验；未命中的自动GC分配窗口实验保留为未复现，不冒称覆盖全部GC时序。

## 大型真实墙钟：功能通过，性能未改善

同fixture、同详细观察器 `4e8e38f2f87dc22c24ba0a88f484f79f975b8a101b605c789f3f89afed98c3b9`、无并发测量；固定Mock／test_only文件SQLite/WAL。单位秒。writer为snapshot promote后区段，**不冒充精确锁获得瞬间**。

| 源码／结算笔 | G0 read | writer区段 | 总计 | 结果 |
| --- | ---: | ---: | ---: | --- |
| 配对基线4e7／1 | 34.115723 | 51.034718 | 85.151420 | COMMITTED |
| 配对基线4e7／2 | 35.219780 | 54.017114 | 89.237499 | COMMITTED |
| 本轮3c／1 | 36.458948 | 53.115493 | 89.575375 | COMMITTED |
| 本轮3c／2 | 39.069815 | 52.763406 | 91.833758 | COMMITTED |

本轮同一个Cold Run有两笔模型结算事务，7次固定Mock、0真实调用，原完整G1、首UPDATE rowcount1及实际SQL提交均执行。整体Run SUCCEEDED、结果v1。首次新解释器只读回读确认HTTP／app／typed结果相同，两Cold VERIFIED，主DB内容不变；WAL absent→empty明确不是物理身份完全相同，非空WAL仍要求精确字节身份。

较基线总计慢4.423955／2.596258秒。四阶段完整编码次数仍833／820／869／853，编码字节均增加；不能称减少编码或净提速。投影返回数不等于深投影次数。观察器未拆分PB owner资格、legacy深投影、native Binding READ，不能据总时间臆断可消除比例；完整图比较仍为已计时互斥项最大成本。没有为本轮再叠加未证有益的缓存或放宽预算。

早期5b真实大样本在G0 9.717732秒回滚，尚无首次DML／G1；原因是PB canonical View被错误转为dict。3c修复后才重跑成功。失败原文在 `signed120-5b412287/`，未抹除。

## 原30秒负例与取消

原30同大型输入，6Mock／0real，在G0约29.958570秒耗尽。首次DML未尝试，G1未执行，0typed成果，最终Run FAILED、Attempt／Operation REJECTED_KNOWN，原响应与已知1000 tokens保留。原诊断随后因旧 `type(caps)` 断言退出1；5af修正为精确schema分类并通过18项回归。没有重跑业务或将原退出改为0；只读原DB的后验负例核对通过，详见 `pb-owned-original30-saved-negative-validation-20261101.json`。

持锁取消为同大型fixture、显式120合同、6Mock／0real：独立写探针实际SQLITE_BUSY5，未改数据；GET状态0.054579秒，取消POST0.126897秒。G0 32.755768、writer3.663037、总36.420116秒，实际G1中断并回滚；已接收行、旧历史、资源、归档和typed均不变。此时真实中间态RECONCILING／RECEIVED未改写成CANCELLED。

随后原DB私有副本调用默认 `Worker.once` 收敛CANCELLED；重复cancel为200/CANCELLED，第二个全新Store.once=False，0新模型attempt。仅目标Attempt／Operation状态转REJECTED_KNOWN，正文／用量和所有非目标行保留。未修改时钟／租约；报告 `lease_expired_at_start` 实际在末尾计算，不可用来证明精确起点租约。

## 限制Linux包与已验证使用范围

包：`deliverables/limited-pb-owned-20261101/Sim2Act-local-candidate-5af351804a33.zip`，3,416,609字节，SHA256 `7c80f29c1e107430dd29a43740048c3f4011e06e38444ef1d4743a88c7e94af4`。wheel SHA256 `0ce650f483d6622a8a5635176bdb0378f7741035ffec70f81af8166543c73528`。其源标为5af，不冒充后续证据HEAD。

GCC从clean Git blobs离线构建，四原生扩展必须齐全；隔离新venv安装，已有锁定依赖由简单pth提供，未验干净机器下载依赖。离开源码目录以 `-I -B` 加载包内CLI和四扩展，逐一比对wheel内hash；32项包内PB回归通过。构建产生的新二进制与工作区旧构建hash不同，**完整大型链未在这个wheel二进制上重跑**，只签源一致及安装后CSV／32项覆盖。

实际用户入口验证：默认不启用模型，CSV `item,amount\nA,10\nB,20\n` →草案→显式批准发布→实例→amount求和30/v1；同键复用同Run。两次SIGINT均STOPPED／clean／exit0，首次新进程重开结果一致；自由目标明确FAILED/UNSUPPORTED_CAPABILITY。新测试venv卸载实测只移除此环境应用／元数据／命令，工程文件字节及共享依赖源不变，数据保留。

已有真实Intern“单份TXT／MD逐字保存”能力证据绑定fc978源码：实际仅两行合成文本、两次真实请求并保存重开；本轮新包未重做live验收。协议最多4096 UTF8字节不等于已测所有4096字节输入；自由目标无通用语义完成保证。正式PG／大型live／新版Windows未验，无新凭据或费用。安装启动见包内 `docs/LimitedTextCandidate.md`，每次采用READY URL；普通CLI随机端口不冒充桌面稳定origin。

344项核心回归绑定5b；34项admission最终回归绑定3c；18项诊断回归绑定5af；32项安装后PB回归绑定5af新wheel。均0失败0跳过，但不能合计为同一精确字节全产品验收。历史失败和测试契约对照另保留；不将旧SyntheticContract.caps=dict、旧类型AST或未命中GC harness称本轮产品通过。

`identity.json`、`artifact-manifest.json` 和 `privacy-check.json` 记录身份与扫描范围。仅合成项目证据，无DB／响应正文文件入库；注入秘密实际值扫描无命中，不能冒称全量未知秘密检测。仅开发分支，无main／Release／部署／PC／新Windows CI。
