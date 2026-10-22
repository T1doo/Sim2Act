# Source / Extract 完成回执冷页只读入口

基线 `607c05d230e73562b2aaa40a8102902f8c61ff66`；实现按已审 `docs/F2/ProtocolCompletionReadbackPlan20261022.md`，最终执行16份冻结源码/配置逐份对应 `frozen-source-hashes.json`。没有新Edge/PG/provider/G0窗口，没有重跑旧37/20或进程套件。

新认证GET `/api/projects/{pid}/protocol/runs/{rid}/completion-receipt`，只为原test_only/mock Source及单请求Extract定位已持久V2完成命令。原Run与对应Attempt的两份完成镜像、完整origin/READY或ACCEPTED、wire/usage/共享池/provider槽/sidecar、原admission和成果封印共同校验；全部实际Attempt双族扫描。缺单边、重复、错族/Attempt/类型冲突拒绝；无任何V2标记仅NOT_FOUND，不证明未执行，不补原键。服务端未调用完成writer、compile、provider、Worker或新账本写入。

Source原完成回执保持WAITING_APPROVAL/UNKNOWN，当前SUCCEEDED需原独立review_proof及精确version增量；Extract重建固定九字段canonical response，额外字段/布尔整数混淆及recovery_fence浮点拒绝。当前actor/project/双主体Grant撤权与期限、来源、接受快照/账本封印每次重查。历史completed_at核原冻结Run/origin/provider/实验边界，不拿今天设置重做或扩大旧动作；测试明确在执行截止后及今天run_seconds=1时仍仅阅读有效旧回执。未持久的完成时动态设置不能独立回推，原完成事务门未改。

页面新增独立只读Map与明确控件，和“核查回执”及完成POST状态机分开。空Map仅GET找回旧key并新鲜复读成果，不创建UUID或自动POST。NOT_FOUND/403/坏格式/详情不符中性化当前投影，保留真实Run.status/error和历史回执。旧完成意图参数冲突拒绝，匹配UNKNOWN也不被新Map升级。原手动“重新读取成果”可以在明确新鲜采纳见证下恢复普通worker成果的原业务路线，不制造可选完成回执；poll不自动清失败flag。不能把不存在的V2完成key变成原业务的新资格。

最终实际 **62 PASS，20.18秒**，一条现存Starlette TestClient弃用警告保留，未安装依赖。共74认证路由GET（72 ASGI、2实际loopback TCP），0业务POST：200×16、400×4、403×20、409×34。`runtime/http-sql-observations.json.gz`保留每次原响应、SQL/参数及前后55表指纹；33330 SELECT /105 BEGIN，成功和异常均0DML/DDL，sidecar不变。负例故意修改隔离副本的准备阶段与被测GET严格分开，不宣称整个pytest没有夹具写入。两次TCP的API/自有AnyIO正常终止、共享各3秒清理内、无强杀；原件在runtime对应目录。无OS/API独立进程重启声明。

62项内含实际页面控制器VM74项检查、两项UNKNOWN保留反例、旧完成控制器73项兼容检查；这些数量不再与62相加当独立测试总数。VM响应来自实际新认证GET及原详情GET序列化，VM不是真实DOM/像素验收。旧完成VM使用原脚本内部假的POST来验证原流程，未向业务API发送POST。模型/Mock/Worker/Source/extract/新review均0。

Source/Extract未审核完成原件沿用各自`protocol-*-process-recovery-20261022/after.sqlite.gz`及原sidecar，逐次核旧manifest。审核后Source来自本环境此前已完成并收尾的 `sim2act-review-ui-20261022-final/test_source_review_actual_http0/review.sqlite`，本轮只读归档为`source-reviewed.sqlite.gz`；55表与原Source仅runs/events/protocol_reviews三表不同，旧归档`protocol-review-ui-20261022/http-receipts.json`的原回执逐字段精确对应，见`source-reviewed-origin.json`。没有本轮新造review或响应补证。

独审发现的recovery_fence严格类型漏项已修；同类UI错误码漏保留也闭合：旧review失效与关闭工作区原先将OUTCOME_UNKNOWN清掉，2个同脚本VM反例实际红→绿，见initial-failed/unknown-red.*与最终runtime/unknown-preservation.json。旧完成JS块仅一处workspace投影保留error修复，POST/原键/回执逻辑逐字节对照不变；两个Python完成writer整文件与基线相同，不再称整个JS块完全未改。

失败历史完整保留：first.xml为测试夹具错误36F/5P（取不存在的phase、把dataclass当Pydantic）；second.xml/log为原VERIFICATION_FAILED实际400而预期限403/409的4F/38P；initial-failed/final.xml/log为原GRANT_REVOKED错误类别漏列的12F/48P。修正测试以接受原拒绝类别，未修改生产拒绝来迎合测试。targeted16P/4.64秒为中间定向结果，最终资格只认冻结版62P。

限定：仅合成SQLite、认证ASGI/本地TCP及控制器VM。本次两原完成封存样本的experiment见证均为null，代码保留适用实验期限门，不将此视作新的V2实验组合实测。新控件未做原生Edge/截图，PG应用角色并发、真实provider、G0/Cold2/W5、Cold硬刷新、全文像素及整体F2/R0仍未验。owner PENDING、publication=false；不恢复未持久UNKNOWN，不新增writer、权限、凭据、费用或部署。
