# 修改后的固定 CSV 版本复用：有限工程证据

基线 `d96e20e0f82793c5fe460d408ca48ff69fc0e01f`，分支 `dev/project-column-revalidation-20261011`。本轮接续已经完成的有限项目列修改和内部版本，只补原 F2-T03 / AT10 的有限 CSV 新材料及无内容逻辑复用。范围见 [实现前合同](../../F2/ProjectColumnMaterialReuse20261011.md)。root 是唯一产品写入者；独审只读产品，探针和夹具在 `/tmp`。

直接复用保持项目已批准的默认列（本轮样本为 quantity），另一份 CSV 必须同 owner/project、当前授权、已 derive、真实 ID/hash 不同且具有同名有限数值列。若需选择另一列，须先在旧来源有效时明确授权无内容三步逻辑，再对当前新目标精确绑定。公共逻辑无旧列名、overlay、CSV 内容/hash、旧输入输出或 Run；复用不读取旧资源、Operation 或 Run.result/context。新目标版本的默认从实际目标计划和 aggregate 回执重建，旧来源和结果保留。

实际执行沿用注册 read→aggregate→report Worker、冻结合同、独立 CSV/Fraction 复算及 typed 原子提交。计划、执行、新版本和实例各自明确确认。固定来源的授权或新材料计划接受不明，只用原逻辑 ID/原 plan key GET 恢复。页面用来源实际 Run 的 plan fingerprint、完整计划和真实回执识别材料来源；重签公开 Release/Instance 指纹不能替换实际计划或默认列。没有新增执行器、身份、Grant、业务表、模型或正式发布入口。

最终核心运行 `final-core.log/xml` 已完成 15 PASS / 0 FAIL / 0 SKIP，619.23 秒。其中 11 后端与 4 进程内 HTTP ↔ IPC ↔ 离线 JSDOM 病例；页面实际 16/21/23/22 检查，共 82。每个病例加载 index.html 与 15 个仓库 JS 的实际 SHA256，均与冻结文件一致。这些页面检查包含在四个 pytest 病例内，不另算用例。

最终作者集合为 269 个唯一选定节点：SQLite **262 PASS / 7 SKIP / 0 FAIL / 0 ERROR**，另 2 个真实旧源码升级测试明确 deselected。7 个 SKIP 中 5 个需要显式隔离 PG 应用角色，2 个缺少指定真实旧源码归档，逐项原因保存在 [实际汇总](final-validation.json)。核心 15 PASS / 619.23 秒，关联 247 PASS / 7 SKIP / 1801.09 秒；两套并行运行，时间不相加为墙钟。`final-collection.log` 与两个完整 JUnit 的 269 个节点精确一致，没有未完成占位。

`frozen-before.json` 与 `frozen-after.json` 的 76 个 Python/JS/HTML 源码/页面文件及 238 个测试代码文件，共 314 个，逐字节一致。另 32 个 CSS/结构化夹具文件独立对照基线 HEAD 完全相同，未混入这 314 个冻结计数。产品修改仅五个源码文件，另新增三个测试文件。关联的四个原项目版本 HTTP/JSDOM 病例 27/26/25/25 检查、共 103 检查与各 16 页面文件哈希也实际通过，包含在 254 个关联 pytest 病例内；与新切片 82 检查分别保存，见两个 `final-*-ui-summary.json` 和 `final-artifacts/`。运行结束后只更新说明和证据，未改源码或测试。

独审 [最终报告](independent/FINAL_REVIEW.md) 为 LIMITED PASS：后端实际 13 PASS / 0 FAIL / 0 SKIP；最终仅 JS 来源门修改，后端按 75/76 个精确同字节源码桥保留，**未重跑后端**。最终 fresh 页面实际 16 PASS / 0 FAIL / 0 SKIP，覆盖七种重签 HTTP 200 回包，加载 15 个真实 JS，独审 314 文件前后不变。独立 Fraction 输入、删除旧源后的 SQL 读取追踪、typed 插入后精确到期回滚、三条实际 operation 后正式撤销拒提交均有实证。两个停止内部 Run 的实际状态为 WAITING_RESOURCE / GRANT_REVOKED / null result，原 units=40 和 data_version=1 保留。独审数不加到作者 pytest 数；31 个原始报告、脚本、日志和 JSON 均按 [清单](independent/review-manifest-final.json) SHA256 归档，无夹具数据库。

失败历史完整保留：作者首轮缺 target 图、二轮撤权后复用旧 derive key、页面首轮缺已有 jsdom 的 NODE_PATH、三轮在 API 建立后修改 Settings 的预算夹具错误，见 `prior-history.json` 和原始 `.log/.xml`。独审最初 UI 10 PASS / 2 FAIL 属于同一个实际产品漏洞：同时换普通-looking plan key 和 default 后重签公开指纹可绕过来源分类。修后先绑定实际来源 Run 和 plan fingerprint，原两例及另一个真实存在但不属于该 Run 的普通计划均被拒，fresh 16 项通过。旧脚本、失败 JSON、后端小数字符串断言/冻结层级/状态读取夹具错误均保留。修复前已中断的作者 8 PASS 核心、115 PASS/3 SKIP 关联套件及旧四页面 PASS 不计最终结果；未完成 JUnit 占位不算 PASS。

全树 Ruff 10 个错误、mypy 5 个错误与基线逐条一致；改动 Python Ruff 通过，Node 语法通过。全树静态检查未全绿。原始测试/独审输出保持字节，包括其原有行尾空白；源码、测试和说明的 diff 检查单独核对。

环境见 [实际版本](environment.json)：Linux，Python 3.12.14、SQLite 3.53.1、Node 24.19.0、JSDOM 26.1.0。HTTP 为 TestClient 进程内请求，页面为离线 IPC，实际 Worker 的 NoModel 在调用 provider 时直接失败；真实模型请求为 0。

NOT_RUN：PostgreSQL/角色、Windows、原生浏览器/视觉、旧源码升级、真实/付费模型、完整 P-A/P-B/AT10、人工语义/owner 验收、远端 CI、部署。未知/语义依赖仍不获得安全改写资格；semantic UNKNOWN、owner PENDING、正式发布关闭。本轮没有重试被拒浏览器路径、扩大网络/安全权限、配置凭据或修改 main/coredev。

复现当前有限集合，需已有测试环境与 jsdom，不安装依赖或连接模型：

```bash
NODE_PATH=/workspace/node-tools/node_modules .venv/bin/pytest -q \
  tests/test_project_column_material_reuse.py \
  tests/test_project_column_material_ui.py \
  --basetemp=/tmp/project-material-reproduce-core \
  --junitxml=/tmp/project-material-reproduce-core.xml

NODE_PATH=/workspace/node-tools/node_modules .venv/bin/pytest -q \
  tests/test_csv_material_reuse.py tests/test_csv_logic_reuse.py \
  tests/test_csv_dag_instances.py tests/test_csv_report_dag_instances.py \
  tests/test_csv_two_sum_instances.py tests/test_project_column_versions.py \
  tests/test_project_column_versions_ui.py tests/test_csv_dag_version_switch.py \
  tests/test_csv_dag_boundaries.py tests/test_csv_dag_proof_guards.py \
  tests/test_internal_lifecycle.py \
  -k 'not actual_50b_source_upgrade and not actual_fab_source_upgrade' \
  --basetemp=/tmp/project-material-reproduce-regression \
  --junitxml=/tmp/project-material-reproduce-regression.xml
```
