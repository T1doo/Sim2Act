# P-B 原提取 key 安全关闭：最终有限独审

**有限独审通过，无剩余确定 P1/P2。** 当前资格源码为 `f7a48c062dfbcd3b9b515d893bb696eb65d69d9a`。非作者审查包含合同/源码、精确冻结字节、原件独立复算；实际产品资格由 root 执行。独审者未执行产品函数、HTTP、Worker、模型或SQLite查询，只对已关闭DB文件计算字节摘要。

交付补齐真实缺口：原票据已保存而POST未受理时，可显式永久关闭原key；另点原GET核对后才忘记票据，迟到或换body的原key POST永久拒绝。已受理结果不可关闭/取消。复用现有项目事务锁、delivery_graph_requests双seal及source/target权限门，无新executor、Grant种类或权限扩展。关闭只新增2份metadata；原提取按旧合同仍创建runtime和2个工具Grants，不能说全阶段0Grant写入。

三项WIP问题已修并通过最终相关资格：marker整行读取移到target gate后；terminal由PK和独立request/response scope锚联合识别，canonical读取严格恰2行；相关接受记录严格4journal集合、原key独立锚，损坏/残留不冒充absence。源码顺序及精确快照见各review文件。修前发现来自首次工具完整可见源码；外部snapshot落盘时root已修，未冒称修前原文件已保存，也未独立动态复现原漏洞。

| 冻结/批次 | 后端 | UI | 结果 |
|---|---:|---:|---|
| f0652b42 | 5P/2F，176.660s | 2P，236.503s | 保留POST-first默认5秒锁等待500及撤权码observer错误 |
| ce407aae | 6P/1F，209.969s | 2P，246.089s | 保留反向CLOSE-first原POST默认5秒等待500 |
| f7a48c06 | 7P，198.531s | 2P，256.124s | 当前9唯一全部通过 |

总计27次执行、24PASS/3历史FAIL，不能称三轮全绿。f065→ce仅close wrapper有界SQLite wait30与两处精确GRANT_REVOKED断言；ce→f7仅普通extract wrapper同wait30。去对应唯一wait参数后模块AST保持；不改共享_extract、试验控制器、Store、权限、clock/lease/deadline或PG设置。每轮685执行输入前后0漂移；最终133生产文件匹配Git冻结，当前685输入0漂移。

最终7后端实际证明双连接/线程在真实BEGIN IMMEDIATE重叠，两种赢家串行得到关闭/拒绝或接受/拒绝；exact与changed-body latePOST拒绝；旧key幂等、目标Goal失效且未受理可关闭、完整sibling允许、目标撤权sibling保守UNKNOWN、账号/项目/当前来源拒绝、损坏锚/单half错位/额外seal及事务回滚failclosed。不是PG或网络原生并发验收。

最终两UI场景合计 **118checks、62actions、118页面API、108资产、226实际HTTP、4次新DOM**。原POST未送达→冷页UNKNOWN→显式close仅保票据→完整terminal SHA真实计算后延迟投递、关闭旧panel仍不忘记/不paint→另显式GET核对才解锁→原请求完整字节迟到409→新key须重新审阅/确认；以及实际接受丢201后关闭409、原GET+fresh app完整核验才忘记。独立复算原17字段票据/fullExtractInput hash、完整CloseInput hash、去自身terminal hash、实际SHA输入字节/事件序列、原wire原字节及各HTTP响应hash、原全部行保留与精确delta。每份当前页面资产与冻结源SHA匹配。

三轮六份正常fresh source seed实际 **24次Mock**（每seed生成3+来源1）、6次成功来源Worker claim；当前轮其中8Mock/2claim，页面Worker0，真实模型0。没有复制seed次数冒充额外模型执行，也没有伪造成功行或修改业务时钟。

读取屏障只覆盖所选Run/contracts/resources/operations/intents，不覆盖task_extractions/delivery_graph_requests的wire JSON；因此“完整wire前鉴权”为非作者源码顺序复核，实际资源单元屏障通过，不能扩大为实际wire-cell全库零私有读取。

正常source push及精确scoped fetch实际exit0，远端156→157只新增 `dev/pb-extraction-close-20261018`，SHA为f7a48c06；其它远端HEAD保持，本地上游0/0。此结论不提前背书后续文档/证据提交推送，最终交付由root继续核验。

保守限制：来源fullproof漂移、相关已接受sibling目标撤权/stale或64app/256journal预算不足仍UNKNOWN，不能绕权限强行关闭；30秒是有界等待，不保证任意负载永不超时。Windows/native、PG、远端CI、真实模型/语义/真人验收/正式发布未执行。旧永久取消安装candidate双actor digest窗口完全排除；旧满盘独审报告缺失与exit139根因Unknown不关闭。P-B v1→v2/下载只读定位另存，未包装成本轮资格。

独立纯原件脚本首次误将HTML资产当JSON，实际重定向stderr及首脚本保留；修复仅parser和资产分母，没有重跑产品或改原件。root汇总首脚本曾将pytest current symlink重复计数，原脚本及明确标注的工具stderr转录保留，排除symlink后纯汇总通过；不能把该转录说成当时已重定向原stderr。

原始原件位于 `/workspace/pb-extraction-close-evidence-20261018`，本目录 `final-independent-artifact-audit.json`提供完整原字节清单、三轮复算及推送核对。封存后停止全部写入；仓库和原件始终未由独审者修改。
