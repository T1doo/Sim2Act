# 本地交付候选原始证据

限定交付源码 `c9e9f3fc9787350d1e7997860234694b270a6a7f`，产品基线 `986799d766e98744e29e038543299af13785ea36` 不变。结论及未验证项见 [交付报告](../../F2/LocalDeliveryCandidate20261016.md)，运行命令见 [候选说明](../../LocalCandidate.md)。本目录不进入候选 ZIP；包内不含本机路径、配置、数据库或日志。

## 最终范围的实际通过

| 原件 | 证明范围 |
| --- | --- |
| `preflight-and-source-freeze.json` | 单 worktree、clean c9、远端基础/主分支、磁盘、8fc 祖先；src 不变 |
| `candidate-v2-manifest.json`, `independent-c9-package-proof.json` | 固定 Git 白名单、134 包文件/133 manifest 项、113 wheel 产品文件同源 |
| `wheel-installed-origin.json`, `v2-install.log`, `v2-wheel-install.log`, `pip-check-v2.log` | 新 Python 3.12 venv、锁定依赖和实际 wheel 安装；113 文件匹配，未加载 checkout src |
| `v2-demo-prepare.log`, `v2-http-receipts.json`, `v2-worker-receipts.json`, `v2-mock-receipts.json`, `v2-demo-receipt.json` | 实际 HTTP/正常 Worker：CSV=30；P-A 原材料；P-B 第三材料逐次使用；各 v1；4 次单 claim；5 条 mock；0 真实请求 |
| `v2-demo-verify.log`, `v2-cold-read-receipt.json` | 独立进程新 Store/API 冷读 3 结果及同 Run 人工验收；全库持久行不变；0 Worker/模型 |
| `v2-serve.log`, `v2-serve-smoke.log`, `v2-serve-smoke.json` | 真实自有 loopback 服务：8 GET 200、POST 405、SIGINT 退出 0；原生浏览器 NOT_RUN |
| `root-c9-final-light.xml/.log`, `independent-c9-light.xml/.log` | 同 10 项边界轻测各 PASS，重复执行不相加为 20 |
| `independent-c9-review.md`, `independent-c9-review-manifest.json` | c9 静态、轻测及包同源有限独审，当时完整链尚待执行 |
| `independent-c9-actual-review.md`, `independent-c9-actual-proof.json`, `independent-c9-actual-verifier.py` | 随后完整原回执/已安装字节/只读 DB 增强核查，无剩余限定交付阻断；未重跑 Worker |
| `final-runtime-verification.json` | 根实际退出码及上述执行范围摘要；不代替原回执 |

`v2-build.log` 仅为本轮 setuptools wheel 构建原件，不在 ZIP 中。安装依赖用了当前既有网络；演示仅 loopback/MockTransport，不是捆绑依赖的完全离线安装包。

## 保留而不改签的早期证据

- `root-light-wip-6p1f.xml`：新增测试最初错误期望项目列表返回对象，实际为数组；该断言修正后最终 10 项通过。
- `root-light-final-10p.xml`、`root-light-c9-10p.xml`：更早来源阶段的轻测原件；最终精确源以 `root-c9-final-light.xml` / 独审 c9 为准，不累计重复分母。
- `candidate-manifest.json`、`independent-package-proof.json`、`independent-light-final-10p.xml/.log`、`independent-0f-review.md`：首包 0f 的静态/10 轻测/包同源通过，当时完整链待完成。不能覆盖其后实际完整 FAIL。
- `failed-0f-prepare.log`、`failed-0f-http-receipts.json`、`failed-0f-worker-receipts.json`、`failed-0f-mock-receipts.json`、`failed-0f-pa-readonly.json`：首包完整链 FAIL，P-A 新材料 per-use 单 claim 后 RUNNING、只有 resource.read、无 runtime attempt；原演示目录仍保留。未复用或重放该 Run，具体根因未确定。
- `independent-scope-adjustment.md`：收窄到原材料 P-A + 新材料 P-B 是演示范围调整，不是上述失败修复。最终候选的 P-A 新材料 per-use 明确 NOT_RUN。
- `independent-0f-independent-report.md`、`independent-0f-csv-prepare-proof.json`、`independent-0f-csv-cold-proof.json`、`independent-0f-ordinary-pg-boundary.json`：独立前包 CSV 与第二进程冷读/普通 PG 拒绝边界；加载解包源码，未从 wheel 执行自然链。
- `independent-baseline-review.md`：开始阶段既有 PG/SQLite mock、LIVE 批准及白名单边界。该初核不是产品新执行证明。

前轮 45P/1F + 定向 2P（有重叠）+ 独立 9P，以及自然双 Run 未触发新恢复分支、旧 F9 未复现、旧满盘报告未落盘，均保持原事实；本轮没有补跑故障矩阵。Windows、PG、真实模型/语义/人工验收、原生浏览器、远端 CI、部署均未执行。仅公开合成身份，无真实凭据。

本目录每个文件（本清单本身除外）的 SHA256 见 `SHA256SUMS`。交付 ZIP 的摘要另见 `deliverables/local-candidate-20261016/SHA256SUMS`。
