# 未安装的持久 ledger + canonical account cursor 原子 CAS 控制器

基线080ea7b184a7476019431c1803b4bfe4864afbd9。root唯一仓库写入者；父级已有限审查通过基线。原19 unique/20 executions结果原样保留，只是历史资格；取消仅顺序SQL，未宣称并发；正向仅generate，不称source/cold链。

最高价值下一片：新增独立 production_trial_journal.py，复用现有 policy 与 Store.tx/当前权限门，补真正服务端可信加载与持久原子更新。来源producer需要实际provider合同，sender需要外部IO证明，均可继续离线开发，但本片先关闭可独立实现的持久占槽/CAS缺口；账户缺失不阻止本片。

## 输入与存储

内部函数 reserve / record_attempt / settle 只接受Store、原user/完整contract/approval key、完整ReservationIdentity、实际wire bytes、合成内部SourceVerificationResult、expected_revision；settle另收Outcome。不接收ledger、cursor、任意callback、source/sender选择器或凭据。read接受原scope和账户opaque ID，先核自有ledger完整标量锚，无记录/错scope拒绝且不先读global cursor；再按account→ledger锁顺序读历史，不发起动作。所有回执恒UNINSTALLED/live=false/dispatch=false/real-source=false，不是Permit。

已有delivery_graph_requests四键表复用新明确uninstalled namespace，ledger及其seal一对、同canonical账户全候选全project/trial共享cursor及seal一对；不动旧synthetic kind/ledger，不加表/DDL/Grant/权限。新kind仅由显式内部调用在事务中写，API/Worker/importer仍为零。此候选账户串行覆盖仅本journal，不宣称全系统/旧synthetic共桶。

Ledger response存revision与Ledger、最后写入的quota revision；quota response存revision与AccountQuotaCursor。初始ledger仅由原requirements生成，不由caller提供。quota键由原canonical算法及account派生，caller不能选桶。load核双份完整性、exact request/scope/account、typed policy状态和cursor不落后。缺一份/损坏拒绝，不自动修复；空状态只在该scope从未存过时建立，旧revision0新Attempt不能覆盖既存状态。不声称抵抗DB管理员同时回滚全部可信行。

## 事务与重复

先核owner/project/runtime；账户行用于同账户序列化，ledger按project/trial定位；持有原project及当前Run锁至commit，fresh policy在账户等待后重新检查取消/lease/fence/版本，不续租。最终具体锁顺序须与现gate project/资源/Run顺序核对，避免新增反序。SQLite使用原BEGIN IMMEDIATE；PG语法实现但本轮无PG资格。

全新账户用原方言ON CONFLICT DO NOTHING创建成对哨兵并锁读；已有单边拒绝，拒绝/失败整TX回滚。全部非重复mutation同时对ledger两份及quota两份作带旧fingerprint+requestFP+revision数据的CAS（无外部通用save接口），每次revision递增，quota时间只在reserve前进；一项冲突则整TX回滚。expected_revision须精确匹配，不能传旧snapshot/空Ledger回放。

原Attempt完整身份相等的reserve重复、已marked的record_attempt重复、完全同Outcome的settle重复可返回原历史且不更新任何revision；即使expected_revision旧也只能读原历史，恒无send权限。错wire/原scope/原Attempt/outcome拒绝；新Attempt受精确revision及pending/halt门。

record_attempt标记是会计marker，不是sender授权。和实际取消/lease/fence写入由同事务锁线性化：取消/漂移先commit则标记失败且原槽保留；marker先commit则后续取消/漂移后settle保实际usage、accepted=false/halt，不退槽。没有“外部请求与DB原子”的声明。

## 最小测试边界（合成来源、无模型/transport）

1. 两独立Store并发同原Attempt只一次reserve，重复无写；显式旧revision新Attempt拒绝，原key重复仅历史。
2. 同账户两project/两trial并发首预留仅一胜，另一RATE_LIMITED，只有一个cursor；证明SQLite候选账本串行，不冒PG行锁。
3. 真实两连接顺序控制marker与实际Store.command(cancel)，及lease/fence写入，各双序；用测试Event/SQL观测控制已持有事务与竞争者已尝试BEGIN，有界等待、全部join，无产品注入hook。marker先则后续settle拒收保usage；竞争写先则marker拒绝保预留。
4. 新Store重开pending/marked及UNKNOWN，read/重复仅历史，无自动mark/send/退款；partial usage的null保留、cursor时间与原槽不减。完全重复settle只读，改Outcome拒绝。仅本journal新增恢复，不重复旧synthetic恢复矩阵。
5. CAS旧fingerprint冲突/末写失败必须整TX四行回滚；单边/损坏持久副本拒绝且不修复。只覆盖本新增存储边界，不扩成一般故障矩阵。
6. 固定离线哨兵拦HTTPTransport/Settings.from_env/InternModel。保留fixture与命令/JUnit/inputs/helper before-after、journal行数/指纹/revision及原权限表严格不变。针对新module做Ruff；不重跑原19节点。真实模型/fee/source/cold全链/Windows/PG/远端CI均不冒通过。

待设计独审后实现。最终冻结源码、有限独审、普通开发分支推送；不改main、不启用LIVE、不注册API/Worker/sender、不读凭据或扩权限。
