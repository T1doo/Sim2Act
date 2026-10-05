# F1 Plan

基线：V5；状态 IN_PROGRESS。任务范围和门槛沿用总计划 §3。

| task_id | 目标/产物 | 测试 ID | 状态/依赖 | 证据 |
| --- | --- | --- | --- | --- |
| F1-T01 | 文档与数据契约 | AT-03 | IN_PROGRESS；原生/LIVE 部分 BLOCKED | [Log](Log.md) |
| F1-T02 | 原生启动链 | AT-01/05 | IN_PROGRESS；原生/LIVE 部分 BLOCKED | [Log](Log.md) |
| F1-T03 | 三工作区骨架 | AT-05 | IN_PROGRESS；原生/LIVE 部分 BLOCKED | [Log](Log.md) |
| F1-T04 | 身份与可信动作网关 | AT-03/04/08 | IN_PROGRESS；原生/LIVE 部分 BLOCKED | [Log](Log.md) |
| F1-T05 | 持久任务与操作账本 | AT-05/06 | IN_PROGRESS；原生/LIVE 部分 BLOCKED | [Log](Log.md) |
| F1-T06 | 书生适配与统一限流 | AT-02/07 | IN_PROGRESS；原生/LIVE 部分 BLOCKED | [Log](Log.md) |
| F1-T07 | 固定测试资产 | AT-01—28 | IN_PROGRESS；原生/LIVE 部分 BLOCKED | [Log](Log.md) |
| F1-T08 | 冻结环境与待确认 | AT-01/02 | IN_PROGRESS；原生/LIVE 部分 BLOCKED | [Log](Log.md) |

顺序：文档冻结 → 骨架/启动/持久链 → 书生适配/受控工具 → 权限/恢复/故障/日志。
所有测试初始 NOT_RUN；LIVE 和 Windows 缺依赖 BLOCKED。AT-09—28 规格先冻结，实现在对应阶段推进。不得降低验收。
