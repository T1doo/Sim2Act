# Sim2Act 动态总入口

当前基线：V5；F1 IN_PROGRESS，尚未通过阶段门。仓库开发分支：dev/f1-foundation。

规范：[平台产品设计](平台产品设计.md)、[分阶段开发计划](分阶段开发计划.md)。
来源：[V5 原始文本与校验](sources/V5/manifest.json)。原始正文完整保留；修订见 [DocumentReview](DocumentReview.md)。

| 阶段 | 状态 | 当前证据 |
| --- | --- | --- |
| F1 | IN_PROGRESS | [任务](F1/Plan.md)、[日志](F1/Log.md) |
| F2 / F3 | PLANNED | P-A、P-B、增量验证全部保留，待 F1 门通过 |
| R0 | PLANNED | F1—F3 通过；禁止执行任意模型生成代码 |
| C0 | BLOCKED | 截止、体验链接、托管模型文件要求从 F1 并行核实；R0 后最终验收 |
| F4—F7 | PLANNED | 本轮不实施 |

目标平台为 Windows 11 x64 原生 + PostgreSQL，尚无用户环境实测。云端 Linux 工程测试不等于 AT-01/27 通过。
运行后端仅书生；缺账号与预算时真实接入 BLOCKED，不读取隐藏凭据，不调用收费 API。
保持项目、应用、资源三个工作区；应用发布与两条生成路径在 F2 实施。

## 最小待确认

- 参赛主体/成员、准确截止时间与时区、体验链接接受形式、托管 API 模型文件要求（F1 并行；未核实 BLOCKED）。
- 用户 Windows 环境及数据库安装条件（BLOCKED，仅影响原生验收）。
- 书生账号、本地私有配置、批准的调用/Token/修复预算（BLOCKED，仅影响 LIVE）。
- 授权真实材料与独立验证者（F1 收集条件，F3 评价）。
