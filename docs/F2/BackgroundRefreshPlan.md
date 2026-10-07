# 慢 API 下的后台刷新有界修复

先行范围：8c106e9 最终 PG 全量真实 1278 PASS / 4 SKIP / 1 FAIL / 1407.99s；Report UI 原 90 秒 Timeout，817 进度记录、40/49 检查、374 请求启动，真实源码加载回执未到达。SQLite 同源1241 PASS / 42 SKIP / 698.42s不能覆盖该失败。旧 e4 和本轮 trace 全部保留。Graph/Report 最小 PG CRUD 角色及21角色检查真实通过，不替代整体通过。

实际源码 app.js 的2500ms async后台timer没有in-flight边界，整次refresh串行加载材料、目标、通用App、多family目录、任务历史。慢API使整次refresh超过周期时，新tick会在旧链结束前进入并增加generation；既有generation检查不撤回已发送GET。实录34health起点、51genericApp inspect、42namedApp list；后段60–90s响应中位642ms，最长3202ms。该重叠风险由源码可复现，但尚不宣称它是本轮PG超时唯一根因。

最小产品变更仅将既有后台callback设单一in-flight：在第一个await前占用，try/catch/finally释放；忙时忽略该周期tick，下一原2500ms周期可重入。全部原请求链、现有identity/project/generation guard及错误显示保留。显式用户refresh/open不走该后台busy门，不强行取消用户行为。项目/身份切换不把后台busy强制清零；旧链只能通过原guard退出再finally释放。无请求缓存、权限缓存、自动POST/提交恢复、额外模型、预算或timeout变更。

必要oracle使用真实加载的产品app.js与完整DOM，延迟API响应并重复触发原后台callback：整个链最多一个后台请求链；显式刷新仍可执行；失败后下一tick恢复；旧项目/身份延迟响应不能重绘新上下文；unknown提交原键/body不变且后台零POST。该异步调度oracle是合成API，明确不是真实HTTP/PG/native。

修复后先原49实际HTTP/DOM和相关图/旧应用专项SQLite、独立调度oracle，再一次专属PG定向Report49保持90秒和14promotion/7fixedMock，记录实际HTTP进度/加载hash/完整权限快照，失败不自动重试。定向通过后再冻结必要新版全量SQLite→PG；不重演未修复full或跳过失败。Windows900/Edge240/Node150仍不改，native预算继续NO_GO，普通push需等待本轮问题真实闭合。
