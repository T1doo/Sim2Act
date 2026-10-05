# 2026-10-05 有界 LIVE 子链证据

结论：指定 [dd195681](https://github.com/T1doo/Sim2Act/commit/dd195681de8966f79cf9ba45188ea15a04704f75) 在正常 loopback API / 独立 worker / PostgreSQL 17.9 / 项目 InternModel 路径完成合成只读反馈闭环。最终 **PARTIAL / LIVE**，答案去除空白为 **42**，resource.read Operation **VERIFIED**，不是 SUCCEEDED。语义目标验收仍 NOT_RUN，Windows 原生和 F1/R0 整体门未通过。

## 不覆盖失败记录的证据顺序

1. [原提交 04335528](https://github.com/T1doo/Sim2Act/commit/04335528cdce3febec03273fe9446695aa7b11d5)：官方独立接入返回 Intern-S2；旧 worker 仅接受小写。零外部请求诊断通过项目 API / InternModel MockTransport / worker / SQLite test_only 确认官方同形返回导致 FAILED / MODEL_OUTPUT_INVALID、零 Operation；小写合成对照闭环为 PARTIAL。该 JSON 中 LIVE 标签与 10/10/20 usage **全部为合成夹具，不计真实用量**。见 [离线诊断](04335528-offline-model-name.json)、[96 PASS / 1 SKIP 工程检查](04335528-engineering-tests.xml)。
2. dd195681 第一次真实 PG 任务：Run `run_10f56d3bac394bdcbea227f31614da1d`。第一轮 HTTP 200，模型身份 ACCEPTED，resource.read VERIFIED，工具反馈写入 PG。第二次预约产生的完整发送体 2028 字符，超过 2000，**发送前拒绝，未发第二个 HTTP**，Run 保持 FAILED / BUDGET_EXHAUSTED。第一个 attempt RECEIVED，第二个 FAILED、usage unknown/null；第二个预约不是实际计费用量。见 [失败 Run 完整脱敏导出](dd195681-first-run.json)、[真实发送与本地拒绝](dd195681-first-wire.json)。
3. 用户明确授权后，新独立 Run `run_d47057009ccf4d47beabfce85fd18ab0`：目标缩短为 `Read; echo.`，资源仍为合成文本 `42`。先零请求利用原项目正常序列化、此前真实公共助手响应形状计算首轮/预计回填轮 1170/1958 字符；三个必要工具 schema、权限和完整回执字段均保留，未修改生产代码或原响应。实际两个请求也为 1170/1958，HTTP 均 200，完成后间隔 6.100161262 秒。原项目独立 worker 收到真实反馈后回答原文 `\n\n42`，最终 PARTIAL / LIVE。见 [零请求尺寸预检](short-input-preflight.json)、[成功 Run 完整脱敏导出](dd195681-short-run.json)、[真实发送账本](dd195681-short-wire.json)、[独立核验](short-run-validation.json)。

前次临时数据库在前轮取证后已清理，旧失败导出保留未改写；成功任务在新的临时数据库接受为新 Run。此目录不伪造同一数据库中旧任务转为成功。

## 请求与真实 usage 总账

| 批次 | 真实 HTTP 请求 | 已知输入/输出/总 tokens | 范围 |
| --- | ---: | --- | --- |
| 早期网络测试/诊断 | 3 | 未提供返回用量，未知/无返回 | 数量来自用户委托历史，不补造时间、HTTP 状态或费用 |
| 独立 API 接入 | 4 | 980 / 175 / **1155** | models 一次（无 usage），最小文本、加法工具选择与回填；[原账本](api-intake.json) |
| 项目 PG 第一 Run | 1 | 485 / 91 / **576** | 第二发送体拒绝，不算第二真实请求 |
| 项目 PG 短目标新 Run | 2 | 1256 / 156 / **1412** | 两轮真实选工具与反馈后回答 |
| 合计 | **10** | **2721 / 422 / 3143 已知 tokens** | 早期3次未知部分未纳入 token 合计；不能推断总费用 |

请求预算耗尽，剩余 **0**。未知/无返回不记零计费；MockTransport usage 不加入真实合计。此归档没有再调用模型，也没有重新查询 models。

所有实际模型请求只访问 `https://chat.intern-ai.org.cn/api/v1/` 官方端点，stream=false；接入测试 max_tokens 为128/512/128，项目两次运行均512，上限没有放宽。每次完整合成发送体 <=2000 字符，超过上限者在发送前拒绝；真正相邻请求间隔至少6秒。SDK自动重试关闭，项目 max_repairs=0；没有真实用户/园区资料或外部写入。

## 身份策略与持久化核验

请求始终 intern-s2；只接受原始返回 intern-s2 / Intern-S2，规范值 intern-s2，策略 `intern-s2-returned-name.v1`。两轮成功 attempt 均 RECEIVED，raw/canonical/policy/enforced/verdict 与实际 usage 保存在 PG parameters/账本，未改写响应或放宽到任意大小写。14项独立零网络身份复核见 [JUnit](dd195681-model-identity-tests.xml)。

成功 Operation `op_4dd2cbc60e7e42fc9be978ca507a9389` 的 resource.read=VERIFIED、receipt.readback.v1=PASS。API接受202，最终回读200；新 Store 连接重新读取 PG 后确认两个 attempt/两个预约、唯一只读 Operation、tool消息与回执/最终result.receipts完全一致、资源哈希及最终答案正确。持久上下文角色顺序 system/user/assistant/tool/assistant。模型没有访问任意路径或执行生成代码。

## AT-02 覆盖及边界

已完成 **合成 LIVE 子项**：真实书生按目标选注册工具、严格参数/授权检查、只读工具执行与核验、完整反馈交给模型并得到最终回答、请求/返回模型与策略版本、usage 与 Run/Operation 持久化及回读。独立 API 接入和离线诊断分别标明，不能冒充该项目真实链。

未通过/未测：Windows 11 原生及 PowerShell 生命周期、真实材料授权与独立语义 oracle、完整账号能力/429故障矩阵、F2应用生成发布、F1/R0整体验收。模型权重版本仍 unknown。AT-02不升格为完整场景签收。

## 环境、安全和收尾

Linux Python3.12.14，临时 PG17.9；迁移与运行角色独立，运行角色无超级用户/建库/建角色/schema CREATE，仅目标业务表DML/schema USAGE。API/PG均仅loopback，Doctor数据库UP。外置测试发送守卫只在httpx发送边界计数、测字符、记录安全元信息和拒绝越界，不替代项目适配器/worker、不改请求或响应/TLS/代理。

已停止独立 API、worker、临时 PG容器并验证端口关闭；证据在清理数据库前已从实际持久记录导出。开发源码/分支未由验证器更改。只归档筛选过的合成输入、脱敏回执、数值用量、测试结果与哈希；不提交原始tar、进程日志、配置/环境值、请求头、真实凭据或私有 reasoning_content。移除本机绝对路径与 data_dir；归档扫描未匹配已注入真实凭据、Authorization/Bearer值、含密码数据库URL或私钥模式。

源码 SHA256 与精确提交见 [source-hashes.json](source-hashes.json)；归档每文件 SHA256/字节数见 [evidence-hashes.json](evidence-hashes.json)。证据 manifest不哈希其自身；Git提交固定最终归档内容。
