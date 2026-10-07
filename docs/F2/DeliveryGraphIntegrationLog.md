# DeliveryGraph 集成支持 Log

2026-10-07，独立分支 `dev/delivery-graph-integration-contract`，原核心 `e66a437be14d40ff7ad70bad2a96e30a1d3db572`，支持包父提交为独立修复 `0836bf7518e4e175d228bd5c0be28fae8ac83463`。最近正常 fetch 核实远端 foundation 仍为 `e828c066ec63689fe5de5d66f650eda33c0086e8`；本地没有主线正在编写的产品适配器。因此只交付主线调用合同与可接入其接口的黑盒辅助器，不冒称测试未提供的代码。

## 实际发现和修复

独立审查发现首版辅助器四处漏洞：拒绝后覆写已有账本行仍 PASS、200 缺 outer_fingerprint 仍 PASS、CLI 导入异常输出秘密哨兵、空身份/未选中状态误匹配。修复为完整 ledger_fingerprint 比较、闭合响应和核心/请求/扩验/外层规范指纹核验、固定错误类型 JSON、不输出异常消息、严格项目/应用身份及防可变 observe 别名。永久 self-test 覆盖全部。

收到主线严格 revision 修复请求后，本线与独审分别复现纯模块历史 receipt 的 Python 相等陷阱；单行 JSON 类型敏感比较修复已先单独发布到 dev/delivery-graph-receipt-types，保留旧 e66。源码严格 Pydantic revision 模型原已拒绝 bool；新问题位于未建模历史回执最终比较。相关三回归 86 项图测试 PASS、Ruff PASS、Mypy 38 files PASS，独审另复跑三项 PASS；细节见 ReceiptTypeFix。

外层 reference 也改为规范 JSON hash 比较，增加核心回执/外层授权 revision 协调篡改重签及持久图 bool revision 场景。协调重签并不成为当前可信快照。主线自行负责规则/check 实现源码与完整 FrozenGoalSpec 内容绑定，纯模块不验证调用方没有提供的材料。

## 支持包验证

Linux x86_64/Python 3.12.14，隔离 `/workspace/Sim2Act-core-test-env`，显式 PYTHONPATH 指向当前 src。

```bash
PYTHONPATH=src:tests python tests/delivery_graph_adapter_contract.py --driver test_delivery_graph_adapter_contract:MemoryDriver
PYTHONPATH=src python -m pytest -q -p no:cacheprovider tests/test_delivery_graph_adapter_contract.py tests/test_delivery_graph_receipt_types.py
python -m ruff check tests/delivery_graph_adapter_contract.py tests/test_delivery_graph_adapter_contract.py tests/test_delivery_graph_receipt_types.py
```

参考 driver：17/17 PASS；辅助器 self-tests 15 PASS（含 9 种错误实现被拒绝、CLI 合成秘密哨兵、空身份与切换响应负例），加独立核心类型回归合计 18 PASS/0 FAIL/0 SKIP/0.60 秒。Ruff PASS，只有既有 Starlette 弃用警告。不是重跑 83 个算法负例充当服务验收；新的场景针对接线、账本、跨应用和响应身份边界。

## 未测与整合

先 cherry-pick 核心修复 0836bf，再 cherry-pick 独立支持提交。支持提交只新增两个 tests 文件及两份文档；不改共享 API/UI/Store、权限、数据库、CI、安装线或已有阶段文档。本分支普通 push 不匹配现有仅 dev/f1-foundation 的 workflow。

真实产品 API、DB 跨进程冷启动、并发提交、跨 principal 请求键隔离、实际 UI generation 策略、Windows、规则源码/FrozenGoalSpec 绑定、扩验检查实际执行与发布签收均 NOT_RUN。MemoryDriver 只用合成数据和 JSON 内存重建，不使用数据库/网络/模型；公开请求不能携带授权上下文，特权 transition 仅供隔离 fixture。主线按 Contract 文档适配真实 driver 后再运行，报告仍明确 product_acceptance=NOT_IMPLIED。

最终独立审查：CLI 17/17 PASS、退出码 0、stderr 为空；self-tests 15 PASS/0.54 秒，确认 9 个不安全 mutant 被拒绝，Contract 文档证据界限明确，无剩余阻塞。审查没有修改文件；本 Log 是结论后的事实记录。

## 主开发服务整合阶段回执（不替代上文支持包历史）

主开发树 `/workspace/Sim2Act-bounded-product-candidate` 已正常快进为 `c51d6c9ca90308f8fddae28752ab04ef72d5085f`；独立集成树同 SHA。既有原始 main/work、旧失败树和远端均未重写。正常 ls-remote 当前 foundation 仍为 `e828c066ec63689fe5de5d66f650eda33c0086e8`，尚未 push。

