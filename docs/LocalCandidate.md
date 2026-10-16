# Sim2Act 本地交付候选（合成 mock）

这是 Linux/Python 3.12 下验证的工程候选。`candidate-manifest.json` 标明精确源码提交及每个文件的 SHA256。包内只有程序、现有安装脚本、锁文件、无凭据模板和固定合成材料；没有数据库、私人配置、历史大证据或模型凭据。wheel 与源码来自同一提交。

## 安装并实际运行

需要 Python 3.12。解压后进入包根目录，新建虚拟环境，按平台的现有锁安装依赖，再安装 wheel。例如 Linux：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --no-deps --only-binary=:all: -r requirements.lock
.venv/bin/python -m pip install --no-deps wheels/sim2act-0.1.0-py3-none-any.whl
.venv/bin/python -m pip check
.venv/bin/python scripts/local_candidate_demo.py prepare --data-dir ./synthetic-demo
.venv/bin/python scripts/local_candidate_demo.py verify --data-dir ./synthetic-demo
.venv/bin/python scripts/local_candidate_demo.py serve --data-dir ./synthetic-demo --port 8000
```

Windows 将 Python 路径改为 `.venv\Scripts\python.exe`，依赖文件用 `requirements-windows.lock`；本轮未执行 Windows。安装需要既有网络或预备好的本地 wheelhouse，候选不捆绑第三方依赖，不是完全离线安装包。演示本身只访问 loopback HTTP，模型响应固定为 `httpx.MockTransport`；不需要 Node、浏览器自动化或测试目录。

`prepare` 只能写入不存在的新目录，现有目录会拒绝，不删除数据。明确调用一次后依次完成：CSV 数字列求和 30 → 内部 Release/实例/真实 AppRun；自然 P-A mock 生成与明确保存 → 新材料和已保存 Goal 的逐次 review/提交；从成功 P-A Run 审阅提取 P-B → 保存内部 Release/实例 → 第三份材料和 Goal 的逐次 review/提交。各 Run 只执行一次原 claim；没有恢复或重新提交失败任务的循环。自然生成共 3 条、P-A/P-B 运行各 1 条固定 mock 响应；真实模型请求为 0。

`verify` 在独立进程重新打开同一目录，只 GET 已有 CSV/P-A/P-B 结果和同一 Run 人工验收状态，比较全库持久行保持不变；不启动 Worker。原始合成回执保存在该演示目录：`http-receipts.json`、`worker-receipts.json`、`mock-receipts.json`、`demo-receipt.json`、`cold-read-receipt.json`。失败时保留当次数据，不覆盖后重试。

`serve` 只向 `127.0.0.1` 提供已有结果的只读普通页面，不能生成新任务或提交人工决定。公开合成登录值：`public-synthetic-local-candidate`。选择 `SYNTHETIC MOCK local candidate` 项目，在已保存应用目录选择 CSV、自然 P-A 或 P-B，再选实例和已有 Run 查看结果及人工验收状态。自然语义仍 `NOT_RUN`，人工验收仍 `PENDING`。Ctrl+C 只停止本服务器并保留数据。重新运行 `serve` 不重新生成结果。需要新一次演示时选择另一个新目录。

## 普通安装及真实模型边界

普通使用继续遵循 [安装文档](Installation.md) 和既有 `Setup/Start/Status/Stop` 脚本，要求显式 PostgreSQL 应用角色配置及单独迁移角色；不会从本演示自动切换。默认配置没有批准模型消费，模板内 `LOCAL_PASSWORD` 是占位符。不要将公开演示身份用于真实项目。

真实自然 P-A/P-B 当前缺少可执行的专用 LIVE 批准门与跨 Run 总预算账本，状态为 `BLOCKED / NOT_IMPLEMENTED`，真实模型额度为 0。仅填 token 或打开通用 live 开关不能启用它。后续最低前提是：用户明确批准精确软件、模型、材料/Goal、各生成/运行范围和总次数/token/费用上限；实现并验证自然族的专用批准/总账门；私下配置受支持的 `intern-s2` 凭据、PostgreSQL 角色和受限预算，再重新申请有限实际运行。不能沿用其它 CSV/字面任务批准。本候选不配置、不调用、不扩展这些权限。

已有通用传输还要求明确 `SIM2ACT_MODEL_MODE=live`、`SIM2ACT_LIVE_ENABLED=true`、`SIM2ACT_MODEL=intern-s2`、私下 token、quota subject/RPM；这些只是已有通用条件，不构成自然能力授权。单 Run 上限仍 4 requests / 4 tools / 1 repair / 64000 tokens / 1024 output / 300 秒，只可收紧。不要在包或报告中放入真实值。

## 验证范围

本候选的实际执行结果由交付报告另行记录；说明文字不代替执行回执。未执行 Windows、PostgreSQL、原生浏览器、真实模型/场景/人工语义验收、远端 CI 或部署。

此前 `986799d` 的锁验证保持原分期：安全批次 45 PASS / 1 FAIL，随后定向 2 PASS（含重叠）及独立新增模块 9 PASS；不能称一次整批全绿。自然双 Run 成功但没有触发新恢复分支，旧 F9 具体失败时序没有复现。本候选不重跑或扩展该故障矩阵，也不补称旧满盘环境未落盘的独审报告。

维护者可在干净固定提交上用现有 setuptools wheel 构建流程制作同类包：`python scripts/package_local_candidate.py --output ./dist/candidate-new`。该命令只读取 Git 明确白名单，不收集本机配置/数据；只构建，不安装、启动或部署。
