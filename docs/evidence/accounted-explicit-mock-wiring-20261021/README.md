# 默认关闭的原 Mock 路径显式 candidate 接线

基线 `a0fbd16e7d917ca00ab55aed81519d454bb35998`。唯一写入者继续原环境、模型及
thinking 设置，没有创建新写入者或恢复旧实例。本片仅实现候选接线和局部验证，
不运行 prefix、完整 `_prepare`／两次实际 commit、G0、第四 Mock 窗口或真实模型，
不申请新凭据、费用、权限或发布。实际 Worker／模型／transport 的执行由测试哨兵禁止。

## 现在接到了哪里

```text
run_prefix(..., _mock_accounted_config=显式私有配置)  # 默认 None
  → 捕获原 _cold_model_before；另构造 exact-config partial
  → StopBoundary.wrap(original, ..., _target_context=partial)
      未绑定／非目标：只调用 original，不传配置
      确切 Cold Worker/run/version/attempt 校验、6/8计数关闭、原arm后：
        → 原 _cold_model_before(..., _mock_accounted_config=config)
          → exact _NativeConfig + test_only SQLite + 原PB Cold资格，否则拒绝
          → 原 pre _cold_graph_read
          → 原 _cold_first_binding，完成后
          → 同 guard 的 _native_candidate context
          → 实际 _ColdTrialGraph(..., completed=原结果, _accounted_candidate=同候选)
          → 原 first/second commit 调用位置和主体保持
          → 原第二完整record／finite检查
          → candidate context退出
          → 原graph最终检查／invalidate
          → 原stop／最终时钟检查
```

原 Source → recipe → backend-version → Generate 顺序、各 producer 一次、整族
发行前选路及原授权／完整读集／事务／fence／lease／stop／期限均未改。不是另造
producer／executor 或用 helper replay 替代真实 commit。显式不合资格请求拒绝，
不会悄悄 `yield None`；未显式选择的默认行为仍按原资格处理。

初审发现全局 partial 会把 Generate／Source 也送进显式候选资格门，已在任何业务
执行前纠正：保留 original，仅原边界验证后的确切目标选择 partial。两个实际
构造点的资格明确分离：pre 仅可显式选择合成 SQLite，post/audit 构造不接候选；
普通 `advance_model` 调用也不传内部选项。类型名 ProductionTrialBinding 不等于
生产资格；未替换 production environment 与 test-only SQLite 资格仍无交集。

`configured` 的三项历史合成替换（environment、固定合成 account resolver、
software qualification）原样保留在既有测试文件，没有新增、隐藏或扩展它们。
本次测试没有调用 configured 或安装 account stub。真实 `resolve_account`、
`spec_production.source`、软件门与所有实际账户实现保持基线字节。

现有 `g0_bounded` CLI 仍不传新选项；没有新增 CLI／环境开关、grant 或自动启动。
私有 `run_prefix` 参数只是接线，不能授予执行权。未来实际选择仍需把精确 mode
及有限配置绑定到新的冻结描述／grant，不能复用已消费 grant。

## 错误口径修正

选中路径可能抛出原校验或新增 candidate 的容量／协议 DomainError。独审指出其
来源不能一律记为原 G0 拒绝，已保守修为 `UNKNOWN`，附
`error_origin=UNDETERMINED_ORIGINAL_OR_CANDIDATE`，使用
`selected_context_error/selected_context_diagnostic` 保存原异常内容；异常对象及
cause 保留，不吞掉／重试／降级。未选择的原拒绝分类和字段不变。

父 launcher 不把 UNKNOWN 当成功。即使未来 context 完整返回，也仍需另证实际
route 是 OWNED；LEGACY 回退只能证明旧路经过，不能计为候选性能验收。

## 实际验证与原件

| 批次 | 实际结果 | 对应版本／限制 |
| --- | --- | --- |
| first | 9 passed，1.75s | 初版局部测试；未包含后来两项正常／过期退出测试 |
| frozen | 192 passed，59.58s | 含11项局部接线与既有native/component/guard/fingerprint/release回归；在最后诊断分类修正之前 |
| closure | **12 passed，2.73s，0 fail/error/skip** | 最终四SHA；仅对最后分类增量作必要局部验证，普通body错误及candidate容量错误都为UNKNOWN |
| closure guard units | **27 passed + 4 skipped，31项总计** | 原保护单测独立进程；4项缺原独立编译native依赖，未声称通过，也未为未改VFS扩大构建／运行 |

192项之后 runtime／prefix SHA 未变，最后只改 guard 的错误分类及对应测试，故
未重复整组；不把192重标为最终四SHA的整组结果，不相加重叠用例计总验收数。
原始日志／JUnit、两个冻结清单及命令见 `tests/`、`validation.json`。
最终 Ruff 四文件通过；mypy runtime 单文件通过，其 SHA 与最终清单相同。

局部接线用真实 CGR／native context，但 first binding 和 TrialGraph 使用明确
stand-in；record-shaped 值只核 scope 退出及退出后原时钟拒绝，不冒充完整业务
authority。边界测试只有本地计数状态／arm callback，不是实际 Mock 交换或 G0。
没有执行 `_prepare`、trial commit、Worker、InternModel、provider transport 或
configured。正常／异常 scope 关闭、缺第二guard、过期、非测试／非SQLite／错误
路由／外来配置、默认与post不启用、非目标分派及UNKNOWN分类均有局部用例。

两份独立静态限定 ACK 见 `reviews/`，绑定最终四SHA；reviewer 只读代码及作者
原件，没有亲自运行产品／测试／数据库。保留初始全局partial发现、修后设计ACK、
分类缺口中间报告及最终closure；旧报告不冒充已审新SHA。

