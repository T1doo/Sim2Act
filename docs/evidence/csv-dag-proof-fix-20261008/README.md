# 固定 CSV DAG：两项 P2 修复候选

源码及测试冻结 SHA：`4c7d81b80d2d81ce9471b185b09ac34fd7c74740`。候选分支 `dev/csv-dag-proof-fix-20261008`，基于冻结 DAG `5a5543c902fbb78dd91c28c98386af51fb24dd67`；修复源码提交 `059a875025c821839e800604763612a0c7bfaef0`，后续 `4c7d81b` 只加强真实时钟测试。证据提交不改变源码/测试。独立审查 **PENDING**，未并入 dev，未发布。

父线程报告原候选 e8b1ed4 在独立审查两后端均为 25 PASS / 4 FAIL：最终回执读取跨过 lease/deadline 后仍成功；持久化 count=true 与整数1错误相等仍被认可。该审查的原始文件不在本环境，不冒认下面的同作者证据为独立验收。

## 实际修复

仅修改现有 `src/sim2act/csv_dag.py`，增加 `tests/test_csv_dag_proof_guards.py` 的24个对抗病例。最终成功事务在回执读取后重新核 fencing、lease、停止状态、真实时间和当前设置/冻结合同/声明预算三者最小值。单步事务将待提交操作计入工具预算；失败不留下半个操作、计数或成功结果。

实际持久化输出经过严格 JSON schema 校验；整个回执、输入 intent、计划、接受回执和最终结果用类型敏感指纹对照独立重算的期望。整数、布尔和浮点相等值不能互换。Run 数量/有限时间另作检查，同时保留既有损坏上下文的安全失败记录路径。合法旧记录原样可读、可恢复，不重写旧版本。

## 本轮冻结验证

九文件223个唯一病例，范围在 `runner.py` 和 `summary.json`：

| 后端 | PASS | SKIP | FAIL/ERROR |
| --- | ---: | ---: | ---: |
| SQLite | 220 | 3：PG应用角色子进程专用 | 0 |
| 自有 PostgreSQL 17.9 | 222 | 1：SQLite历史NUL专用 | 0 |

24个新增病例两端全通过。真实 wall deadline 病例记录进入/退出回执读取时间，真实等待1.25秒，断言进入时未过期、退出时已过期，然后验证整个数据库快照回滚。count=true、1.0、"1" 不改输出指纹，实际 API GET 拒绝且读不写；另覆盖预算/修订/接受版本等类型篡改、部分与完整冷恢复、合法旧回执。原所有测试文件、依赖锁、脚本与 workflow 逐文件保持不变。

实际 loopback HTTP + 原产品 JS/DOM 每后端保留 DAG24、列补丁20、CSV图29、Report图29项检查及加载源码SHA256，见 `sqlite/`、`pg/`。这是 jsdom 工程证据，原生 Windows/Edge **NOT_RUN**。Ruff src/scripts/tests PASS，mypy50源码文件 PASS；原 Windows900 / Edge240 / Node150 标准保留，旧720或1591结果不作为本改动证明。仅既有 Starlette TestClient 弃用警告，未为此改依赖。

两后端 `*-provenance.json` 保存运行前后全部 src/tests 哈希及冻结SHA，均 returncode=0 / source_unchanged=true。旧5a归档源码（与e8源码相同）用059检查点24病例各复现19个预期FAIL、5PASS，见 `baseline-*`；该驱动真实时钟宽限为0.5/0.75秒，最终4c加强为1/1.25秒并明确交叉标记。旧驱动原文和模块路径/哈希单独保存，不混作最终新测试通过。最初阶段78PASS4FAIL3SKIP的失败及当时未运行项保留在相邻 checkpoint 目录；放置检查的修正已在最终回归覆盖。

所有原始日志/JUnit以 `.gz` 无损保存，原始字节数与SHA256见 `raw-log-preservation.json`。`cleanup.json` 记录24个自有临时路径清理；PG test schema/role均0，network=none、无端口映射，自有容器/镜像/匿名卷已移除。`.venv` 开发环境保留。

## 用户复现

按既有安装说明使用锁定开发依赖和 Node/jsdom；只使用自己的隔离临时数据库，保持 `LIVE=0`、MOCK。先检出本候选，勿在 main 实现：

```bash
git fetch origin dev/csv-dag-proof-fix-20261008
git switch --no-track -c review/csv-dag-proof-fix FETCH_HEAD
LIVE=0 SIM2ACT_MODEL_MODE=mock SIM2ACT_LIVE_ENABLED=false .venv/bin/python -m pytest -q tests/test_csv_dag_proof_guards.py --basetemp=/tmp/your-owned-proof-tests
```

完整定向九文件命令从 `runner.py` 读取（223病例）。运行 UI 项前给 `NODE_PATH` 指向自己安装 jsdom30.1.2 的 node_modules。PG再显式提供 `SIM2ACT_TEST_DATABASE_URL` 指向自己的隔离库；既有 fixture 创建/删除独立 test_* schema，应用角色测试还创建/删除受限 test_app_* role。不得传生产/用户数据数据库。证据 runner 固定了作者本次临时路径，复现时应复制到自己的输出目录并调整 fixture/NODE_PATH，勿覆盖冻结证据。

页面演示沿用 [原 DAG 指南](../../F2/FixedCsvDagQuickstart.md) 与 [列绑定指南](../../F2/ColumnBindingPatchQuickstart.md)。count类型篡改是自有测试库对抗病例，无产品业务写入口。本候选没有改页面、任意代码执行、真实模型调用或业务写权限。

后续：交同一独立审查者验证两项 P2；接线扩展停在本地 `0ec1f291d51356d3968c6761d7d80b803e97a65b`，未推送，需另行取入本修复再验证。正式发布关闭，semantic UNKNOWN / owner PENDING / publishable=false；真实任务 gold、通用 P-B、人工签收未完成。本轮无 dev/main 合并、强推、凭据配置、安全权限扩大、部署或新CI。
