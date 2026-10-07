# 整合步骤、失读恢复和应用使用

父授权从bd56f808起整合三个独立产品切片，产品候选暂不push/CI。先核对525edbe相对bd仅docs且无额外产品祖先，正常fetch远端bd后普通fast-forward同步525edbe，remote exact一致；docs不匹配既有workflow paths，没有手动dispatch。本地独立dev/product-integration-local，原树保留。

阶段1两个真实merge：05670de整合d069e03（包含9f30cd2和c041ace等价文档），8bd1c89整合1ebdb719。Plan/Log按共同前缀+两边追加完整保留；项目handler选d069清Run详情、开头加clearApplicationUse(true)，身份清理自动保留两者。一次冲突脚本缩进错误使本地临时merge含标记，立即纠正并amend未推提交，未测试或发布错误树；最终无标记、Node/diff通过。74生产文件逐byte/SHA与稳定8bd源对应，独立复核通过。一次913 collection与merge并发，明确AMBIGUOUS_TRANSITION，不作525基线；稳定整合914 collection可信。

阶段2稳定8bd完整回归：SQLite876PASS38SKIP0FAIL/914/262.84秒，PG910PASS4SKIP0FAIL/914/510.56秒，两者2warnings。PG为owned postgres17 loopback新container，既有每test schema明确迁移/CRUD最小role，非API建表；4SKIP为Windows原生启动、两个SQLite-only协议UI fixture、本机protected Chromium helper阻塞。各自全日志保存，Linux保护未绕过，没有新PNG。新增同会话16检查：正常CSV两参数v1/v2后交替普通PARTIAL/VERIFIED步骤、失读GET恢复、双清理+旧命令不可写、两详情实际200的late failure及success/ABA、foreign403、合法格式错实例回执锁定GET-only、冷会话两历史零POST。后端3AppRun/2data/2MOCK RECEIVED，Grant/Principal全行不变。最终shared core和native fixture胶水先期2PASS；canonical targeted9PASS，PG补充8PASS。实际worker FIFO目标拒绝不重排/重置，不把FAILED/UNKNOWN/PARTIAL签成完整成功。

阶段3新增受保护Edge接线候选：共享16core，既有agent API/正常SQLite fixture，旧合成A/B身份与权限前置；新CLI-only integration-worker严格要求真实全库最老QUEUED及instance binding，正常Worker。旧agent33和注册生成29断言先原样完成，随后同page新document关闭测试poll以确定性控制双held回复，原产品timer未改。新增phase真实renderer before/after+每capture审查、所有authority fingerprint相同、3AppRun/2versions/仅2MOCK、零外origin/运行时错误。复用main desktop/mobile槽为新cold-use画面，history原布局断言保留但JSON明确截图已superseded，agent生成和protocol槽不改。不增加emit名字/文件上限/目的地、浏览器/API服务/runner/权限/凭据；workflow/WindowsPS/保护args/15min job/4min browser/150s helper/12sDOM原样。新原生Edge/PNG NOT_RUN，等待下一发布安排，不借旧bd绿灯签收。

最终候选精确全量SQLite/PG将在源码freeze后重跑，另追加实际结果，不以首轮914签收新测试/fixture接线。新增bounded probe仅progress可选require.resolve改DEVNULL+10s，actualdriver捕获/30s/断言不变，6超时FAIL/缺依赖SKIP负例（原4+progress2）通过。新增native fixture测试是实际agent seed和FIFO正常worker，不是浏览器替代。独立shared-harness早退/ModuleNotFoundError原FAIL保留，修正确认results存在+16checks/模块路径/单次seed。

本轮真实模型请求0，既有MOCK样例attempt与此前另记的1真实请求460token不是同一计数，历史不改、不refill。F1/完整AT02/Win11/目标语义/正式发布/通用应用/完整P-B不提升。下一核心缺口为固定内部使用到正式应用验收的衔接；现阶段只可信工具结果与固定CSV新column，没有目标语义签收。stage-only文档与候选本地保存，最终SHA及精确CI差异后返回父线程。
