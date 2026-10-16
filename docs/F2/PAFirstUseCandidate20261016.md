# P-A 首次新材料逐次使用候选：2026-10-16

本轮新包在全新安装、全新合成库上实际完成：保存 P-A → 空实例首次新材料及 Goal 逐次提交得 v1 → 同实例另一材料及 Goal 得 v2 → 独立进程冷读两个原成果。没有用原材料 P-A 或 P-B 成功替代这条路径。

源码冻结为 `fc69c863f57f0cdf9a8dbfeaeb5fdc567e42c675`，从交付 `e7dcdb4ff25e5765be5dc34a4edc72ecba1929bc` 接续普通开发分支 `dev/pa-new-material-running-fix-20261016`。后续交付提交仅追加本报告、证据及已验证包；包内 manifest 仍指向 fc69。产品 `src` 与 e7、`986799d766e98744e29e038543299af13785ea36`、首包 `0f0819a6a481841a0221cc69f75959326f264529` 逐字相同。

## 取得的证据与修复范围

原失败 `run_be5e46f6c8794042bc18f2f9ca7ea6a7` 没有重放或改写。只读核对其 runs/events/attempts/operations/binding 五组原件完全相同，原 DB 前后 SHA256 均为 `bf2293cb3d5f96d9a054596d7e1cccd9905e1088f69620e9fc4e2989375b1d4c`。原件仍是 RUNNING、resource.read VERIFIED、0 runtime attempt、error=null，观察时 lease 已过。

0f 的 `Demo.once` 同步执行 `Worker.once()` 后完整 GET，并明确要求成功，因此不能把原 FAIL 解释成只提前轮询了后台业务。`Worker.once()` 的布尔值只表示取得进度；源码允许处理异常后，因为原 lease 已过而无法落失败状态，随后仍返回 True。这能解释现象，但原失败没有最初异常/事务 trace，**不能确定该次最初异常或具体锁持有者**。也不归因于旧 F9。

使用首包已安装 wheel、精确 0f 脚本/材料/Goal/recipe 的新库最小前缀对照，首次逐次 P-A 一次自然成功：`run_4b338799aaeb474c95b0fd52b3c04a7a`、v1、一次 claim/fence1，`Worker.once` 22.479 秒。原操作委托式 trace 记录两次后台 BUSY 和终态后迟到 STALE，没有 fail_owned。它证明同链能够完成，**没有自然复现最初失败**。完整 trace 的 gzip、原始 SHA、运行脚本和输出已归档。

因此只调整候选脚本的 Worker 生命周期：使用既有普通 Worker/Store.claim 按原一秒间隔服务，读取轻量调度 metadata，以实际终态结束；保留原接受身份、绝对截止、300 秒预算及 30 秒 lease。失败/阻塞/未知状态、意外异常或截止即退出；没有重发受理、resume、清除 unknown、改历史或新增 executor/Grant。允许原 Store 合法回收后重领，所有真实 claim/fence/WORKER_LOST/RECONCILED 均公开记录，**不再承诺单次 claim**。每轮检查不存在其他 active Run，并核此 Worker 全部领取 ID；实际双 queued 负例证明拒绝旁路工作。

新增 `prepare-pa` 恢复精确首包新材料路径，第二次仍走 P-A per-use；旧 `prepare` 的原材料 P-A → P-B 演示保留，本轮没有重跑或改签其历史结果。没有修改产品 lease/guard/心跳/权限/版本或模型门，旧生产最初异常仍未定位。

## 本轮实际执行及独审

从新 ZIP 解压至 checkout 外，在全新 Python 3.12.14 venv 安装现有锁及 wheel。`pip check` 通过，实际导入来自该 venv，113 个已安装产品文件与 wheel 逐字一致；checkout src 不在 sys.path。

`prepare-pa` 和随后独立 `verify` 均退出 0：