## 下一次完整验证的最小真实合同

这是后续验证所需条件表，**不是授权申请，也没有执行它**。目标限定旧首 G0，
原 first 和 second commit 都完整经过，退出原 graph 后在 W5 前停止。

| 项 | 原路径推导及上限 |
| --- | --- |
| 新库／目录／grant | 各一次全新；不续旧库、不复用已消费grant、不自动重试 |
| 实际交换 | Generate 3 + Source 2 + Cold首1 = **6**；不需要／不允许Cold2 |
| 方法入口 | 6交换入口 + Source原2同步delegate = **8**；两次commit复查同一已收Cold响应，不新增交换 |
| 时间下界 | 6次同账户reservation的5个至少60秒间隔，跨度至少 **300秒**；不是额外300秒纯等待，也不是成功时长保证 |
| 外部上限 | prefix **480秒**，G0 **120秒**，总work **600秒**，同组清理TERM5+KILL5 = **10秒**；不因candidate扩大 |
| 原更严期限 | lease **30秒**、每Run最多 **300秒**、TTL **1800秒**、每60秒一reservation等仍优先；外部120秒不准延租约 |
| 磁盘 | 原 **67108864字节／64MiB监测预算**，按父循环和收尾采样，selector等待最多0.05秒；不是native hard quota，必须报告真实间隔和清理证据 |
| native资源 | 必须冻结显式 `_Bounds(nodes,edges,depth,leaf_bytes,encoded_bytes)` 与 `_Limits(resident,peak,work,integer_bits)`，单位为受控新增工作／分配的逻辑账本 |
| 尚缺资格 | 当前没有从完整原输入证明的有用native有限配置／OWNED选择见证，也没有整进程RSS上界；不能把夹具10**30等或旧2.2MiB磁盘峰值充当该证据 |

历史第三轮总work342.467021839秒／G030.985113144秒只是一个已存观察，不能保证
新候选两次commit成功，也不能推出更小保证预算。完整验证前还需冻结“明确Mock
mode + 有限配置 + 实际OWNED/LEGACY记录”的原launcher接入／新grant合同；当前
CLI默认未选择。这是具体剩余技术条件，不能靠再开相同窗口、上调额度或伪造
账户事实填补。出现UNKNOWN／LEGACY／期限拒绝必须分别如实报告。

范围不能混淆：以上6/8足够的是**首 G0 的两次commit及W5前停**，不是完整PB。
原产品3+2+2整链还包含Cold2，固定handler下总计7交换／9入口，reservation跨度
至少360秒；这超出既有6/8诊断合同，本片不改该合同、不执行或申请扩限，也不把
首G0完成写成完整PB完成。

## 真实 account resolver 尚缺的最小合同

来源是[原证据边界](../../F2/ProductionEvidenceBoundary20261018.md)、
[原账户来源合同](../../F2/ProductionTrialSource20261018.md)及当前源码，
不是本片新增授权需求。账户费用source与已成功任务的业务归档source是不同事实。

| 层 | 最小已有合同／尚缺实现 |
| --- | --- |
| 服务端调用输入 | `resolve_account(user, exact original TrialContract/V2/PB, approval_key)`；caller须先以原Store/事务核 `_approved`，不接受HTTP传source/ALLOW/registry/callback |
| 原合同派生要求 | principal/project/runtime/trial/approval、完整contractFP（含材料／Goal／caps）、softwareFP／authorizationFP、固定provider/model/endpoint、canonical quota、原expires、paid_cap严格0；投影本身不证明批准 |
| 身份事实 | 服务端受审来源确认稳定opaque账户及原channel；结果账户必须匹配ProductionTrialBinding.account_id和唯一canonical quota算法，不能由用户声明／猜测／凭据字符串替代 |
| 权益事实 | 同账户当前合法免费权益，须有可核查来源／条款／账户事实；公开价格／余额／hash／ALLOW布尔本身不证明合法权益 |
| 收费控制事实 | 可执行的强制不可收费、paid_cap=0、禁止收费fallback；不是仅设置预算字段或调用后猜零费用 |
| 状态事实 | 当前revocation、observation与有效期，未知不当false；可信身份／权益／控制／状态可以来自同一受审来源，不要求虚构四个provider API或签章接口 |
| 内部输出 | exact strict SourceVerificationResult：requirementsFP/account/quota/provider/model/endpoint/evidenceFP、ALLOW/DENY/UNKNOWN、显式权益／不可收费／撤权事实、observed_at/expires_at |
| 原核验 | 精确绑定、canonical quota、ALLOW、revoked=False、两权益事实True、observed_at<=now<expires<=contract.expires；enclosing source匹配账户并保留软件资格与后续动态重核 |
| 信任根缺口 | 固定服务端producer的来源真实性、当前撤权与实际零收费控制尚未实现／受审注册；resolver当前requirements后无条件SOURCE_MISSING，输入DTO／CandidateDiagnostic无法安装它 |

原 `production_trial_source.load_offline` 的四角色、8192B原始JSON及合成issuer只
验证既有离线存储合同；不得直接标成真实生产来源，也不擅自把该格式上限或
30秒重签要求加给真实provider。`check_source` **没有统一30秒观测年龄门**，
`validate_candidate` 的30秒仅是无权威候选诊断规则；原lease30秒是另一种期限。
无来源、UNKNOWN、撤权、错绑定或过期继续拒绝，不签Permit／FeeProof、不重发
或把未知usage／费用补零。本片不实现账户producer、不安装凭据、不修改这些门。