该组合已纳入显式迁移的可信图账本/独立锚/幂等回执/真实项目 peer 扩验等待项和内部 owner 锁；API 仅 CRUD、没有公开客户端授权上下文或 lock 冒充入口。UI 显式保存/读回/影响规划，无打开应用时自动图网络调用；失落回执保留同键/同 body，完整绑定当前项目、身份、候选、来源及双层指纹。只形成 PLANNING_ONLY / UNKNOWN / PENDING；不会执行补丁、调度检查或发布。

原 peer 缓存/历史授权和锚漏验的真实失败已保留，新后台独审 9 项实际 HTTP/SQLite oracle 限定通过；坏 peer 新键可明确 BLOCKED_PARTIAL，未把合法 peer 的等待项冒称完整 PROJECT 已验。服务 driver 17 个真实黑盒检查全部到达，另冷 Store/撤权及 promoted Report 部分扩展 2 例，共 19 PASS。真实完整 PROJECT fixture 用现有声明式 bounded_agent/合法 CSV peer，不伪造该 agent 的来源任务终态。UI 4 项 HTTP/DOM PASS（图各 29、原 Report 49、原应用流程）；后续仅修权限快照排序，图 2 项重验 PASS。全 src mypy 41 文件通过，后台最后 34 PASS / 1 PG-role SKIP。初始 mypy 14 FAIL、原 UI 和 driver fixture 失败、独审脚本错误、旧 e4 PG 2 FAIL 均独立保留。各冻结、时间与导入见对应 evidence。

组合全量仅准备：实际 1261 collected，独立 source-first 工作副本/清理方案已保存，未运行新版 full 或 PG。核心 `0836bf` 已拒绝历史回执 bool/int 协调篡改；但 `derive_manifest_graph` 原始 source_versions 在建模前仍以 Python dict 相等比较，独立实际 True/1.0 被接受，整体 BLOCK_UPSTREAM_RAW_SOURCE_VERSION。模块所有权按父既定分工交独立核心线，主开发不重复编辑；已请求可正常 fetch 的修复 SHA。收到后正常合入、最终冻结及 SQLite→PG 串行自然终态，实际执行两个最小 CRUD 角色用例，再普通同步既有 dev。

图模型增量 0 / LIVE 0，不新增产品 Principal/Grant。受保护 Chromium 现有 SUID helper 阻塞未解除，HTTP/DOM 不等于浏览器像素通过。Windows 原 900 秒预算仍 NO_GO，不盲重跑；Win11/F1/AT02/owner/语义/完整 P-B 均未签收。所有本阶段资源已自然终态，尚需上游修复、最终 full/PG 和精确普通 push；没有额外上传目的地或恢复包。

## 后续：纯核心 BLOCK 闭合并启动最终全量

父线 `97c7d43f25a259e221ebbca2c5e7cfff0b7ca0b0` 已正常 fetch 并 cherry-pick 为 `a62779342925866c8aebb8307721a66d1a7dd035`，接口不变。根实际 108 核心专项通过；Ruff 全 src/scripts/tests、mypy 全 src 41 文件及 Node 语法通过。独审 exact a627793 的 CSV/Report 10 项原负例/合法版本/规划与历史回执检查通过，全部输入不变；True/1.0 为 INVALID_MANIFEST，合法整数不一致为 VERSION_CONFLICT。此前原始类型 BLOCK 仅在此对应范围关闭，旧报告原文保留；新证据位于 independent-core-final。

最终冻结文档 tip `8c106e9ba7e12d298a5ac3ff5c7d7409e16aa4a7`：实际 collection 1283、238 tracked 源码文件逐字匹配、6 次当前/clean-child 实际导入均来自专属回归树。SQLite 一次全量已经启动，PG 必须待其自然 exit0 后建立。运行中所有 src/tests/scripts/.github 保持冻结；本记录仅 docs，不变更运行源码。终态通过之前不 push、不把旧全量或专项合计冒认本次全量。

CI NO_GO 不再由核心缺陷导致。上次 Windows whole job 已在 912/900 秒取消，工程 741 秒加 setup55、未完成 Edge110、cleanup6 已超过 900；本次 1283 项较其1046新增237项。局部 Linux fixture节省19–21秒并无Windows全分支资格证据，新增用例的完整 Windows 成本未知。既有并行 controller 提案仍缺原job-start marker、整Edge240deadline和owned descendants fault/cleanup资格验证，尚未实施或获准启用。不能以降低断言、加timeout、换容量或盲重跑填补该缺口；最终本地全量后普通push须明确延后自动CI，并单独给出原预算内下一步准备。
