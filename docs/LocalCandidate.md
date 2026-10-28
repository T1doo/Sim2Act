# Sim2Act 本地交付候选（合成 mock）

这是 Linux/Python 3.12 下验证的工程候选。`candidate-manifest.json` 标明精确源码提交及每个文件的 SHA256。包内只有程序、现有安装脚本、锁文件、无凭据模板和固定合成材料；没有数据库、私人配置、历史大证据或模型凭据。wheel 与源码来自同一提交。

## 安装并实际运行

需要 Python 3.12。解压后进入包根目录，新建虚拟环境，按平台的现有锁安装依赖，再安装 wheel。例如 Linux：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --no-deps --only-binary=:all: -r requirements.lock
.venv/bin/python -m pip install --no-deps wheels/<candidate-manifest.json 中实际记录的 wheel 文件名>
.venv/bin/python -m pip check
.venv/bin/python scripts/local_candidate_demo.py prepare-pa --data-dir ./synthetic-demo
.venv/bin/python scripts/local_candidate_demo.py verify --data-dir ./synthetic-demo
.venv/bin/python scripts/local_candidate_demo.py serve --data-dir ./synthetic-demo --port 8000
```

Windows 使用 `.venv\Scripts\python.exe` 和 `requirements-windows.lock`，并必须使用独立的 Windows wheel（或明确的纯 Python 预览）；Linux 原生 wheel 不能仅改解释器路径后复用。本轮云端没有执行 Windows。安装需要既有网络或预备好的本地 wheelhouse，候选不捆绑第三方依赖，不是完全离线安装包。演示本身只访问 loopback HTTP，模型响应固定为 `httpx.MockTransport`；不需要 Node、浏览器自动化或测试目录。

`prepare-pa` 只能写入不存在的新目录，现有目录会拒绝，不删除数据。明确调用一次后依次完成：CSV 数字列求和 30 → 内部 Release/实例/真实 AppRun；自然 P-A mock 生成与明确保存；在空实例以第一份新材料和已保存 Goal 经逐次 review/commit 运行得 v1，再在同一应用/Release/实例提交另一材料和 Goal 得 v2，保留首份 typed 行及 artifact。首次使用材料、Goal 和 recipe 固定为首包 0f 的合成案例，未先执行原材料 Run。共 3 条生成、2 条 P-A 运行固定 mock 响应，真实请求为 0。

候选按正常 Worker 服务生命周期等实际终态，`Worker.once()` 的布尔值仅是进度，不代表完成。服务只调用既有 Worker/Store.claim，保持每 Run 原接受时钟及最多 300 秒预算、普通30秒lease（新P-B可显式签署一次有限120秒SQLite结算合同）和普通1秒服务间隔；到绝对截止、出现失败/阻塞/未知状态或意外异常即停止。它不会重发提交、resume、清除 unknown 或修改 Run 状态。若原机制合法回收过期 owner 后重领，每次 claim/fence/WORKER_LOST/RECONCILED 都在回执中公开，不再限定只一次 claim，也不将它冒充旧 F9 的复现或修复。每个 `worker-service-<Run>.json` 保存原接受时钟与逐次服务状态，`worker-receipts.json` 保存真实 ledger。运行中仅观测已知合成 Run 的 metadata 标量，终态才执行完整 HTTP 结果读取。

每轮服务前后检查隔离库中没有其他 active Run，并核实际本 Worker 领取过的全部 Run ID；发现非目标任务立即停止并保留回执，不私改 claim 选择器或隐藏旁路工作。这个入口只用于自己全新创建的合成数据目录。

旧 `prepare` 命令仍提供此前范围的原材料 P-A → 提取 P-B → 新材料逐次 P-B 演示，使用另一个全新目录；它不代替 `prepare-pa` 的新材料 P-A 验证。二者原始执行范围由各自交付报告记录，不把另一条链的成功改签为本条通过。

`verify` 在独立进程重新打开同一目录，只 GET 已有三个结果和同一 Run 人工验收状态；对于 `prepare-pa` 逐项核对同实例 v1/v2 artifact 和原 typed 行摘要，比较全库持久行保持不变；不启动 Worker。原始合成回执保存在该演示目录：`http-receipts.json`、`worker-receipts.json`、`worker-service-<Run>.json`、`mock-receipts.json`、`demo-receipt.json`、`cold-read-receipt.json`。失败时保留当次数据，不覆盖后重试。

`serve` 只向 `127.0.0.1` 提供已有结果的只读普通页面，不能生成新任务或提交人工决定。公开合成登录值：`public-synthetic-local-candidate`。选择 `SYNTHETIC MOCK local candidate` 项目，在已保存应用目录选择应用，再选实例和已有 Run 查看结果及人工验收状态。自然语义仍 `NOT_RUN`，人工验收仍 `PENDING`。Ctrl+C 只停止本服务器并保留数据。重新运行 `serve` 不重新生成结果。需要新一次演示时选择另一个新目录。

## 普通安装及真实模型边界

普通使用继续遵循 [安装文档](Installation.md) 和既有 `Setup/Start/Status/Stop` 脚本，要求显式 PostgreSQL 应用角色配置及单独迁移角色；不会从本演示自动切换。本包默认保持合成预览，模板内 `LOCAL_PASSWORD` 是占位符。不要将公开演示身份用于真实项目。

2026-10-28 已接入固定免费 `intern-s2`／原 Intern endpoint 的可信账户来源与有限执行门；用户的零费用确认有效，不要求重新泛化授权。已有独立真实 Source/Cold 提取成功记录；最新完整控制链使用7个有限 Mock、真实SQLite事务并保存结果，见 [云端闭环证据](https://github.com/T1doo/Sim2Act/blob/cc0616519adabb21d89cdc7555ffbdb042152669/docs/evidence/cloud-frontier-structure-20261028/README.md)。这两组证据不能合并为真实模型全链。当前包仍明确为合成候选，不含token、不自动启用LIVE。正式外部执行仍需要实际 PostgreSQL应用角色配置、选定principal/project/trial及对应精确软件/材料/预算审批；缺少这些具体部署事实时不能拿合成身份替代，也不能再泛称免费模型未授权或接入未实现。
已有通用传输还要求明确 `SIM2ACT_MODEL_MODE=live`、`SIM2ACT_LIVE_ENABLED=true`、`SIM2ACT_MODEL=intern-s2`、私下 token、quota subject/RPM；这些只是已有通用条件，不构成自然能力授权。单 Run 上限仍 4 requests / 4 tools / 1 repair / 64000 tokens / 1024 output / 300 秒，只可收紧。不要在包或报告中放入真实值。

## 验证范围

本候选的实际执行结果由交付报告另行记录；说明文字不代替执行回执。未执行 Windows、PostgreSQL、原生浏览器、真实模型/场景/人工语义验收、远端 CI 或部署。

前一个 `0f0819a6` 包的首次全链尝试失败：P-A 新材料逐次运行一次 claim 后仍 `RUNNING`，只有 resource.read 完成、没有模型 attempt；原数据和回执保留，最初异常/长事务原因未定。此前 `c9` 包仅验证原材料 P-A + 新材料 P-B，不能当作该功能完成。本轮精确 0f 新库对照首次 per-use 自然成功、一次 Worker.once 22.48 秒，因此未自然复现原失败。本候选恢复明确的新材料 P-A 路径并调整正常 Worker 服务生命周期；不是生产 lease/guard 修改或已确定原最初异常的修复，不把后续成功改签为旧包通过。实际新候选执行结果仍以交付报告和原件为准。

此前 `986799d` 的锁验证保持原分期：安全批次 45 PASS / 1 FAIL，随后定向 2 PASS（含重叠）及独立新增模块 9 PASS；不能称一次整批全绿。自然双 Run 成功但没有触发新恢复分支，旧 F9 具体失败时序没有复现。本候选不重跑或扩展该故障矩阵，也不补称旧满盘环境未落盘的独审报告。

维护者可在干净固定提交上用现有 setuptools wheel 构建流程制作同类包：`python scripts/package_local_candidate.py --output ./dist/candidate-new`。该命令只读取 Git 明确白名单，不收集本机配置/数据；只构建，不安装、启动或部署。

### 新开发版本的 Windows 预览装配

现有 `package_windows_portable.py` 可将上述精确候选装入此前已下载、已锁定的 Windows 运行库。新版本必须显式提供同一次构建的 `--candidate-manifest`，并在本次独立 inputs 文件中将 `product_commit` 设为该清单的完整 `source_commit`；保留原 Python、依赖及其摘要，不修改旧输入或旧成品。示例：

```sh
python scripts/package_windows_portable.py \
  --inputs ./current-portable-inputs.json --assets /path/to/existing-frozen-assets \
  --app-wheel ./dist/candidate-new/<匹配 Windows 的实际 wheel 文件名> \
  --candidate-manifest ./dist/candidate-new/candidate-manifest.json \
  --output ./dist/new-preview.zip
