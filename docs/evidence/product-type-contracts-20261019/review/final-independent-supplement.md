# 类型修复回归的独立补充审查

结论：**有限通过，未发现可归因于本次类型补丁的明确 P1/P2**。原主批仍是 62 节点、60 PASS / 2 FAIL；不能签为全回归或产品整体验收通过。两个失败均在原 5f 基线同点实际复现；候选 MD 单项隔离复跑通过，不抹去其原主批失败，也不证明该类型补丁修复了心跳问题。

## 代码与证据身份

基线 `5f5f964906792433d51140871d9d7b7aab365de0`；候选源码清单 SHA256 `bd38631dcfc5ac4405880f8b9b7a1ac2d4b71e73faf180d1be82fb33fc04cc46`。本次再次逐项验证 115 个源码/配置文件仍匹配冻结清单。21 个相关源码、测试、观察插件分别保存基线和候选副本及 SHA256。Worker、Store、普通反馈 DTO 定义、模型及原测试/观察插件未改。两个旧审查清单哈希未变，未改写旧 sealed 报告。

## 实际回归结果

| 运行 | 原始结果 | 证据边界 |
| --- | --- | --- |
| 候选主批 | 62 节点：60 PASS、2 FAIL，658.53 秒 pytest | 两个 F 均保留，不重写为预期拒绝通过。 |
| 5f 基线 V2 七槽单项 | JUnit 1 FAIL；同一 stage_review → _generation_accounted 的 Mixed/unknown backend 拒绝 | pytest 完成后外层观察脚本出错，真实 pytest 退出码未持久化；不伪造 exit 1。erratum 和 JUnit 原件保留。首次导入缺依赖的 exit 4 也不当作测试失败证明。 |
| 5f 基线 MD correction[True] 单项 | exit 1；第 169 行 RUNNING ≠ PARTIAL | XML 用例 82.030 秒、pytest 总计 84.35 秒、外层 97.98 秒，三个计时口径分开。 |
| 候选同 MD 单项顺序隔离复跑 | exit 0，JUnit 1 PASS | XML 用例 135.738 秒、pytest 总计 136.77 秒、外层 149.44 秒。原源码、测试、30 秒租约和断言未改。 |

本审查只读取并复制作者已经完成的 XML、stdout/stderr、执行记录与观察日志，没有自行运行回归或数据库。完整 mypy 113 源成功、公开 8 schema/3 序列合同不变以及全仓 Ruff 仍有相同 117 条旧诊断，属于已保存的作者证据；本审查没有独立重跑这些门，不将 Ruff 全门称为通过。

## 第二个失败与本次改动的关系

普通 correction 使用 `Worker.process` 通用循环，不经过 text_workflows 的恢复心跳。通用线程每 lease/3（当前约 10 秒）调用 Store.heartbeat；任一异常会停止该心跳线程。Store.heartbeat 在事务内重新 guard，Store.guard 拒绝 lease_until ≤ 当前时间；过期租约不能被续活。主循环捕获 DomainError 后尝试 finish，如果 final guard 再次因过期拒绝，该错误被吞掉并把后续收敛交给恢复，Run 可以保持 RUNNING。这些 Worker/Store 源码在基线和候选完全相同。

原候选失败记录的子 Run 时间为：CLAIMED 1792396321.9464624，最终 lease_until 1792396351.9453492；首 MODEL_RESERVED 1792396330.9639068；resource.read TOOL_VERIFIED 1792396349.3350253，距租约截止仅 2.6103 秒。context 已保存一次模型响应和一次工具回执、requests=1/tools=1，尚无第二模型调用。这与原租约未延长、后续 guard/finalization 拒绝的机制吻合，但原主批没有相应心跳异常记录，精确终止异常/争用来源不能据此补签。

基线 MD 隔离日志实际记录了两次带 run_id 的心跳失败：OperationalError、sqlite_errorcode=5，无成功 Run 续租返回。该事实只证明基线该次运行的观察。候选隔离自身日志也记录一次带 run_id 的 OperationalError/code 5，无成功 Run 续租返回，但节点通过；因此一次数据库心跳错误不是该断言失败的充分条件。候选日志另外两次 return 均 run_id=None，是 Worker 活性心跳，**不是 Run 续租**。此前进度消息将两次 return 称作续租已明确纠正，最终 JSON 分开计数。

对原 8 条及额外 23 条修复逐项复核后，普通运行链实际触达的变化仅为：同一普通反馈 DTO 的显式 Issue 实例构造、原缺失声明的同码同文案拒绝、有限局部容器注解和 CSV/MD 函数的不同局部名称。没有新增 SQL、延长/取消租约、改变 guard 或 heartbeat、自动重发、替换权限检查或修改模型调用数。工具 AST 在归一化已审查别名/注解后相同；ordinary_corrections 各函数在仅归一化已记录的 DTO 构造/缺值拒绝后相同。DTO 显式构造属于真实运行时操作，不能凭静态分析保证耗时完全相同；基线实际同点失败及候选隔离通过也不证明所有环境均无潜在性能回归。

## 有限交付判断

本轮可按真实范围交付原类型门的最小修复、独立源码审查和实际回归结果。没有发现要求撤销本次源码有限通过结论的明确新增 P1/P2。保留两项已有失败：V2 旧正向夹具未绑定既有控制器，以及普通 MD correction 的运行/心跳收敛问题。不要迁移旧夹具、修改产品隔离、扩大费用/权限或另修心跳来凑本轮运行数字。不得宣称零未知回归、全仓 Ruff 通过或整体验收完成。

本审查仅写本新目录；未改产品、测试、Git 或配置；未运行生产链、模型、数据库或网络。Windows、PostgreSQL、远端 CI、真实账户/免费额度、真实语义/人工验收和旧满盘缺失报告仍不在本轮证明范围。
