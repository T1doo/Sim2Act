# 条件报告产品来源绑定整合（实施前）

2026-10-07，独占 `/workspace/Sim2Act-core-conditional-integration` / `dev/core-conditional-integration-local`，base0126f5459d7385f0c33f3ca4d9d585d91e2a4a1f；正常merge已独审源码fb239a5e95f217df473da1569195397b0a2dca2a，merge e02000279da1774f84badd84254a548ea5a1f2b5。fb239包含f958历史与后续共享成果一致性修复，不单独恢复已撤销的f958。保留0126原生/文档；不接触原core、native-capture或共享venv。

现产品条件页只支持人工Report无持久写核对；真实Run/check/candidate/DAG/cold API已存在但页面缺入口。本片只整合这个实际产品缺步，不新业务family或语义成功来源。新增独立“来源绑定”区和JS模块；原人工表单、API与原生入口不替换。新入口从用户选的当前授权A-S资料与严格显式假设创建source，GET重核真实技术receipt后POST独立check，eligible当前绑定才可extract；展示固定受限read→language DAG和actual candidate receipt。冷阶段明确选择资料/新假设，创建cold并读新receipt/新check。source/cold始终整体NOT_ACCEPTED、semanticUNKNOWN、WAITING_APPROVAL；extract SUCCEEDED只技术编译/NOT_RUN。无provider时显示WAITING_RESOURCE，不自动注入Mock或启用真实provider。

只消费既有conditional-runs端点，不HTTP收Report/gold/candidate/decision，不写Run.result、不替换sourceproof或候选契约。默认缺provider不发送，旧成功门保持。纯有限注册模板、resource.read，说明文字NOT_CHECKED/现实事实未核查/ownerPENDING/发布关闭。仅显式click提交，分页/刷新/冷会话不自动创建任务或恢复PASS。切换身份/项目/资料版本、编辑输入和失败清除可用检查/候选展示；已接受Run不可导航撤销。提交未知保留同request_key及body以显式重试，防重复；不得用旧check重放新Run。按身份/项目/资料/输入版本闭合ABA延迟响应。

验收：真实loopbackHTTP/jsdom UI→实际Worker/InternModel MockTransport→2source/1extract/1cold，实际RECEIVED/VERIFIED/双锚/4slots同offline14，gold输入0、Principal/Grant无增量。人工报告任意修改不能影响新POST/result；未知事实或错Report不给candidate；当前source/cold整体UNKNOWN不称成功。版本、错Run、旧结果、撤权、跨项目/身份、同键未知重试、冷会话、晚响应和失效页面永久负例；原人工DOM/native相关旧测试回归。默认noProvider实际阻断不发。

先专项静态/HTTP+DOM冻结请父独审；新隔离venv localpth当前src→共享deps路径（不处理共享旧editable，不安装），controller+cleanchild provenance。完整SQLite与唯一标签PG `sim2act-core-conditional-integration-20261007`（独立端口/schema/role）回归，sanitize日志/失败历史、清理owned schema/role/process/container0。无新增表/DDL/Grant/身份/准备器激活/LIVE/部署/push/CI。原生/像素本片NOT_RUN，父负责独审与最终合并；下一片扩大有限独立覆盖或明确真实模型审批，不自动提升当前状态。
