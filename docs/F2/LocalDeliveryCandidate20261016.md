# 精简本地交付候选：2026-10-16

本轮交付的是**限定范围、合成 mock 的可复现工程候选**。产品 `src` 逐字保留已独审 `986799d766e98744e29e038543299af13785ea36`；没有修改 executor、Grant、权限、版本、原 300 秒 Run / 30 秒 lease 或心跳控制器。

候选源码冻结：`c9e9f3fc9787350d1e7997860234694b270a6a7f`。交付提交只追加本说明、必要原始证据和已经构建验证的包；包内 manifest 指向该源码冻结，不能把最终说明提交当作重新执行过的源码。

## 产物与运行

- [候选 ZIP](../../deliverables/local-candidate-20261016/Sim2Act-local-candidate-c9e9f3fc9787.zip)：1,512,866 字节，SHA256 `082d1e4dae16e0dece011f719fe22a9142b195f4464d46310c4ec44539f65701`。
- [逐文件清单](../../deliverables/local-candidate-20261016/candidate-manifest.json)：包共 134 文件，其中 133 项列在清单，清单不自签。131 个 Git 文件、独立 README 及 wheel 都来自明确白名单。
- wheel 在 ZIP 的 `wheels/` 内，SHA256 `824157288bc83d3e8cff7d0e0681d9c93d5038534aa590b47f2504166711e9b0`；113 个产品文件含 21 个网页资源与冻结 `src` 一致。
- [安装及演示命令](../LocalCandidate.md)：新虚拟环境装现有平台锁及 wheel，依次调用 `prepare`、独立进程 `verify`、只读 `serve`。不需要 Node 或测试目录。包不含第三方依赖 wheelhouse，首次安装需要现有网络或自行准备依赖。

包不含私人配置/真实凭据/数据库/日志/测试目录/历史大证据/venv/node_modules；仅 `.env.example` 无凭据模板和明确公开的合成身份。构建日志和本轮原始验证证据单独保存，不属于候选载荷。没有使用旧满盘实例、旧 bundle 或旧共享文件。

## 实际执行与独审

从上述 ZIP 解压到 checkout 外，在第二个全新 Python 3.12.14 venv 安装锁定依赖和 wheel。`pip check` 通过；导入路径实际在新 venv 的 site-packages，113 个已安装产品文件与 wheel 逐字匹配，checkout 的 `src` 不在 sys.path。显式全新数据目录启动真实 loopback HTTP API，没有预置结果。

`prepare` 实际退出 0：CSV 创建→内部批准/Release/实例→正常 Worker 得到 sum=30/v1；自然 P-A 经 3 条固定 mock 生成、明确保存、原保存材料/Goal 运行成功/v1；从该成果经已有 extraction options/review/consent 提取 P-B，保存 Release/实例，第三份材料和新 Goal 经逐次 review/commit 运行成功/v1。相同意图重复 POST 返回同一 Run。4 个 Worker 各只有一次 claim、fence=1（含生成 PARTIAL）；没有重放失败 Run 或 drive-to-success 循环。自然 mock 共 5 条响应，真实模型请求 0，人工验收 PENDING，真实语义 NOT_RUN。

随后独立 `verify` 进程退出 0：新 Store/API，仅 GET 3 个已有结果及同一 Run 人工验收状态，artifact hash 和 v1 一致，全库持久行不变，Worker/模型请求均 0。另启动实际 `serve` 自有进程，普通页、JS、目录、已有结果/人工验收 GET 成功，POST 返回 405；SIGINT 后正常退出 0，数据保留。此项是 HTTP 启停验证，原生浏览器未执行。

新增边界轻模块冻结源上作者 10 PASS、独审 10 PASS，属于同 10 项重复执行，不相加为 20。独审另核 ZIP/manifest/wheel 同源、包隐私、普通 PG 边界，并独立执行前包的 CSV + 第二进程冷读；后者加载解包源码，不能冒充本轮安装 wheel 的完整自然执行。最终独审对本轮完整回执的核查另见证据索引。

## 保留的失败与限制

首包源码 `0f0819a6a481841a0221cc69f75959326f264529` 的完整 `prepare` **FAIL**：CSV 和自然生成完成，但 P-A 新材料逐次 Run `run_be5e46f6c8794042bc18f2f9ca7ea6a7` 一次 claim 后仍 RUNNING；只完成 resource.read，0 runtime attempt，error=null，返回观察时 lease 已过。原目录和只读原件保留，具体原因未定，不称旧 F9 同因。本轮随后只收窄演示为原材料 P-A + 新材料 P-B；**没有修复该失败，P-A 新材料逐次使用在最终候选为 NOT_RUN**。前包的 10 项轻测、包同源及 CSV 独验通过不能替代其失败的完整链。

最初新增轻测曾 6 PASS / 1 FAIL：测试误将实际项目数组期望为对象，已修正，原 JUnit 保留。独审还在冻结前发现并修复回执输出 symlink 覆盖、篡改回执绝对 URL 跨 origin 请求两个问题；最终轻测实际覆盖父目录/输出 symlink 和精确 loopback origin。没有发生外网模型调用或覆盖外部文件。

历史 `986799d` 仍按 **45 PASS / 1 FAIL + 定向 2 PASS（有重叠）+ 独立新增模块 9 PASS** 分期表述，不能称一次全绿。此前自然双 Run 成功但没有触发恢复分支，旧 F9 具体时序未复现；本轮没有重跑故障/恢复矩阵。旧满盘环境未落盘的最后独审报告没有补回。

普通启动仍要求 PostgreSQL，不能把 SQLite mock 夹具当作普通安装。真实自然 P-A/P-B 专用 LIVE 批准门与跨 Run 总预算账本尚未实现，额度 0；最小批准和私下配置前提列于使用说明，本轮没有配置/调用真实模型或增加网络权限。Windows、PG、真实场景/人工语义验收、原生浏览器、远端 CI、部署均 NOT_RUN。

完整本轮原始证据及校验值见 [索引](../evidence/local-delivery-candidate-20261016/README.md)。主分支和原远端基础分支保持原 SHA；最终推送回执在 checkout 外另记录实际交付 HEAD、远端相等、工作区和未推送差异。
