# F2-T04 route B 实现候选

以下 PENDING 为候选冻结时状态。随后父线程报告限定独审通过，并授权按已审
产品字节整合 dev；后续复验及当前状态见 [整合证据](../bounded-readonly-dag-integration-20261008/README.md)。

分支 `dev/bounded-readonly-dag-20261008`；基线
`a02371d44208dc2bc4b561a540dd4afa665e57d8`。最终源码 SHA：
`67807be6940cda16007a6a0cca90d9b04a589461`。
独立审查 **PENDING**，不得据此并入 dev；语义 UNKNOWN、用户验收 PENDING、发布关闭。

## 真正实现

原 CSV DAG 页面/API 增加封闭的 1–4 节点组合，不接受任意 Manifest。
可编辑已有读取、求和、报告动作及语义端口、前驱和 typed 条件。编译为既有
Manifest/ActionSpec，复用原 preflight、Run、Operation、Worker、确认、预算和
lease/fence。只使用同一应用已有授权 CSV；未新增 Grant、注册动作、模型调用或业务写权限。

四节点的新 amount 求和/报告与 quantity 求和/报告均实际运行并生成持久结果。
独立 CSV/Fraction 验算为 30 与 15。条件跳过传播到其后继，独立支路仍执行；
每个执行节点保存真实参数指纹、input_sources、前驱回执哈希和独立读回证明。
多个末端输出保留；缺失明确为 null/部分结果，无假报告或自动签收。

旧三节点请求、接线与条件入口保持；旧应用、预览、资源、身份和授权均不覆盖。
同键改 body（含兼容字段）拒绝；所有端口/schema/拓扑校验在保存之前执行。
第五节点、环、自引用、未知前驱/资源、跨语义端口、混合报告元组、未知或非数值列、
未注册动作、代码字段及预算不足均拒绝。原锁、PROJECT 不确定依赖、撤权、
来源变化及精确版本确认门控仍有效。APP 的语义完整性未决项保持原候选标签。

## 精确证据范围

| 阶段 | 实际执行源码 | SQLite | PostgreSQL |
|---|---|---|---|
| 核心 + 定向旧合同/页面回归 | `9b238f3436a2b327c66629a509e702aeb6db4337` | 248 项：241 PASS / 7 SKIP | 248 PASS / 0 SKIP |
| 最终可见文案 | `67807be6940cda16007a6a0cca90d9b04a589461` | 原页面 17 PASS | 原页面 17 PASS |

最终文案提交只改 index.html 的可见文字；编译/执行 Python、JavaScript、全部
测试、schema、脚本和工作流与核心受测 SHA 字节相同，见 `label-delta.json`。
每次执行前后完整文件哈希一致，实际收集 ID 与 JUnit 数量一致。两个阶段的
17 页面用例重叠，不能相加成独立测试覆盖。

`scope.json` / `page-scope.json` 给出实际范围；各后端 collection、JUnit、日志、
summary 和 provenance 保存 SHA、文件哈希与 250 个原断言/脚本/锁/工作流的
字节保持证明。覆盖新增组合、旧 DAG、条件、接线、证明类型/终态防篡改、有效
预算/租约/fence、旧源码升级、暂停/取消/同键/并发、冷恢复和原锁门控。

新增组合核心有 42 个参数化用例（SQLite 的 2 个 PG 角色用例跳过，PG 全过）。
PG 的四节点 true/false 最小 CRUD 角色运行与冷 Store 读回通过；DDL 尝试被拒绝。
新增四节点 lease 失效后的冷 Worker 恢复覆盖已提交 1/2/3/4 节点并保持 Operation ID。
旧三节点另有真实子进程恢复测试；本轮没有四节点跨进程死亡注入测试。

每个后端 17 个实际 loopback HTTP/JSDOM 原页面病例共 242 个 DOM/回执断言，
包含新增组合两例、旧 DAG 一例、受控条件六例和所有旧接线八例。原页面结果、
请求轨迹、加载文件 SHA256 见 `*-actual-proofs` 与 `*-page-actual-proofs`。
这是 Node/JSDOM 工程证据，**不是原生 Edge 或 Windows**。

Ruff PASS；mypy 52 源文件 PASS；产品及新增驱动 JS 语法检查 PASS。
LIVE=0；原 max_tools/max_requests=4、Windows 900 / Edge 240 / Node 150 不变。
旧全量 1591 结果未用于证明本改动；未运行新 CI、真实模型、部署或 main 写入。

## 作者审查及剩余范围

作者审查了闭合 Node/Composition schema、纯动作派生、权限/资源不扩大、预检
预算、拓扑排序与动作对应、回执真实输入、skip/终态、冷恢复、原键及版本门控。
源码范围仅一个封闭编译模块、既有 DAG 链和原页面；没有平行运行器。
此作者检查不能代替父线程独立审查，当前仍 PENDING。

仍未实现非 CSV 新输出、PROJECT 作业闭环、通用 P-B、真实任务 gold、人工签收或
完整 F2/AT13。原生 Windows/Edge 未测。组合暂只允许一份固定已授权 CSV，报告
五个算术/来源字段必须连接同一个 aggregate；不支持任意表达式或跨应用资源。

## 复现与清理

[用户复现指南](../../F2/BoundedCsvCompositionQuickstart.md)说明原页面及 API 的具体步骤。
`run_frozen.py` 与 `run_page_frozen.py` 必须显式指定自己的隔离测试资源，保持
LIVE=0 / SIM2ACT_LIVE_ENABLED=false；原库不能用作测试数据库。
升级用例需显式准备 scope 所列两个原源码 archive；JSDOM 30.1.2 安装在自己的
临时目录，以 NODE_PATH 指定；不要安装到产品或共享 Node 配置。

`cleanup.json` 保存独占 PG 17.9 容器/镜像身份、network=none/无端口、零残留
schema/临时角色/public 表，以及自有临时目录的正常删除证明。没有强制清理。
候选普通推送独立开发分支；dev 保持原基线，等待独立审查后另行决定。
