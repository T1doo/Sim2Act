# 自有GoalCard边界复核：冻结前只读

2026-10-12，独审`/root/text_logic_review`；仓库`/workspace/Sim2Act`，分支`dev/text-logic-owner-20261012`，HEAD `233ba9618ba462aad19e1ca16f085cd0d7242632`。作者仍有未提交产品修改；本复核只读src/tests/doc，只写本/tmp；未运行pytest、Worker、HTTP、Node或模型。作者通知candidate2自己的测试已冻结运行，明确要求独审继续静态、不启动测试。

## 当前已满足的设计方向

- `SaveInput`严格类型/额外字段禁止，外部旧card ID没有输入位置；refs先比当前唯一target，不遍历调用者旧refs；新原文和scope都拒绝空白。
- 项目锁下先核newlogic候选、当前target权限及logic软件/预算，再核本app自己的双seal记录。metadata keys只取本app、本owner及这两个kind；左右key集合一致、最多64，pair规范指纹一致，记录闭集字段、request/body/goal内容/snapshot指纹和native immutable版本交叉核验。
- 原始body严格类型；序列及goal版本显式`type is int`，连续绑定序列、前一binding fp和同card ID约束。generic编辑可使head落后于sealed version而STALE，显式修订通过head CAS生成新native版本，没有自动复活或继承。
- native card/head/version与双seal都同一事务，写后`current()`再验当前权限、native版本及两seal。历史原keyGET可以返回自己的已封历史版本，不能将其设成当前head。
- 自有GoalRef只增加Run accepted request及snapshot，不改immutable Release/candidate/原goal provenance。enqueue要求精确当前binding；prepare_dispatch、commit_result及typed append后最终门均`check_run`。历史`load_binding`只`verify_frozen_run`对应历史版本；owner.context另外检查当前Goal。旧技术结果可读、当前人工证据需要新Run的分工正确。
- 最大criteria为title+goal(2)、五类原条目(80)、applicability(16)、resource/technical范围(2)，恰好100；决定要求完整有序IDs及非空reason。作者新增100项测试与Goal创建前/修订后的普通Run测试。
- owner contract已加入规范`current_limits`；本设计报告前阶段的预算建议已采纳。当前预算变化仍高于cap也会改变完整契约指纹，旧签收应STALE，不破坏永久Goal历史anchor。
- 合同已明文强Run政策、历史读取边界及软件指纹升级fail closed/no迁移/旧库升级NOT_RUN。

## 已报父作者、待下一冻结实际验证

1. `verify_frozen_run`未先校新增两字段同时存在：只有`owner_goal`而缺`owner_goal_binding_fingerprint`会触发直接索引KeyError；该函数未controlled，普通HTTP调用可能返回/抛500而非受控DomainError。必须先拒绝字段缺失/null/不正确ref结构，再核本app自己的历史seal；增加普通持久字段污染验证。父作者已确认将在candidate2测试结束后修。
2. 当前复用`source_barrier`不包含`goal_card_versions.snapshot`。本新合同尤其禁止继承旧source与初始target GoalCard，须把两张初始卡ID纳入实际SQL private-cell屏障，才能把“旧卡读取0”作为证据结论；原目标材料仍需正常授权读取。父作者已确认追加该规则。现candidate2页面通过（若通过）不可追认成已覆盖这两个旧卡snapshot的屏障。

没有从静态阅读再提出扩大产品范围的要求。下一冻结最低独审范围是作者新主线API/实际Worker/4个普通可见IPC页面，加独立双seal/native/RunRef普通污染探针与64/65版本容量/原key恢复边界；具体以父作者冻结交接为准。所有失败、stderr/exit/SQL/资产proof及源前后hash保留，不套用旧取消竞态目标。

本阶段执行数0，无活动独审测试进程，不能签实现PASS。禁止socket/native/PG/Windows、真实付费模型/凭据/main/core/force/deploy等边界持续；旧范围误选真实结果与旧BrokenPipeUNKNOWN不改写、不重试。