| 项目 | 实际结果 |
| --- | --- |
| CSV `run_d39435ce914b4246977b9fdac89318c9` | SUCCEEDED，sum=30，v1 |
| 生成 `run_2d73f756b6074bb6b150825b0c2c710a` | PARTIAL，三条固定 mock，明确保存 P-A/Release/空实例 |
| 首次新材料 `run_97e4565fb73b46c2a2fddd1b5b40d795` | SUCCEEDED，accepted base=0 → v1 |
| 第二材料 `run_5f36e0ee795c4618974ac84077967b2e` | SUCCEEDED，同实例 accepted base=1 → v2 |
| 独立进程冷读 | CSV + 两 P-A 成果共 3 个，artifact/版本/typed 行摘要一致，全库持久行不变；0 Worker/模型请求 |

两次 P-A 都经原 pa-use-review/run 显式提交，重复同一意图返回原 Run；同应用、Release、实例 `iinstance_9cd6bc6cea5a2d13d87da77dee2f9915`。第二次写前捕获首 typed 完整行并核其保留；两个旧/新成果均能通过同 Run 人工验收入口冷读。5 条响应全部为固定 MockTransport（3 生成 + 2 P-A），真实请求 0，owner PENDING、semantic NOT_RUN。

4 个实际 Worker 均为 1 turn / 1 claim / fence1；本轮没有实际 WORKER_LOST/RECONCILED。多轮及合成 fence3 只在脚本合同轻测中覆盖，不能冒充自然失租恢复通过。作者与冻结独审各执行同 21 项轻测通过，是 **21 个独特用例重复执行，不相加为 42**。独审另逐字核新包、安装内容、材料/Goal、DB 绑定、v1/v2 保留及冷读原件，没有再次启动自然 Worker。

只读 `serve` 的两个外部 15 秒启动探针均 FAIL：它们在导入阶段被自己的 SIGINT 清理中断，失败原件保留；独立只读 import 测量实际 1.274 秒，不能由此断定普遍启动原因。随后直接 CLI 启动成功，8 项 GET 200（含目录 NATURAL_PA、两同实例 Run 人工入口），POST 405，DB hash 不变。TTY Ctrl+C 仅结束工具包装进程（报告 exit1），子服务仍在；核对本次 PID/命令/启动时间后，用 pidfd SIGINT 停止该自有进程，确认退出及端口关闭。真实子进程退出码不可获取，**不称 serve 完整 exit0 通过**。读取 `/proc/30182/cwd` 曾 EACCES，没有重试或升级该读取；没有停止未知进程。

## 包、证据与未执行范围

- [ZIP](../../deliverables/pa-first-use-candidate-20261016/Sim2Act-local-candidate-fc69c863f57f.zip)：1,515,823 字节，SHA256 `0ff78bc7330bcbbd5cc2a9fff76bb3cd2d2cd4e9ec37a3a0e1873acd50c74507`。
- [manifest](../../deliverables/pa-first-use-candidate-20261016/candidate-manifest.json)：134 个包文件、133 项清单、131 个 Git 文件。wheel SHA256 `3f7b7b527dfdf3dca64c2953daf61464dbbd259278287b8c95fa89f22bb37a0f`，113 个产品文件含 21 个网页资源。包无 DB、日志、测试、私有配置、历史证据、venv 或第三方 wheelhouse。
- [安装及调用命令](../LocalCandidate.md)；[原始证据与独审索引](../evidence/pa-first-use-candidate-20261016/README.md)。首包、c9 包及既往报告均保留原字节。

普通启动仍要求 PostgreSQL，本候选是显式 SQLite 合成 mock。真实自然 LIVE 专用批准门/跨 Run 总账尚未实现，真实额度仍 0。Windows、PG、原生浏览器、真实模型/场景/人工语义、远端 CI、部署均 NOT_RUN。没有使用旧满盘实例、旧 bundle 或共享文件；旧环境最后独审未落盘的缺口没有补回。

历史 `986799d` 保持 45 PASS / 1 FAIL、随后定向 2 PASS（重叠）及独立新增 9 PASS；此前自然双 Run 未触发新恢复，旧 F9 具体时序仍未复现。本轮没有扩展恢复矩阵。最终普通分支推送的精确 HEAD、远端相等、未提交/未推送差异及原远端 refs 在 checkout 外单独记录，不以源码冻结 SHA 代替交付 SHA。
