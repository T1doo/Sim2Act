# G0 `_base` 资格阶段重复内容遍历：实际产品修复

基线 `5d5a255eb9b3fed2f9f91c5a3aab8d51022b2a25`，原V5 §8.2–8.3 / F2-T09 的完整Cold尾段工程。本片不以缺Windows/真实模型为停工理由；实际修改两份产品源码及必要定向测试，未新跑完整Mock或真实时钟窗口。

## 源码变化及闭合边界

既有完整profile在 `schema-stream-cpu-20261021` 记录 first `fixed_serializers→validate_model` 4313次 / 5.623557610 inclusive CPU 秒；后续 `_stream_values→validate_model` 13888次仍存在。数字有profiler扰动，不能相加为可省时间或据此承诺G0过门。

原 `_base_segments.fixed_serializers` 为确定schema/code纯性，先全量验证所有actual模型，再由原 `_trial_typed_values/_stream_values` 完整新鲜验证actual/raw、dump及严格比较。新资格阶段仅以非递归原生DFS发现本次可达模型类型，再保留原完整schema与serializer新鲜见证。精确原生类型、active-before-completed、completed强引用、dict.values不触foreign key的hash/equality。未知布局/类型/cycle返回不合格，恢复原完整入口路径；没有新增业务深度/规模拒绝。

类型发现不返回或保存model header、raw、omitted、指纹或验证PASS。真正consumer的完整actual字段/fields_set/extra/private/type/cycle门、raw门、model_dump和strict equality均原样保留，不因同事务假定model不变。`_cold_typed_stream.py` 与 `natural_live_admission.py` 未改。没有跨调用缓存、通用skip标记或重入状态。

新增 `serializers_current` 在资格后、consumer前鲜核bootstrap全catalog的compiled serializer身份与标准dump方法；因此定向反例在发现后插入原未发现kind、替换dump时，仍在未知回调前完整entry pin。它不是对全catalog schema元数据的完整复验，不主张抵御任意进程代码篡改；原discovered kinds完整schema见证仍逐次执行。新helper/catalog身份纳入已有资格代码见证。没有删除独立入口、SQL/来源/授权返回检查、两端动态门、完整出口pin、原异常失效或期限检查。

原 `_base` 成功后仍发布同样的无返回值边界。原BEGIN IMMEDIATE/连接/scope/epoch/settings/stop/Run/fence/lease30/Run300/TTL1800、原业务bytes/回执/授权模型和默认native关闭状态不改。并未从mutable frontier移除新根或证明完整owned闭包。

## 实际验证（各批不相加）

- 最终冻结版 **37 PASS，59.19秒，0F/0E/0SKIP**，含新6和原single-content31。555份src/tests前后哈希一致；无测试中改码。覆盖资格后hidden-key/fields_set/替换`__dict__`，新增未发现kind+未知回调之前的entrypin，DAG/cycle/foreign key与container、原raw/stop/settings/write/epoch/scope/未知serializer及默认路径、完整动态两端和scope失效。其中write以撤销Grant注入，复合写入/动态门拒绝，不单独证明授权谓词。初中间6PASS8.64秒不加为43独立用例。
- 新issued SQLite fixture的4root/17kind，实际 `_Comparison.validate_model` 每root仍一次，资格阶段不再调用它。最终6轮交替×10含catalogguard局部median为0.016534840→0.0161380075线程CPU秒（约2.40%）；初版3.31%只是旧中间样本，不继承为最终收益。
- 从本环境已封存的原完整configured前缀库，以immutable readonly SQLite读取原PBTrialContract/Ledger/ExtractInput/CommitInput/3FrozenRunContract JSON，重建7model/25kind，仅测资格。源库SHA `d5f57c88c056ba8b9841febf6ba7bc612053ae0d8b3f10366ac0c8f1a8915ed1` 前后相同。8轮交替×40含新增catalogguard，median **0.0998839175→0.0940888440线程CPU秒（约5.80%）**。原序列/来源/脚本完整保存。JSON重建不保原运行Python跨根别名；该7模型并非原完整Cold cohort或完整原对象拓扑。DAG与foreign对象安全由独立反例覆盖，不能把此局部收益套全链。
- Ruff helper/test通过；mypy仅变更helper通过，非全树类型检查PASS；diffcheck通过。首次中间mypy注解诊断及两处只读诊断命令拼写错误以tool回执转录保留，不伪称原始stderr文件。

所有本片实际测试/计时均 **0 Mock / 0新Worker / 0模型 / 0业务HTTP**。pytest正常退出、SQLite engine由原fixture dispose；本片未启动服务或子进程Worker，没有强杀/未知进程操作。官方公开文档读取与Git只读访问不计为业务HTTP。独审只读核代码、37项原件、冻结摘要、计时原序列和源库SHA，没有另跑测试。

## 生产账户侧的精确缺件

已核实际接线：`pa_trial_dispatch._journal_source` → `spec_production.source` → `production_evidence.resolve_account` → `policy.check_source`；sender已有预占/发送/结算新鲜来源门，journal已有完整账本/账户CAS。无需再造这些组件或另造FeeAuthority空壳。缺的是固定可信生产producer，当前resolver恒SOURCE_MISSING。

最小外部锚是可审原始账户映射/合法免费权益/强制不可收费及禁付费回退/撤销和时效的来源合同、样本和已有合法读取方式；拿到后可先用离线原件实现绑定/撤权/过期/失败关闭的固定producer，不必先真实发模型。synthetic issuer/两份DB镜像/hash或ALLOW不能当这个来源。V5 §7.1/7.3/7.5要求真实API/账号配额/有效预算及价格未知不冒称免费；paid_cap0及强制零费是原冻结trial/用户无新增费用边界，不是V5指定某种证明类。

已只读核[官方鉴权](https://internlm.intern-ai.org.cn/doc/docs/用户鉴权/)、[模型列表](https://internlm.intern-ai.org.cn/doc/docs/模型列表/)、[Chat API](https://internlm.intern-ai.org.cn/doc/docs/Chat/)和[FAQ](https://internlm.intern-ai.org.cn/doc/docs/Q&A/)。所核公开页面没有给出该账户级零费/撤权原始证据合同；这不证明不存在其它私有控制台或接口。未读取凭据/私有控制台、未查询业务models接口，不凭通用公开说明注册新权威。

## 仍未完成

本片是G0路径中的有限代码改进，不是G0修复验收。没有新的完整prepare→两commit/receipt/正常退出A/B、端到端CPU或真实30秒租约裕量记录；旧整链/旧UNKNOWN不迁移签本版。局部约5.80%不支持立即开同样窗口碰运气。下一真正技术条件仍是保持原合同下可量化的完整尾段余量，或经完整消费者/别名/读集证明的更大表示改进；不延租约、拆事务、删校验或缓存PASS。

PG、真实账户/provider、Win11、owner语义、Cold2/W5、整体F2/R0及正式发布均未验/未授权，不新增权限、账号、凭据、安装或费用。旧失败原件不改写。
