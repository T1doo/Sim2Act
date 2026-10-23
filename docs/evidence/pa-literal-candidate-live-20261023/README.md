# 受限字面清单候选：单次真实诊断失败

本次在明确的新有限执行决定下，仅执行一次受监督 CLI。执行版本 **`aed920f4bb32cacbfa8070bfe8044a6540a9d42d`**；新 case `/workspace/pa-literal-authorized-20261023-1`、独立 output `/workspace/pa-literal-authorized-result-20261023-1`，未重用旧窗口。结果 **STOPPED_NO_RETRY / MODEL_TIMEOUT_OR_TRUNCATED**，不是 P-A 成功。

## 实际发生

| 项目 | 原件结果 |
| --- | --- |
| 请求 | 2 次原 adapter 请求，2 次 HTTP 200，0 重试 |
| 首轮 | 3919 input + 176 output = 4095 token；实际选中绑定 resource.read，取得 1 次模型请求的真实授权工具反馈 |
| 第二轮 | 3864 input + 1024 output = 4888 token；原解析器拒绝，未进入 candidate 编译或样例计算 |
| 合计 | 7783 input + 1200 output = **8983 token**，usage known |
| 预约 | 两个完整 wire 为 16426 / 16774 字节，共预约 **35248**；预约不是上游 token/费用硬配额 |
| 间隔 | 首轮有效响应处理完成到第二次 send boundary **60.025179903 秒** |
| 时限 | worker **89.954637 秒**；父监督 **90.029614 秒**，未达到 300 秒全窗或清理上限 |
| 进程 | child 59390 自然退出 **1**、已 wait/reap；未 terminate/kill，无监督或清理错误；仅该已知 PID 的后查无当前条目 |
| 数据 | 55 表 / 9 行向量和 DB/sidecar 文件清单完全相同；连接关闭、engine disposed |

首请求原始完整 wire 在执行前冻结；第二请求可由已保存的原 assistant/工具结果按原序列化重建，两者摘要都与实际 guard 的记录相符。未发送 oracle 或 fixture 候选；材料仅自有合成 83 字节。所有请求均固定既有 endpoint/intern-s2 与 1024 输出，不改变凭据或生产来源门。

## 失败的精确边界与证据限制

第二轮 `http_status=200`、完整 usage 已保存。依据冻结源码顺序，身份与 usage 检查之后，`parse_response()` 的结束原因检查会产生本次错误；后面的候选编译没有到达。它不是 300 秒总时限耗尽，也不能凭错误码中的 TIMEOUT 推断为网络超时。

**具体 finish_reason 没有归档。** 因此不能确认原值必为 `length`，只能推断原解析器拒绝了非 stop/tool_calls 的结束原因。第二轮 output=1024 是已保存的报告值，不证明所有合法完整候选都必然无法在 1024 内表达。第二原始响应、部分候选及身份投影未保留；第一响应只有摘要，无法由归档独立重算其原始字节。不得补造原件或通过新请求/API 回取。

原第二 slot 仍是 `STARTED_OUTCOME_UNKNOWN` 并附 HTTP 200/known usage，表示没有完成该 slot 的有效响应校验；保留原报告不重写为成功。整体已停止且 claim 保持消费。没有第三次请求、增加输出、补字段、recipe 替代、创建应用或发布。

## 原件与结论

`prepared.json`、`execution-claim.json`、`result.json`、`supervisor.json` 原字节保存。`preflight.json` 冻结路径/参数/Goal/13 源码摘要/资产及首 wire；`postflight.json` 与 `after-table-vector.json` 记录终态限定后查；`fixture-after.sqlite.gz` 是结束后合成库，其解压摘要等于执行前 inventory（没有冒称另拍过 before 库）。原 response body 未保存。归档前再次检查现有 token 的原字节和解码 JSON 反射，无 token、Authorization 或凭据摘要写入归档。

独审限定接受失败封存、工具反馈关联、usage/预约/间隔、完整性及最终清理，不签成功候选、通用自主规划、正式生产来源、发布、G0 或完整 P-A。费用依据仍仅用户确认，不是官方权益/收费核验证明。旧 sleep(10) 历史 UNKNOWN 未改。

本轮不重跑旧离线套件/CI。后续仅可离线改善固定枚举结束原因/失败阶段的观测；它不能修复或追认本次结果。任何输出合同调整或新真实窗口均须另有明确方案，不能消费已结束窗口的余额。
