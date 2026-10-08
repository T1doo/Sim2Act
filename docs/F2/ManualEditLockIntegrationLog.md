# 人工编辑保护限定审查后的开发整合

2026-10-08父线程明确授权：工作树干净、无merge/cherry-pick/rebase/revert/sequencer挂起；远端dev为72563fa220c66dd142be5656c5468d177de8fede，候选2bde4eb852db28883adab8c6e47f4af06bdf3180为其后代。正常fast-forward整合，无冲突、新产品逻辑或权限变更。**冻结执行2bde4eb852db28883adab8c6e47f4af06bdf3180**，src/schema/tests/scripts/workflows与独审源码 **de6ba39eae81abd138aa94cc87d1e083530056af** byte-identical。后续提交仅归档文档证据，原候选分支保留。

## 独审限定范围

父线程报告LIMITED_PASS、无阻断：source de6ba39，SQLite26PASS/1PG角色SKIP，PG17.9 27PASS；每端15实际页面断言。独立合成CSV算术105.50→13.875，ABA/CAS、并发、撤权、篡改、真实旧包锁记录兼容和最低CRUD角色通过。此处归档父线程报告，不冒认作者重新跑审查方driver或取得原始审查文件。[parent-independent-review.json](../evidence/manual-edit-lock-integration-20261008/parent-independent-review.json)。

只本人项目固定CSV图既有单节点编辑保护，不改身份/Grant/安全设置/管理员强制解锁/跨项目继承。跨进程竞争、原生Edge、超过50条历史**未独审覆盖**。它不等于完整F2-T07、业务/人工/F1/F2或通用P-B验收。旧候选107作者测试、独审27和本轮整合16三个范围分开，旧失败/限制保留。

## 必要整合验证

同一16唯一collection：SQLite15PASS/1PG专用SKIP；PG17.9 **16PASS/0SKIP/0FAIL/0ERROR**；两端均0FAIL/ERROR。执行2bde4eb，源码运行前后hash不变，原tests/scripts/workflows/锁逐文件与旧dev72563fa核对保持。范围为锁定—冲突且内容保持—解锁—重派生—新精确检查30/15、ABA、三种真实双连接Barrier线程竞争、四种当前权限/来源恢复门、旧内部锁记录读回/公开解锁、冷Store恢复、PG最低CRUD角色、新实际页面及两个真实旧CSV执行源码升级，另原受控条件运行/冷读回。没有重跑107/757/旧1591全量，不能跨源码自动签收。

各端新实际页面14断言，包括原键UNKNOWN恢复、SUPERSEDED、延迟状态项目ABA、冷页面零写，以及真实原列绑定检查；不是布局或原生Edge。两个实际旧源码archive（5a5543c和1b65e94）产生旧执行再读新源码，旧证明/计划/确认拒绝、新派生与新精确确认才运行，历史JSON字节保留、不迁移/不重签；人工锁真实旧包兼容依独审报告，本轮旧内部set_lock病例没有冒称另跑审查方旧包driver。proofs/collection/JUnit/log/字节hash见[证据目录](../evidence/manual-edit-lock-integration-20261008/)。

Ruff src/scripts/tests、mypy51及diff通过；LIVE0、现成developer Node/自有jsdom30.1.2，原900/240/150和依赖/断言不改。无真实模型、部署、新CI调用/权限变更。自有隔离network-none PG无端口，schema/role/public表零目录查询、正常stop/rm、自有npm/test/archive目录清理见cleanup.json；共享Python/Node不删。

## 使用与尚未签收项

[原页面复现步骤](ManualEditLocksQuickstart.md)保持；正常获取dev/f1-foundation。锁改动使旧图失效，必须显式重新派生；新计划/检查重新确认，旧历史不覆盖。source升级也不迁移旧证明。远端精确HEAD由交付回复确认。

后续短建议仅限原计划：优先核定F2-T07 **PROJECT/非CSV扩验作业仍PENDING** 的实际检查与保持证明最小缺口；已完成的CSV APP扩验与单节点锁不重复做，内部兼容switch页面也已实现。其次，F2-T04仍是固定CSV三节点/受控条件及有限现有动作，尚不能据此签收更广已注册动作的有限DAG。这些是原方案实质离线功能方向，仅建议、不自行开工。

验收阻塞另列：Windows900完整当前源码成本/Edge尾段仍NO_GO，干净Win11普通用户首次体验、原生Edge、本次跨进程竞争及超过50条历史未验；真实P-A/P-B与语义需要真实provider/获批预算/独立目标评价；owner精确候选验收与正式发布授权缺失，LIVE仍0。不能新增固定模板/外围报告来替代这些真实条件，也不把功能方向自动转成新范围或外部效果/通用写权限。
