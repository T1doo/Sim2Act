# Source / Extract 已持久完成回执的冷页只读定位

基线 `b2839be97450bf14aff896eb975bdca4c7b7e8d0`。本片先交实现合同供独审，不启用新入口，不运行模型、Worker、完成POST或CI。依据 V5 §8.2–8.3、分阶段计划 F2-T09 / AT-05 / AT-18：接受事实不能只在网页内；丢响应不能据此重复执行。本合同不扩展多请求Extract、UNKNOWN补证、Cold完成恢复或真实provider资格。

## 已确认的具体缺口

`web/protocol.js:64–65` 的 `protocolCompletionIntents` 仅页内 Map，键绑定token/project/Run。`completeProtocolExtraction:148–185` 仅在原页保留body/key时发完成POST或只读复查；硬刷新后不能定位原完成请求。现有 `protocol_reviews.read_receipt` / `/review-receipt` 定位的是**后续注册合成核查**的请求，不是完成命令。即使两种动作的回执都存在，也不得互相代替。

已有事实足够新增只读定位，无需新表/事件/worker：Source 的 `PROTOCOL_SOURCE_RECOVERED_V2`（`protocol_source_completion.py:793`）和 Extract 的 `PROTOCOL_EXTRACT_RECOVERED_V2`（`protocol_extract_completion.py:621`）在原完成事务内，将 `request`、`response`、`completed_at`、原发送/恢复fence镜像写入 Run 与对应Attempt；Source另含原admission。普通 `PROTOCOL_COMPLETED` 是成果封印，无完成命令原键，不能拿它制造回执。

封存进程样本的 `after.sqlite.gz` 实际各有一对V2事件：Source原键 `process-complete-source-known`；Extract原键 `process-complete-known`。这里只核压缩文件manifest及只读事件形状，不重跑旧进程/完成套件。详细Run/Attempt关联与原件摘要见同日 `protocol-completion-readback-design` 证据。

## 最小服务端合同

拟新增一个无body、无key参数的认证GET：

`GET /api/projects/{pid}/protocol/runs/{rid}/completion-receipt`

固定六字段 `{namespace:"protocol-completion-readback.v1", run_id, phase, state, request, receipt}`。phase仅`source|extract`；FOUND返回原持久request及**原response**（含原cached=false，不把一次GET伪装成执行或幂等POST）。NOT_FOUND时两者均null。客户端严格字段、类型、整数、namespace及Run/phase关联，沿现有CompletionInput/receipt校验；不收客户端补充response、path、owner、deadline或expected key。Bearer只走现有认证依赖，无磁盘/URL保存。

入口保持现有V2完成的 test_only + settings.mode=mock 边界，不授权其它运行模式。首先在原事务中验证当前用户拥有项目、Run principal/project匹配，调用完整`verified_pending`（接受快照/Run绑定、当前双主体授权、冻结合同、来源依赖及完成账本封印），拒绝不支持phase/bounded-check，再检查下述V2完成标记；授权前不开sidecar。完全无标记时直接NOT_FOUND，不因普通worker历史缺V2 sidecar错报损坏V2。有标记才在现有服务器选定sidecar锁及原事务内重新核授权、全部事件及完整见证，不信前一个事务的PASS。不初始化/迁移、不补锁文件、不修权限。

只读验证可复用 Source `_verified`、Extract `verified_receipt` 的完整持久见证校验：原请求wire/响应/usage、共享池/provider槽、Attempt、来源proof和sidecar摘要仍按现实现新鲜核对。无 provider/runner/transport/compile/reserve/accept/complete_in_tx/store.event。GET只能SELECT与事务/既有锁；持锁不等于新业务writer，测试应证明无DML/DDL和全表/sidecar不变。

在该Run及其**全部实际Attempt**中查两种V2完成事件，不只拿第一个或限一条。正确family必须恰有一份Run事件＋一份预期Attempt事件（Source最后Attempt，Extract唯一Attempt），两份完整领域值精确一致。额外/错族/错Attempt/重复/仅缺一边/字段错型/未知版本一律冲突关闭，不能降为NOT_FOUND。全部相关完成事件均无时，返回NOT_FOUND仅表达“没有可认证的持久完成回执”；包括普通worker直接完成但没有V2命令原键的Run。它不证明请求未发/未完成，不允许换key或据此POST。READY/ACCEPTED本身不构成FOUND；STARTED/UNKNOWN、旧V1与bounded-check不升级。

验证存储原request为精确CompletionInput，response须恰为原九字段canonical结构：namespace/Run/status/version/fence、该族result或plan fingerprint、provider_requests=0、automatic_resend=false、cached=false；严格类型及完整领域指纹一致，并绑定原完成封印/READY或ACCEPTED、原发送fence及Source admission。Extract现prior分支没有完整重建response结构，不能不加审查便当新GET的充分validator。不能仅比较两个JSON相同，或仅凭PROTOCOL_COMPLETED的result存在便返回FOUND。

## 历史完成、当前授权与期限

这是回执阅读，不是再次完成。`completed_at`须有限并位于原accepted/READY之后、冻结Run/provider/origin及实验原边界之前；不续原Run/lease/TTL，不退预算或清halt。Source现有prior分支的 `_bounds(current=False)` 是历史依据；Extract读路径须同时核原origin/provider、冻结Run与适用实验边界，不能只看两份回执或用当前放大设置补合法性。

