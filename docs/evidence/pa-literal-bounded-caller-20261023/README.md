# 受限字面检索清单生成：bounded caller

在 `81c9ff364e30c694a6fa71f513960c1be6e9c919` 的[完整候选只读合同](../pa-literal-candidate-contract-20261023/README.md)上补必需发送边界。依据原 V5 P-A / F2-T02 的候选生成阶段。提示已经固定 `text.literal_evidence`、单节点、schema 和接线要求，因此本片只称**受限字面检索清单生成**，不称通用自主规划、正式生产 P-A 或发布验收。新 caller 本轮真实请求 **0**；未新增真实执行决定。

入口为 [pa_literal_candidate.py](../../../scripts/diagnostics/pa_literal_candidate.py)。`prepare` 只建立自有合成 SQLite、原真实 GoalCard 与读授权，封存当前完整 prompt/body、表向量、文件、合同资产及所列源码摘要；没有业务 Run、模型请求或生产来源资格。`run` 显式选择执行后监督一个自有 worker；当前尚未运行带真实凭据的 `run`。

## 已冻结的边界

- 每个新 fixture 的 `control/execution-claim.json` 以排他创建并 fsync 文件/目录消费一次，不因失败、换输出目录或崩溃退还。删除目录不是支持的恢复。不同 fixture/其他客户端不共享该技术账本，不能把它称为全账户额度。
- 最多 2 请求，每次输出 1024 token、完整 wire 最多 32768 字节。每次发送前持久写入 `len(wire)+1024` 预约，总预约和完整报告累计 usage 均不超过 64000，每个报告也不得超过该 slot 预约；未知 usage 停止。预约不是上游 token 或费用硬配额，不把未知计作零。0 repair、重试、重定向或付费回退。
- 原 `InternModel.request_serialized_captured` 发送原字节；guard 精确核 POST、固定 endpoint/model、完整 body、当前凭据及一次入口。原适配器关闭重定向，无网络失败重发。当前 Goal/权限、文件/所列源码/合同摘要在各动作边界重查；SQLite 以 `mode=ro`、`query_only`、数据库 authorizer 和 SQL listener 限只读。授权读取连接在 HTTP 前关闭。
- 第一响应后的单调时钟间隔至少 60 秒。每请求 deadline 是剩余全窗与 120 秒中的较小值；启动、导入、校验、工具反馈、等待均消费原 300 秒。**不保证 120+60+120 加上开销仍能完成。**
- CLI 的独立父进程从启动 worker 前开始监督 300 秒，随后最多 10 秒清理。超时、SIGTERM、KeyboardInterrupt 或监督异常均只终止/必要时 kill 并回收该自有 child，保留 UNKNOWN/失败；没有成功追认。内部 worker 需继承管道、实际父 PID、case/output/script 摘要及原时钟起点握手，真实 transport 在 claim/凭据读取前拒绝无监督入口，每边界复核父存活与管道未关闭。管道是当前 Linux 受控调用能力，不是防同账户恶意替换代码/文件或整个 OS 故障的安全隔离。
- 响应原字节及解码 JSON 全部先查秘密反射，再保存任何响应摘要或内容；错误/不完整响应不保存原文。归档不含 Authorization、token 或凭据摘要。原始响应仅摘要可供关联，不能从归档重算其原始字节，不能据此声称可复验全部原始响应。
- 原当前授权网关提供唯一一次模型请求的工具反馈；授权/完整性复核还会做新鲜只读查询，并非总数据库读取仅一次。第二轮直接输出完整候选，由原严格编译、冻结绑定及 4 个注册 `compute` 样例核查。样例不是创建应用运行。`NOT_ATTESTED / PREVIEW_ONLY / semantic UNKNOWN / publishable:false` 保持，生产来源门未改。

## 输出容量仍未知

旧离线完整候选 4611 字节不是 token 数，Mock usage 也不是实际计数。没有 provider tokenizer 或真实完整候选证明它能装入 1024 输出。当前检查只能证明完整输入 wire 在冻结预算内，不能声称输出可容纳。`finish_reason=length` 必须停并封存失败，不补字段、不用 recipe 代替、不扩额、不自动再试。若后续有限执行另获明确决定，须新目录、新 claim，不能复用旧 AT-02 或探针余额。

## 实际验证

最终 `frozen-tests.xml`：34 PASS、0 失败/错误，4.62 秒。全部模型 HTTP 为 Mock；真实 OS 子进程测试包括直接 worker 拒绝、管道握手、正常退出、TERM/强制清理、KeyboardInterrupt、SIGTERM，以及完整 CLI 父子启动后以两种 token 均空在凭据门拒绝（0 slot、0 HTTP）。后者验证启动接线，不是模型验证。虚拟时钟只验证语义和预算，不是 G0 或真实时钟性能。

成功 Mock 原件含两轮完整请求、实际授权反馈、完整候选、4 个字面计算样例、逐 slot 预约/usage、时间和最终只读/连接清理；原表向量和 SQLite 一起保存。最终所列源码摘要与原件一致。ruff 和 `git diff --check` 通过。

先前首版 25 PASS 未覆盖监督缺口，独审拒绝已保留。补监督后第二轮 27 PASS/6 FAIL 原 XML 保留：一个重用测试未选择 Mock 而先被监督门拒绝，四项子进程测试缺 pytest 专有 import path，另一个全局 `time.sleep` 猴补丁污染了 `Popen.wait`。该红轮临时 supervisor.json 已随 pytest 旧夹具清除，不能补造原件或追认该轮 child 清理通过；其失败栈仍在 XML。随后明确 `PYTHONPATH`、仅注入轮询 sleep，并修正 venv 解释器不能解析 symlink 成基础 Python；33 PASS、随后 34 PASS 原件也保留，不累计成不同场景。最终又补父子共享起点断言，以最终 34 PASS 为准。最终实际子进程清理原件只证明最终测试调用。

## 后续执行的环境条件（未执行）

仅当前 Linux 指定环境、现有 venv/依赖与端点，准备和运行都需明确 `PYTHONPATH=/workspace/Sim2Act/src`，解释器使用 `/workspace/Sim2Act/.venv/bin/python` 原路径。`prepare --case <全新目录>` 后先审封存 witness，再经新有限执行决定才选 `run --case <同目录> --output <全新独立目录> --execute-user-confirmed-pa`。case 与 output 不得包含彼此。无新凭据查找、依赖安装、权限或费用回退；费用依据仅用户确认，不是假官方权益证明。

PG、真实 provider 完整候选、生产来源资格、P-A 发布/应用运行、G0、owner 语义及 Windows caller 均未验。本片不复签旧 Source UI 或完整 F2/R0。
