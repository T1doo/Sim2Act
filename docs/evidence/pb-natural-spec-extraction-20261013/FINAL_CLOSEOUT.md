# 最终工程证据闭合独立复核

结论：**本次自然规范 P-B 有限工程切片 PASS**。最终产品/测试冻结HEAD `507b322e73758f4ad2ae2794382f5dee69760630`；独立r2封存目录未修改。本次只读核对作者终态与实际数据库/页面证据，无新测试、无产品写入。

最终唯一分母 **155**：旧回归120 + 作者negative-r2 27 + 作者UI-r2 5 + 独审新增3条正向。四份最终XML共157次执行；独审5中的status/effect_pointer两例与negative重复，明确扣除，独审本身仍为5/5。逐XML testcase ID去重155、全部PASS、0failure/error/skip，退出码均0。作者negative实际为27，不是曾预计28；3 deselected不是skipped也不计分。作者negative/UI耗时888.83/744.20秒。完整XML hash、唯一ID、交集、退出码见suite-source-check.json。

作者negative/UI的新440文件before/after完全等于独审507的冻结映射；最终当前440文件再算SHA也完全相同。旧120回归原before/after440一致，产品src与507全部同字节，仅三份未参与旧组所选模块的P-B test fixture变化，不能冒称120于新完整测试closure重跑。旧桥、74资格精确pin/map/原anchor/CHANGED/来源/config排除/sole literal不扩的结果保留在../final-independent-r2。mypy检查75个source（包含config）返回1，5个错误在status_report.py/tools.py，两文件与688基线逐字节一致；明确既有baseline失败，不写成mypy通过。

四项最新latefault用只读SQLite URI核真实NS_REJECTED事件与Run错误：source_revoke=GRANT_REVOKED→WAITING_RESOURCE，source_changed=VERSION_CONFLICT→FAILED，cancel=VERSION_CONFLICT→CANCELLED，bad_output=VERIFICATION_FAILED→FAILED。每项当前Attempt REJECTED_KNOWN、received_raw保留、无SAVE Operation/typed成果，排除意外lease/time拒绝的混淆。故障来自合成transport与测试DB变更，不是实际provider、真实并发攻击或API泄露。latefault-actual-codes.json保留精确Run与proof路径/SHA。

UI valid/lost/review-late-edit/commit-late-navigation/receipt-poison五场景全部正常完成，分别16/18/18/19/18项可见操作/状态检查。每场景20份实际静态资源SHA与冻结src完全一致、加载均200、DOM动作visible/enabled。每场景一次extractions POST，随后只对原key GET（污染回执场景两次GET），迟到review的编辑→撤销仍失效，迟到commit导航保留pending，恢复不创建替代意图；真正冷Store/Worker重开页面读取当前target材料的新typed成果，semanticUNKNOWN、goal acceptanceNOT_RUN、ownerPENDING。实际DB target Run SUCCEEDED，checklist原文/hash等于target注册resource，synthetic模型wire单次。这里的native DOM dispatch是在**JSDOM**内的DOM事件，不是原生浏览器验收；API为IPC_IN_PROCESS_HTTP。详见ui-evidence-check.json及原完整receipts。

三个最终目录（独审5、作者负向27、UI5）共45份成功Run驱动日志、45次实际claim、额外reclaim=0，每Run一次且最终SUCCEEDED。**恢复分支 NOT_EXERCISED**：不因最多三次驱动存在而声称失租恢复实测通过。其静态normal claim/new fence/原deadline限制与旧失败解释保留；原deadline或租约没有扩张。

全部失败历史仍保留，history-index.json列出作者每轮XML/hash/终态与是否计入final；旧独审5项4P1F、prepare原source READ后RUNNING/no Attempt的失败和后续r2成功分别存在，不合并改写。早期fixture、真实Release无name集成拒绝、load/lease及UI不存在commands页签失败均不隐藏；happy-r5有测试/资格变化只属历史中间证据。未将运行中、interim或旧重叠运行加入155分母。

有限结论支持“真实成功自然规范任务→受closed codec限制的可编辑/审阅逻辑→精确变量/当前Goal材料绑定→独立task_run应用→新材料冷运行”的工程链路，以及本轮既有门禁与回归。一次成功源与合成模型响应不证明通用语义。真实模型请求/费用0、semanticUNKNOWN/NOT_RUN、ownerPENDING；真实资料/完整P-A/P-B、人工签收、正式发布、原生浏览器、PG、Windows、CI/部署、旧库完整升级等NOT_RUN。来源退休后的独立逻辑许可不承诺，原source仍是当前授权审计依赖。旧取消安装窗口NOT_VERIFIED；actual model/reasoning/Fast/service-tier未核验，不声称切换或关闭。

closeout读取UI数据时初稿取checklist.semantic_status发生KeyError；修正为实际typed result.semantic_status、checklist.owner_acceptance后完成核查，这是审查提取脚本字段误读，不是产品或测试失败。所有实际运行分母来自XML与真实终态，未受该只读脚本错误影响。

本目录在报告/summary/SHA manifest生成后停止写入，早期封存目录保持原字节。