```

装配前核对完整提交、wheel 摘要、全部已打包 Python/网页/数据文件字节及文件集合，拒绝混入、遗漏和重复项；新profile包含全部受软件资格约束的C源码；两份实验C只作源码资源，不自动启用。原生输出按单独白名单与摘要核对，Windows拒绝Linux `.so` 或标签不符的wheel。新版清单摘要写入包内 manifest。候选清单须来自已核实的精确 Git 构建：这些校验只证明包与清单一致，不会把任意手写清单认证成可信源码。未传清单只允许原固定旧提交及旧 wheel，不能借旧 wheel 改标新版本。

这一步只装配、不下载、不安装、不执行 Windows，也不授予正式软件、账户或模型资格。现有运行库仍是已标记 superseded 的 Python 3.12.10；只能保留其原隔离合成预览边界，不能据此称长期正式交付。实际 Windows 启动/退出、像素、真实账户、G0及人工语义仍须各自有效证据，装配状态为 `NATIVE_HOST_BUILD_REQUIRED_NOT_WINDOWS_EXECUTED`；默认入口是待构建的 `Sim2Act.exe`，不回退浏览器。构建与原生窗口验收参见 `scripts/windows/README.md`，只有显式开发预览保留浏览器。


构建命令现在从同一干净Git提交包含 `setup.py`，仅使用已安装 `setuptools==82.0.1`，以 `--no-index --no-build-isolation --no-deps` 禁止隐式后端/依赖下载。默认原生候选必须实际含两份受支持扩展，缺少任一则拒绝成包；只做回退预览需显式 `--python-preview`。清单记录实际文件名、Tag、Root-Is-Purelib、构建平台及原生文件SHA；构建不等于运行验收，重建产生的新二进制仍需验证。本轮已验原生字节只属于云端Linux/CPython3.12，Windows需自行有界构建/测试已有工具，不下载新工具或改权限。

完整云端通过仍余量很窄：两次Cold结算118.04/115.48秒，分别在120秒界限内；G0 41.39/43.64秒超过旧30秒。自然语义NOT_RUN、owner PENDING，正式发布关闭；不能将一次工程通过扩大为生产稳健性或跨平台验收。

2026-10-28 新冻结源码72c523608004244d0be94df0ecaf4e4f7f0b00b5的完整合成P-B控制链已在真实时钟SQLite上以7次Mock保存最终结果，两次事务103.84/98.38秒，完整G1 67.32/62.07秒；参见 [新完整证据](evidence/cloud-raw-mapping-20261028/README.md)。G0 owned公共链仍为显式实验候选；G1新路径每次完整比较当前输入并保留原canonical回退。新包身份和Windows宿主生命周期须单独验收，不能沿用旧6742包称新版本已运行；旧30秒、正式PG/live与语义/owner仍未通过。
