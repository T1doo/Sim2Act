# 既有 bounded agent 内部 UI 最小切片（实施前，2026-10-06）

基线4e7010b3a5e2697fa3bf45a53e0b992f71f6f7c5，dev/f1-foundation。父授权先独立审查、本地实现/验证/提交；父检查前不得push/CI。模型预算0、无LIVE、无新工具权限/Grant/身份/表/正式发布，不改原V5和AT02。

## 原目标与实际缺口

原V5产品§2要求在现有项目/应用/资源工作区使用，§4共同完成条件要求适用输入、模型/连接限制可见，新输入产生AppRun和结果版本，历史不得冒充当前结果；§5/§8要求同一清单、权限交集、审批精确快照和账本。此次为已存在且可验证的bounded_agent候选接通现有应用界面，不另造后台，不增加候选自主生成或新提取API，不要求JSON清单编辑后声称自主交付。

目前GET候选已支持agent，界面却无条件读取input_guidance.columns；HTTP审批没有Replay参数，默认Worker没有Replay来源。原Python服务仅接受显式注入ReplayModel，因此单改表单不能得到真实冷运行。

## 最小实施

1. 保持应用列表/认证/项目选择、内部批准/Release/Instance/AppRun/历史/控制和版本切换入口。agent表单使用term，CSV原路径保持。显示绑定资源/hash/revision、仅resource.read、字面检查和semantic UNKNOWN。离线响应由工程调用者提供，不由真实模型自主生成。
2. 在原内部release-approvals和runs请求扩展可选offline_replay（两条有限JSON wire response）；UI用明确标示的文件输入加载离线响应，限制文件/响应大小及形状；不从原文生成答案、不含gold、不自动调用provider、不创建Grant。未加载Replay时agent审批/提交禁用。后端在原ReplayModel/parse_response/可信检查器核查，不把客户端final当可信结果。
3. AppRun明确提供Replay时，存入既有internal_run_bindings.snapshot，纳入接受request与绑定fingerprint；worker从冻结快照构造新的ReplayModel，优先此已接受数据，绝不fallback真实provider。原Python显式in-memory Replay注入路径保留，CSV拒绝Replay。无新表或API DDL。冷worker执行一个新Run可验证；中途工具/模型阶段断电自动恢复仍需另外验收，不提升完整恢复。
4. UI请求带现有身份/项目/app/instance generation；新增文件读取也绑定代次；切换、撤权或错误清空受保护材料/结果/审批。审批过期不得确认；输入/Replay变化清空未确认批准。历史按版本显示，agent引用用textContent可信文本视图，不渲染HTML。小屏可读和长hash断行。

## 验收与失败边界

先独立审查，之后HTTP/服务测试：既有认证与跨owner/project拒绝、无新增Grant、正常审批/Run/结果新版本/冷Store-worker；坏Replay、错误字面证据、额外tool/超限、同键异Replay、绑定协调篡改、来源/当前Grant撤销拒绝，失败不追加结果。CSV/F1旧回归、ruff/mypy、SQLite和PG。

真实原生浏览器脚本覆盖agent打开、文件选择、明确离线标识、批准手工确认、冷worker新结果与历史、过期响应不覆盖、撤权/篡改拒绝、390px窄屏及桌面截图，必须实际查看截图后才记视觉通过。当前原生Chromium正常/正式审批同命令均因现有SUID sandbox helper配置退出；不关闭sandbox或改系统安全策略，不以jsdom代替真实浏览器，不擅自用CI绕过父检查。继续完成功能与可执行脚本；如仍阻塞，明确browser/截图NOT_RUN和原错误。

完整P-A/P-B、真实自主manifest生成、自由语义正确、Win11/F1正式签收和自动恢复仍开放。本地结果与失败保留在evidence/bounded-agent-ui-offline-20261006。

## 本地实施及验收收尾

已复用既有内部界面和 API 参数、冻结 Replay 到既有绑定 JSON，并实现提交/成功冷读的已接受响应 oracle。文件/输入/app/project 代次、批准到期与原键冻结重试、引用纯文本和当前 draft 刷新核查已接通。独立审查曾实测两个内部篡改错误成功，修复后独立拒绝且无效果追加；原失败证据保留。

新 HTTP 20 PASS、HTTP 驱动 DOM 22 PASS、完整 SQLite 493 PASS/24 SKIP；PG 与全部最终终态见[本轮证据](../evidence/bounded-agent-ui-offline-20261006/README.md)。原生 Chromium 多次受 SUID helper 配置阻断，真实浏览器检查 0、截图与查看 0，窄屏视觉仍未验收。DOM 不替代原生；历史 fetch failed 根因仍未确定，夹具改异步子进程后通过，不将旧失败追认通过。仅本地 commit，等待父线程检查，不 push/CI；本步也不提升自主生成、语义和完整恢复或整个 P-B。
