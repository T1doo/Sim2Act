# P-A 完整字面候选：实现与有限验证合同

本片实现 `goal-text-application.v1` 的只读准备、真实工具结果接续和完整候选严格预览入口。依据原 V5 [P-A 路径](../../sources/V5/平台产品设计.md#p-a从目标直接生成应用)、[F2-T02 / AT-09](../../sources/V5/分阶段开发计划.md)，推进“生成并校验 ActionSpec / AppManifest 候选”，尚未完成发布、正式来源或完整 P-A 验收。本轮真实请求 **0**，没有新模型执行窗口。

## 已实现的最小路径

`sim2act.pa_candidate_preview.prepare` 读取真实保存的 GoalCard、当前用户/项目/运行身份授权和材料，复用原完整提示及服务端 ID 分配。第一轮返回仅允许选中绑定材料的 `resource.read`；`read_feedback` 经原授权网关读取并在返回前再次检查当前 Goal 与权限，保留原 assistant、call ID 和实际工具结果。

第二轮必须直接给出完整 `manifest / actions / source_hash / goal`。`preview` 复用原 `compile_preview`、严格结构/类型/注册表/端口/预算校验和原冻结绑定比较，再经注册的字面计算做小样例预览。没有 recipe 展开、字段补全、手改候选或通过后发布。自然规范 recipe 路径不是本片的直接完整候选生成路径。

原产品只抽出提示和绑定比较的纯函数；编译、reader.check、来源读取及末次 reader.check 的顺序保持。新入口不持 sender、不创建 Run、App、Operation、Grant、Release 或来源见证。入口接收的模型名与 usage 是数据校验，不是调用来源证明；结果固定 `PREVIEW_ONLY / NOT_ATTESTED / publishable:false / semantic UNKNOWN / goal_acceptance NOT_RUN`。直接提供候选也可预检，不能据此证明此前发生过工具对话。

## 冻结的有限语义

[material.txt](material.txt) 是 83 UTF-8 字节的自有合成材料；[goal.json](goal.json) 是完整 Goal 模板，其中 `FROZEN_RESOURCE_ID` 在准备阶段替换为本次真实保存资源的 ID。实际离线 ID/Goal/材料见 `offline/context.json`。只有工具反馈提供材料正文。独立 [oracle-not-for-provider.json](oracle-not-for-provider.json) 不发送给模型，也不作为候选清单模板。

允许的功能只有：区分大小写、返回所有包含 term 的完整原行和精确行号。`Cedar` 对应第 1、3 行，`Moss` 对应第 2 行，`cedar` 和 `absent` 均无匹配；比较全文引用与起止行。空值、两侧空白、超过 80 字符的 term 拒绝。该确定性功能 oracle 不判断材料含义；owner 仍 PENDING、semantic UNKNOWN。合成候选由测试 fixture 提供，不能称为真实模型生成。

拒绝条件包括：未知/错类型字段、JSON 重复键、非注册执行器、额外权限、错端口、错应用/动作/Goal/材料绑定、删改完整 Goal、超预算、错模型、未知 usage、截断、当前 Goal/权限变化和跨 owner。错误不保存候选、不发布、不提高 UNKNOWN 状态。

## 下一段执行合同：仅提案，尚未执行

精确参数以 [contract.json](contract.json) 为准：固定既有 `intern-s2` 端点，最多 2 请求、每次 1024 输出 token、1 次原 `resource.read`、0 repair/重试/重定向/付费回退；工作 300 秒、每请求 120 秒、清理 10 秒，首响应后至少间隔 60 秒。仅合成材料。费用依据是用户确认，不伪称官方权益证明。

未来独立冻结的 bounded caller 必须在每次发送前以完整 wire 计入共享预约账本，单次最多 32768 字节、总预约 64000（`len(wire)+1024`）；该预约不是上游 token/费用硬配额。返回累计 usage 也须检查。调用关联、单次技术 grant、全窗 deadline、原始及 JSON 解码后的秘密反射检查、连接关闭及边界授权复核均由该 caller 承担。本只读入口本身不执行或证明这些预算与真实网络控制，不能直接作为 LIVE 运行资格。

离线两轮完整 body 为 16426 / 16726 字节，预约 35200；完整 fixture 候选 4611 字节。这些不是 token 估计，fixture 的 900 completion tokens 是 Mock 值。**尚不能证明真实模型能在 1024 输出 token 内返回完整候选。** `finish_reason=length` 必须失败封存，不自动扩大预算、修补或替换为 recipe。新真实请求需在该合同审查后另行明确有限执行决定，不能复用已结束 AT-02 的余额。

## 实际离线证据与边界

- `prior-tests.xml`：20 项新增测试 + 1 项原 `test_goal_feedback_repair_release_cold_worker`，21 PASS，12.81 秒；后者是原普通 Worker 的 Mock 兼容回归，非真实模型或生产来源。
- `final-tests.xml`：仅在同一成功样例增加全文 quote / end_line 断言，最终 20 项新增测试 PASS，0.70 秒。不是额外 20 个不同场景；产品源码与上一轮相同。
- `offline/`：最终两轮 Mock wire、真实授权读取反馈、完整 fixture 候选、4 个字面样例、SQL、全表向量及合成 SQLite。成功入口记录 121 条 SELECT；前后所有表相同。负例测试逐项断言拒绝，修改授权/Goal 的反例写入仅为自有测试安排，不是预览入口写入。
- 初次 17 PASS 的 XML 保留；首轮 ruff 曾报测试内未使用 `fingerprint` 导入，已删除。该样式错误的完整原日志未封存，不伪造重建。最终 ruff 与 `git diff --check` 通过；原 Starlette/httpx deprecation warning 保留，未安装依赖。

没有新 HTTP/模型请求、CI、G0、PG、发布、真实语义/owner 验收或正式生产来源验证。当前产品账户来源门保持。原始测试输出、源文件 SHA 与合同资产由 manifest 绑定；独审是源码及离线证据限定 ACK，非性能或完整 P-A ACK。
