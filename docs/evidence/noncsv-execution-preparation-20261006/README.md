# 非CSV技术规格清单：离线执行准备

2026-10-06，本轮实际模型请求0，AT02批准余额0。交付仅本地文档/严格oracle草案，不注册产品ActionSpec、不产生真实模型成果/保存回执或应用、不触发CI、不push。

[完整计划](../../F2/NonCSVExecutionPlan.md)限定原V5《平台产品设计》§10.1原450—458行（9行/822UTF8字节）；原文读取已授权，后续指定原文/技术规格提取外发仍需单独批准。本批合成TXT42/84的已授权发送事实不被此范围限制否定。

`contract.json`绑定完整文档SHA、选段SHA、版本、逻辑资源ref、原行、四规范段逐字quote和必要义务；gold是开发方草案，owner/独立语义确认PENDING。`oracle.py`仅离线严格JSON/source/quote/义务一致性与确定性Markdown模板，无推理、数据库、transport或凭据读取。`prepare.py`实际执行1正28负，并用原公开system消息及完整现有工具定义、合成IDs/receipt/gold生成三轮**MOCK序列化形状**；没有InternModel/Client/send。模型artifact设计为JSON一份，MD是确定性派生视图；不把MD视图说成第二保存成果。

`offline-results.json`：1正28负PASS，三轮字符2530/3613/6184、UTF8字节2782/4357/7400、模型JSON1529字符、保守worker byte-envelope合计17719。这些是模拟形状，不是真实tokens/模型能力或保存检查；真实消息/callIDs可能更长，待接口/schema定稿后须再次做完整预检。

最短F1源任务链3次：模型选read→消费read反馈并选save→消费save反馈报告成果。提议未来最多3次/每次max1024/2工具/0repair/envelope24000/完整体8000字符且10000UTF8字节/≥6秒，全部**尚未批准**，原AT02的2000字符/512输出授权不能扩用。首次仍限822字节源，不扩大至4096字节任务族。完整P-A/P-B生成/冷复用没有当前非CSV注册接口，不能宣称总预算也是3或功能完成。

最小实施缺口：generic save_text的VERIFIED只是存储回读；需要严格来源/规范检查及持久检查结果的可信注册接口，才能形成P-B可信成功证明。注册后工具/schema改变须重新测量；未通过语义检查的成果仅候选，不是成功source。真正未见输入需独立gold，后续坏输入/跨owner/runtime/源版本变更/撤权/幂等负例当前NOT_RUN。无需Win11或进一步LIVE就能审阅本计划，但这些准备不自动关闭任何正式阶段门。

复现本离线草案：在项目已有Python环境运行 `python docs/evidence/noncsv-execution-preparation-20261006/prepare.py`；仅重写本目录开发草案合同/结果，无模型或外部请求。不会重跑已结束AT02 controller。原V5/历史LIVE/固定AT02 case/产品源码不改。
