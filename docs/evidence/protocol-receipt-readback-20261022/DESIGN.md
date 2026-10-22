# 已接受注册核查的冷页只读回执定位

基线 3492531b31d8fb6e1677dc627e6bf7cf920c9101。原 F2-T09/AT05/18 要求已接受任务和回执可持久定位，不要求在没有接受证据时重发命令。

盘点：Run 历史已有持久项目/身份定位；protocol_reviews 保存完整原 request、公开 receipt 所需字段，PROTOCOL_REVIEW event 独立封印；_pending/_validated_review/_oracle 可在原事务内重新验证当前身份、授权、来源、结果、固定合成资格与封印。Source/extract V2 completion 有 events/journal 镜像，state-only recovery 只存 request fingerprint 而没有原请求完整体。三者不能混称同一恢复合同。

本片仅 Source/Cold 已接受注册核查的冷页只读定位：新增当前项目/Run 下 GET review-receipt，查完整已有记录，复用原校验后返回原 request 与同一公开 receipt。无记录返回显式 NOT_FOUND，不代表没提交；不生成 key、不调用 review()，不写 journal/table，也不调用 Worker/provider。独审后收窄为：多记录直接拒绝歧义，不猜 latest、不静默丢弃冲突；残留接受封印或成功态缺记录也拒绝损坏。未完成/其他 phase 不冒充回执。

页面在当前 Run 加显式“找回已接受核查回执（只读）”。该流程只发 GET，验证精确 schema/body/receipt 和新鲜当前 Run；记录恢复为 accepted-read-error，成果精确复读通过后才 accepted，后续只 GET。FAIL/UNKNOWN 仍禁止自动重新核查。已有内存 UNKNOWN 的 key 若和持久记录不一致则拒绝覆盖。

缺记录、错读、越权或未知响应在本只读恢复流程中保持关闭，不生成或重发任何键；缺记录不等于证明请求未提交。首次主动新核查的既有独立确认流程不作为“未知恢复”调用，不扩真实 provider、owner验收或发布资格。不增加 localStorage/服务端写入者、表、迁移、后台任务。此片不声称所有页面内存 intent 跨刷新恢复：无持久接受证据的请求、普通创建/完成/state-only recover 仍不由此自动恢复。

验证复用已完成 Source/Cold 封存事实，不新建模型/Source/extract。测试 GET 前后55表与sidecar不变；同pytest进程新Store新API冷连接，不称OS重启；未知/错项目/错主体/撤权/结果或seal篡改拒绝；controller全新VM复读既有receipt、GET失败不解锁、晚回调ABA隔离、缺记录零POST。Windows/PG/G0不由本片签收。先独审本边界再接运行路径。
