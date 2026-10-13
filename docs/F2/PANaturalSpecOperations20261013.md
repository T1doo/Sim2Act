# 自然规范应用：运行回执恢复与已保存成果使用

基线 `147a6da63ecb8fe15b9dea99d1ff8035f31122c3`；开发分支 `dev/pa-natural-operations-20261013`。

## 原方案与缺口选择

V5《平台产品设计》§1.1、§4 的原赛题来源要求：把任务沉淀为可重复使用的应用；P-A 从目标生成、确认后从“应用”使用，P-B 从已完成任务及真实轨迹提取，两条路径分别验收。§5 要求新运行、新结果与历史分开；§8 要求展示前复核授权。V5《分阶段开发计划》F2-T02/T08、AT-09 对应本次有限使用链路。原赛题原件未在本工作区单独取得；本轮依据仓库封存的 V5 来源及其 U-RACE 引用，不宣称重新核实赛事规则。

已有自然规范节点可以从目标生成候选、确认项目 JSON 保存、保存内部版本、绑定另一份当前 Goal/材料并由冷 Worker 重新抽取。因此不重复实现这些功能。本轮发现用户在应用页仍只能读紧凑 JSON，不能从该版本明确读取并取出已有的 JSON/Markdown 成果；内部 Run 提交回执丢失后，恢复按钮仍发送 POST。规范实例还会请求不支持此家族的旧人工签收接口。

本切片补齐：应用 → 内部实例 → 明确提交 → 原键只读恢复 → 选择结果版本 → 当前授权读取 → 可读清单及下载。它使用现有运行器与保存制品，不增加模型通路、解析器、批准框架或发布功能。

## 精确实现合同

- `pa_spec_apps.py` 新增 `GET /api/internal/instances/{iid}/spec-run-requests/{key}`。当前实例/发布/来源授权在正文之前；复验实际 accepted、binding、Run/AppRun 与完整步骤。返回精确主体/项目/应用/实例/Release/原 key/原请求与指纹。无记录返回 OUTCOME_UNKNOWN；仅读，不重新排队、扣额或运行。
- `internal.js` 的规范实例提交后独立用原 key GET 核对回执，不跟随未核对的 POST run_id。响应丢失保留本页原意图，恢复只 GET；未知状态下不提供另一次意图按钮。项目/应用/实例/工作区选择发生变化后，迟到响应不能读取后续内容、修改当前展示或清除待恢复意图。
- 既有 `spec-artifact` GET 增加精确结果作用域与输出指纹，仍执行完整 `verify_job` 和实际 `resource.read`。页面对照当前 typed 行的资源 ID、JSON 原字节/SHA、结果指纹、Release/版本和独立 Run Markdown，再显示或下载；每次下载重新 GET。Markdown 是已核 JSON 的转义派生视图，不是第二次保存。
- 未标注规范显示要求、条件、例外、未决问题、引用原文、关联未定、全部人工未决项、未覆盖片段与完整原文。DOM 只用文本节点。出处 PASS 与语义 UNKNOWN、人工验收 PENDING 分开展示；没有签收入口可用时明确说明。
- 未知结果的本页请求保存在内存，页面重开沿既有服务端实例/任务历史读取，不新增浏览器正文或凭据持久存储。此切片不声称新增跨页面原 key 持久恢复协议。

## 两个精确授权边界修复

基线 `natural_spec_runtime.py` 的 SPEC_STEP_VERIFIED 之后曾先 replay receipts，再 fresh commit_guard；其中真实求值了 operation receipt 和 Attempt parameters/response/usage。`pa_spec_apps.py` 的 SPEC_COMMITTED 之后曾先完整读取 Run，再 verify_job 授权。

实际 SQLite UDF 观察器已校准非空合成正文。原 r3 四例均最终 GRANT_REVOKED、没有成功 typed 制品，但每例在拒绝之前真实求值了受保护字段；不是只看到 SELECT SQL 就推断内容被加载。两种触发分别是精确事件点的同事务撤权故障注入，以及控制时钟让 Grant 到期但 lease/deadline 仍有效。生产 Store.event 只有 INSERT，SQLite BEGIN IMMEDIATE 排斥外部写者；不能把同事务 monkeypatch 称为公开回调、真实并发攻击或 API 内容泄露。

修复移除模型事件之后多余的旧 receipts，使 fresh guard 在完整回执/Attempt 读取之前；本地步骤事件后也先 guard；保存事件后先 job_scope_gate，再读取终态和完整 Run。最终 verify_job、模型账本、原审计、lease/deadline、事务回滚保持。前两次红轮分别是冻结时钟造成生成事件同时间排序、观察器误挡原始响应 NULL CAS 的夹具失败，单独保留，不计产品复现。修复后的四例初测 4 PASS；最终冻结结果另列。

## 尚未闭合

自然规范 P-B 从成功任务提取尚无独立入口与完整来源合同；既有 P-A 新材料 binding 不能冒称 P-B。真实模型语义、完整 P-A/P-B、人工签收、正式发布、真实资料及其他平台验收仍待完成。测试中的固定合成响应只验证工程，不提供语义通过结论。

2026-10-13 仅访问公开官方文档：模型明确为 `intern-s2`，拟议端点为 `https://chat.intern-ai.org.cn/api/v1/chat/completions`；[模型文档](https://internlm.intern-ai.org.cn/docEn/docs/Models/)及[Chat 文档](https://internlm.intern-ai.org.cn/docEn/docs/Chat/index.html?id=1748476800101)支持这两项事实。[认证文档](https://internlm.intern-ai.org.cn/docEn/docs/Authentication/)要求合法后端 Bearer 凭据。未访问账号或模型端点、未查询/配置凭据。所查文档不能证明本账号免费额度或强制零付费条件，仍 NOT_VERIFIED；[已有最小真实提案](PANaturalSpecRealAcceptanceProposal20261013.md)未执行，真实模型请求和费用均 0。
