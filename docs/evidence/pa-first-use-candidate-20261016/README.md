# P-A 首次新材料候选证据

执行源冻结 `fc69c863f57f0cdf9a8dbfeaeb5fdc567e42c675`；主报告为 [PAFirstUseCandidate20261016](../../F2/PAFirstUseCandidate20261016.md)。本目录为本轮必要原件的逐字副本，`SHA256SUMS` 覆盖除自身之外的每个文件。没有数据库、venv 或私人配置；本地原始 DB 保留于报告列明的 checkout 外新目录。

## 原失败与精确对照

- `original-failed-pa-run-readonly.json`：首包 0f 失败 Run 的既有原始只读捕获；`old-failure-preservation.json`：本轮五组持久行及 DB hash 前后不变，未重放或改写。
- `original-readonly-causal-review.md`、`original-readonly-timeline.json`：原失败同步 Worker/lease/退场路径的有限独审；最初异常未知，不能签具体锁根因或旧 F9 同因。
- `local_candidate_demo.py` 是 **Git 0f 原脚本**，不是当前 fc69 脚本；`original-0f-mock-fixtures.json` 是它的固定 fixture。`reproduce.py` 只在新库执行原前缀至首次 P-A per-use，使用先前全新安装的 0f wheel，不执行原失败 Run，不扩到 PB。它记录本机明确绝对路径；不是候选安装命令。
- `baseline-first-pa-outcome.json`、`baseline-first-pa.log`：精确新库对照一次 PASS/v1；`baseline-first-pa-trace.json.gz` 可解压成完整 JSON，原始字节数及 SHA 见 `baseline-trace-manifest.json`。委托原操作的 instrumentation 只记录耗时/异常，不改时钟、等待、业务返回或状态。
- `baseline-trace-independent-summary.json`、`independent-regression-design.md`、`service-proposal-review.md`：独立只读分析及最小首次 0→1→2 验收设计。一次基线成功未复现旧最初失败。

## 冻结源码、轻测和包

- `source-provenance.json`：单 checkout、单仓库写入者声明、实际 fc69、祖先、src 不变、默认网络远端读取、原远端 refs 和磁盘；是归档前时点，不代替最终推送回执。
- `light-service-isolated.xml`：作者最终轻测 21 PASS（此后仅注释/指南冻结）；`independent-light.xml/.log`：冻结 fc69 上独立执行同 21 PASS。独特用例数为 21，不相加为 42。受控多轮/fence3 只证明脚本合同；实际 CSV 两 queued 负例验证不领取非目标。
- `independent-frozen-review.md`、`independent-frozen-review-manifest.json`：冻结源有限独审及原件 hash。落盘时新自然链为 PENDING，保留该时点，随后由实际回执独审补充，未覆盖旧报告。
- `candidate-build.log`、`candidate-manifest.json`、`independent-package-proof.json`：新包构建/131 Git 文件及 113 wheel 产品文件同源核验。构建日志仅在证据中，不进入候选 ZIP。

## 全新安装和实际 P-A v1/v2

新包根 `/workspace/pa-use-running-clean-install/Sim2Act-local-candidate`；新数据目录 `synthetic-pa-demo`。没有加载 checkout src、旧失败 DB 或预置结果。

- `install.log`、`wheel-install.log`、`pip-check.log`、`runtime-origin.json`：全新 Python 3.12.14 venv、锁依赖及 wheel、实际导入来源。
- `prepare-pa.log`：实际 CLI 退出 0；`actual-demo-receipt.json` 保存 CSV 和首次 P-A base0→v1、第二 P-A base1→v2 的 Run/实例/结果 hash/typed 整行摘要。
- `actual-http-receipts.json`：实际显式材料、Goal、per-use review/commit 及同意图重复提交；`actual-mock-receipts.json`：5 条固定 MockTransport，0 真实请求。
- `actual-worker-receipts.json` 和四个 `actual-worker-service-<Run>.json`：每 Run 原接受时钟、前后 metadata、真实 claim/fence ledger。此次全部 1 turn / 1 claim / fence1，没有实际重领或自然恢复分支。
- `verify-pa.log`、`actual-cold-read-receipt.json`：独立进程实际 PASS，冷读 CSV/PAv1/PAv2，artifact、typed 行摘要及全部持久行不变；0 Worker/模型。
- `independent-actual-receipts-review.md`、`independent-actual-receipts-proof.json`、`independent-actual-receipts-verifier.py`：独立只读核安装字节、固定案例和实际 DB/回执。独审没有再跑自然 Worker；证明此前实际结果，不替代根执行。

## 只读 serve 的分期结果

- `serve-smoke.py`、`serve.log`、`serve-smoke.log`：首个外部 15 秒启动探针 **FAIL**，导入时被探针 SIGINT 清理；曾与冷读重叠。
- `serve-retry-smoke.py`、`serve-retry.log`、`serve-retry-smoke.log`：冷读退出后的唯一同探针串行重试仍 **FAIL**，独立保留。
- `import-timing.py/.json/.log`：另外的纯 import 诊断 PASS，模块 wall 1.274 秒；无 Store/Worker/业务，不覆盖两个 FAIL，启动时序原因未定。
- `serve-direct-http.json`：直接 CLI 启动后的 8 GET 200、POST 405、NATURAL_PA/同实例两 Run、DB hash 不变。TTY Ctrl+C 工具包装进程 exit1、子进程仍活；精确已知 PID/命令/启动时间核对后，pidfd SIGINT 停止自有子进程，确认退出及端口关闭。子进程 exitcode **UNAVAILABLE**，不称完整 exit0 通过。
- `serve-direct-session.json` 是从工具输出转录的会话记录，**不是原始进程 stdout 日志**；其中 `/proc/30182/cwd` 读取 EACCES 未重试/升级。最终 cleanup 通过精确已知进程身份独立完成，没有停止未知进程。
- `independent-serve-final-review.md`、`independent-serve-final-proof.json`：只读核以上回执，不再启动进程或业务，不将失败改签。

普通 PostgreSQL 启动与显式 SQLite mock 保持区别；真实自然批准门尚缺、额度 0。Windows、PG、真实模型/场景/人工语义、原生浏览器、远端 CI、部署均 NOT_RUN。旧历史 45P/1F + 定向 2P（重叠）+ 独立 9P、自然双 Run 未恢复及旧 F9 未复现保持原分期；旧满盘最后独审未落盘的证据缺口仍存在。
