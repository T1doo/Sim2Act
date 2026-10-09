# 受限实际闭环与完成判据

原 V5 §9.3(7) / F2-T07要求实际重验受影响检查及全局约束。原系统PROJECT
仅固化PENDING jobs；APP的CSV列补丁检查器明确拒绝PROJECT；Report展示仅回读
文字。本候选在原精确PROJECT计划下，执行既有可信CSV和Report有限检查器，
逐CHECK记录PASS/FAIL/NOT_RUN，记录缺图/unsupported和未知依赖。不是整体验收。

用户从原计划页面明确读取范围，逐应用选择数值列或所属候选的真实Run版本，
确认当前plan/options/graph/result指纹后提交。CSV实际授权读取原数据并调用原
registered_tool，再独立Fraction算count/sum；Report实际重新读取材料和计算原
有限规则。已接受POST及原键GET均需当前证明核验，UNKNOWN/晚回执保持原body/key。
首次POST本身422才可释放首次未接受意图；GET422、已UNKNOWN后的422不得释放。

所有项目成员先完整验证当前授权、来源与可信证明。权限/来源/锁/计划/成员/
Run/version/fence/result/独立seal/源码漂移必须零写拒绝，不能省略为unsupported。
只有已授权且可信但缺图或不能派生规范图的成员，能保留明确NOT_RUN账目。
原plan、jobs、candidate、Run、presentation、业务表均不修改；只追加现有
request表中的独立检查结果及seal。没有自动派生、自动Run、模型调用或业务执行。

有限PASS仅表示该registered checker当前通过。极端精度超出独立oracle记录
NOT_RUN；schema-valid但违反材料规则的Report记录FAIL；Report explanation仍
NOT_CHECKED。dependency_completeness BLOCKED_UNKNOWN、owner PENDING、semantic
UNKNOWN、overall NOT_ACCEPTED、PROJECT PENDING/BLOCKED_PARTIAL、发布关闭。

判据：实际页面输入→执行→当前精确回执；冷Store、原键恢复、两真实连接競争；
SQLite/PG、CRUD-only角色、独立负例、真实旧源码创建持久数据再升级；实际冻结
源码/页面脚本SHA一致，最终独立审查及普通候选push。执行结果与具体SHA在README
及原始日志中记录；长期PG超时、HTTP200提示限制及Windows/Edge/Node原生边界不变。
