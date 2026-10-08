# F2-T07 单节点人工编辑保护：实现候选待独审

基线dev72563fa220c66dd142be5656c5468d177de8fede；用户明确授权后建立dev/manual-edit-locks-20261008。合同先提交1dc737f，实现/标准测试冻结 **de6ba39eae81abd138aa94cc87d1e083530056af**。证据归档后产品和测试字节保持。未独审不合dev，原成果/候选保留。

新manual_locks适配器挂现有delivery-graph/manual-locks GET/POST及/receipt查询接口，复用项目事务锁、图锚、既有locks/requests表。只固定CSV、自己项目、既有单节点；原LockInput/旧内部记录不改模式，set_lock仅抽出同事务write_lock供两入口共享。公开闭合模型绑定严格图revision/fingerprint、节点id/revision/content、lock revision CAS（零为无记录）、bool目标及明确consent；同状态新键拒绝。当前身份/项目/来源/工具权限先于锁和请求账本。无新表/DDL/Grant/角色/安全/文件权限/任意代码/管理员强制解锁/跨项目继承。

锁及canonical回执、公开意图和独立seal同事务提交，失败回滚。先授权再按原键核验accepted receipts，丢响应重发不先读已失效旧图，仍验证当前来源/授权/独立seal；同参零新写/修订、异参冲突。历史SUPERSEDED不称当前锁，当前CURRENT须锁记录精确匹配。锁操作后须显式重派生；graph_revision+lock_revision防锁ABA。来源被篡改时既有CSV候选拒绝读回/重派生，本切片不扩展来源编辑能力；旧锁回执不改签。

原图页面新增节点选择/锁修订、锁/解锁、明确确认、原键恢复及有限历史。输入/节点/操作/图/项目/身份切换清确认；持有旧图或过期锁状态禁提交；延迟响应依原上下文epoch拒绝落位。read-only有限历史最多50条按键排序，不承诺时间排序或整页刷新自动存储请求意图。候选未验收、semantic UNKNOWN/owner PENDING/发布关闭。

## 冻结实证

107唯一collection，SQLite **105PASS/2SKIP/0FAIL/0ERROR**（两个PG专用CRUD角色）；PG17.9 **107PASS/0SKIP/0FAIL/0ERROR**。执行源码均de6ba39，前后hash一致，所有旧tests/scripts/workflows/locks与基线逐文件不改。107为此次影响范围，不机械重跑旧757，不借旧全量认证本次代码。[完整scope/collection/JUnit/raw/provenance](../evidence/manual-edit-locks-20261008/)。

新增25例含：实际锁定→重派生→原列绑定LOCK_CONFLICT且全表内容保持→解锁重派生→新精确检查30/15；bool/int/图版本/锁CAS/明确确认/键；当前所有权门、撤权/转移/来源变化恢复拒绝；锁ABA/异参/SUPERSEDED；旧内部锁兼容/公开解锁；请求/独立seal/canonical篡改；冷Store读回；非CSV及客户端身份字段拒绝；PG最低CRUD角色。三种真实Barrier双连接线程竞争：lock-lock、lock-modify、unlock-unlock。不可变草案若先提交，可与后到锁历史共存，但后续旧草案检查拒绝；锁先提交则旧修改拒绝。这不声称跨进程并发或自动取消既有Run。

新实际loopbackHTTP/JSDOM原页面闭环每端14断言（真实丢响应、原body/key恢复、清旧图、锁冲突、解锁后检查15/30、SUPERSEDED、项目ABA延迟状态拒绝、冷页面零写读回）。原列绑定页面20、原CSV/Report图页面各29，合计每端4个页面病例/92DOM断言，加载源hash核对。原后端图/列绑定、两个真实旧源码升级、受控运行精确确认与所有权门定向回归保持。HTTP/JSDOM不是布局/视觉/原生Edge认证。

Ruff全src/scripts/tests、mypy51源码及Node语法检查通过。现成developer Node24.19.0、自有jsdom30.1.2；未改依赖锁。Windows900/Edge240/Node150原标准保持，原生NOT_RUN；没有真实模型/部署/新CI调用，提交skip ci。新模块不调用provider，原回归fixture仅既有离线合成/NoModel通道。

阶段日志保留：first17P1F（新断言误把既有LOCK_CONFLICT HTTP400写409）、second18P、third22P1F1S（新测试错误假设改源后既有候选能重派生）、fourth5P；只修新断言并维持真实合同，不改原断言或扩大权限/来源能力。npm首次因默认cache不在可写区失败，后只用自有/tmp cache完成安装，未扩权限；不是产品故障。上述阶段不是冻结通过证明。作者静态检查不冒认独立审查；候选等待父线程独审。

## 清理及复现

自有network-none PG容器/无端口、临时PGDATA、fixture schema/role及npm/测试/源码archive目录清理；停止前实际SQL目录查询确认零fixture schema、零临时角色、零public表，随后正常stop/rm，无force或其它资源清理。cleanup.json和cleanup.py保存具体证据。既有Python环境、共享Node环境保留。

[用户页面步骤及API／测试复现](ManualEditLocksQuickstart.md)。总体F1/F2、真实gold、通用P-B、语义/人工签收、正式发布、Windows原生仍未验收。候选push前再次核远端dev72563fa未变、祖先和新分支不存在，普通推送独立分支；远端精确HEAD由交付回复确认，不触碰main/dev或部署。
