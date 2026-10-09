# F2-T07：PROJECT 计划的实际确定性检查

基线开发分支 `5fedb359eff076798782b99a5fd5748d76da5148`，隔离候选
`dev/project-deterministic-revalidation-20261009`。原 V5 §9.3(7)要求对
受影响检查及全局约束实际重验。当前PROJECT只有PENDING任务；CSV已有APP
读算拒绝PROJECT，Report展示回读仅检查文字。本切片执行PROJECT中可用的
既有确定性检查，不新增条件语言、模板、工具、权限、模型调用或业务写入。

公开确认绑定原计划key/native fingerprint、当前options fingerprint、完整可执行
peer输入或归档Run/version/fence/result，以及明确consent与原request key。
所有项目成员先完整验证权限和来源；canonical通过既有load_family，已识别
named Report来源wrapper通过原conditional_apps.load。权限/来源/证明/源码漂移
零写拒绝，不能降级为unsupported。仅已授权缺图或已有可信wrapper不能派生
规范图可记录未执行。不能自动派生、创建Run、过滤成员或接收客户端未执行理由。

CSV复用原授权实读与严格输入输出Schema，再以独立有界Fraction算术核对count
和sum；极端精度超出有限独立核对能力须明确NOT_RUN，不能认作PASS。Report
先以records限定所属canonical候选的真实cold归档，再以_current_check实际读取
当前材料并重算原有限规则检查；explanation继续NOT_CHECKED。每个CHECK节点
绑定ID/revision/content fingerprint/check ref，全部记录执行或未执行结果；未知
dependency_completeness保持BLOCKED_UNKNOWN，不把局部PASS当完整PROJECT。

新结果及独立seal只用现有delivery_graph_requests。原plan/jobs/presentation
字节与PENDING/BLOCKED_PARTIAL状态不改。单事务预验证完整输入后执行，提交前
重新核验；冷读和原键重试重构当前真实证明并与accepted seal比对，不能信重签hash。
整份原JSON在字段/判别union验证前迭代检查所有字符串键和值，surrogate安全拒绝，
避免错误响应回显编码500。仅首次POST自身422可释放未接受意图；已接受POST后
GET422或任何不确定回读仍保留原body/key。页面显示精确确认与逐应用输入/Run选择，UNKNOWN保留原body/key，晚回执不进入
新上下文或继续新写入。

完成判据：实际HTTP页面执行同PROJECT的Report有限规则与CSV新列计算，展示
逐CHECK账目和遗漏/未知；精确回执冷Store/同键恢复；实际旧源码负例；Schema/
输入/CAS/确认/foreign/撤权/来源/计划及独立seal篡改/peer ABA/成员遗漏零写负例；
真实两连接竞争；SQLite/PG与CRUD-only角色验证及独审，冻结最终源码后普通push
候选，不自行集成。保留所有失败日志，必要原计划/Report/锁/CSV回归，不全量无目的
重跑。LIVE0、overall NOT_ACCEPTED、owner PENDING、semantic UNKNOWN、正式发布
关闭；PG超时OPEN、HTTP200损坏提示限制、Windows900/Edge240/Node150未验收。