两族 `bind_request` 已将发送时 `created_at+min(frozen.run_seconds,worker.settings.run_seconds)` 写入origin.deadline，并镜像/参数绑定；provider_deadline也已持久。适用实验的bound_at+300从验证后的原binding重建。Extract现prior仅显式比较origin/provider上界，新GET须明确补齐历史Run/实验检查。没有持久化完成时后来变更的进程settings.run_seconds，不能声称新GET独立重建了该未记录配置；原完成事件是已通过原完成事务动态门的持久事实，新GET不拿今天settings倒推、不重做该动作，亦不改写或重新授权旧结果。

当前时间晚于原执行截止不自动抹掉历史已完成回执；不调用需要`now<deadline`的新执行门以重做结算。**当前认证、项目拥有权、Grant有效期/撤权、来源内容/版本、合同及账本一致性仍每次读重查**，因此历史完成不等于今天有权读/执行。授权已过期或来源变更时GET拒绝，UI关闭当前投影。证明历史时合法与证明现在可执行分开。

Source原回执固定WAITING_APPROVAL。当前Run可以仍version=receipt.version/semantic UNKNOWN，或经现有独立review证据变SUCCEEDED、version=receipt.version+1；必须调用既有review_proof验证该转换及相同fence/成果指纹，绝不把完成回执当核查PASS。Extract仅原SUCCEEDED/version/fence与compiled_plan指纹一致；owner仍PENDING，publication=false。取消、未知/不支持状态转换或缺关联证据拒绝，不改真实Run.status。

实现先增加私有无副作用的“已完成证据验证”函数；新GET绝不调用`complete_source/complete_extract`以防缺记录走写分支。优先保留原POST代码/异常顺序；如需共用prior验证，必须先证明提取出的函数纯只读、原POST分支行为等价，不借本片修别的POST接受域。

## 页面合同与失败关闭

增加独立、明确标注“找回已完成任务回执（只读）”的入口，Source/Extract均可见；与“找回已接受核查回执”分开展示。只读入口不要求确认框，不创建request_key，不自动点击完成/核查/提取/Cold。

定位结果保存在独立`completionReadbacks`页内Map（同token/project/Run域），不装入可发完成POST的命令状态机。若同页已有原完成意图，body/key不符则冲突关闭；匹配也不能将未知请求擅自当成可重发。FOUND后只GET原Run详情，核完整状态/成果与原回执后才能展示“原完成回执已找回、当前成果已复读”；找回本身不解锁业务路由。该Map不持久化Bearer或UNKNOWN意图。

每次await后重核连接/身份/project、intent、workspace generation、Run；普通后台poll不能冒充导航取消有效定位。明确登记本次已确认回执后的读见证，只有后来开始、同上下文且严格匹配的认证详情读可恢复；旧失败不能盖掉更新成功，旧响应不能在关闭/切换返回后复活。不得通用缓存PASS或降低来源/授权重读。

NOT_FOUND/403/坏格式/详情失败均显示“当前完成状态不可确认，仅可只读重核”，清当前成果/可见完成回执/旧确认文案、提取与Cold入口，保留原历史键和回执但不把它们呈现为当前已确认；真实Run.status不改成UNKNOWN。核查投影和完成投影各有状态，失败中性化不得篡改独立核查事实；业务路由必须同时满足当前新鲜Run与适用投影条件。独立的Source完成命令旧流程保持，不能因读定位失败误解锁或误禁合法的未完成Source。

实现独审收口：可选历史完成回执不能变成普通worker成果的新资格。原“重新读取成果与核查状态”按钮可显式GET新鲜原Run，在严格intent/selection/身份/project/workspace/Run采纳见证下恢复原成果与原业务门；无V2回执仍无FOUND/accepted、不补key。自动poll不清失败标记，403或过期响应不恢复。投影失效/关闭必须保留原错误码，尤其OUTCOME_UNKNOWN；仅清展示不能将其变为无错误。此修正不修改原完成POST、原键或回执逻辑。

## 实施验收边界（尚未执行）

仅复用上述封存完成事实及原sidecar的隔离副本，无新Source/extract/Worker/Mock/模型，无完成或核查POST。必要认证HTTP/控制器回归：两family空Map→GET找回→详情严格复读；当前Source WAITING_APPROVAL与合法review后状态；超过历史执行截止仍可经当前授权读旧回执、当前Grant过期/撤权拒绝；错owner/project、错槽/Run/wire/usage/sidecar、缺/重复/错Attempt镜像、普通worker完成无V2key、READY/ACCEPTED无完成、混淆review与completion、读取失败无旧PASS、迟到/关闭/上下文切换及既有意图冲突。异常必须无DML/计数变化，无新key；55表和原sidecar完整对照。

设计ACK只允许进入该最小代码切片，不代表新GET/浏览器已通过。不重复旧37/20或进程套件，不在本片再开Edge；原生冷页控件将来仅按最终源码与适用授权单独核验。PG、真实provider、G0、Cold硬刷新、完整成果全文像素与整体F2/R0仍未验。
