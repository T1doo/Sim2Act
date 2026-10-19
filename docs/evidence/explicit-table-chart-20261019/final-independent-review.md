# 显式表格条形图 v1：有限独立审查

**LIMITED_PASS_EXPLICIT_TABLE_BAR_V1。** 在本片源码、安装包及已关闭原件范围内，未发现剩余确定 P1/P2。此前两项 P2（最终坐标舍入归零、工作区返回后按钮失效）均在第一次产品执行前修复；WIP 发现及修复记录保留。

本结论覆盖已有封闭有界表格，由用户明确选择原类别列和单一数值系列，重新鉴权同 Run 与其历史 Release 后展示 `table-bar.v1`。原顺序、原值、零基线及单位“未指定”保持；不推断语义、补值、聚合或创建业务 Run。安全 DOM、最终坐标拒绝门、原 Release/typed/内容指纹、迟到回调和真实撤权403清理均已核。两生产文件相对旧包变化，112个 Python 文件不变，无新增 producer/executor/Grant/API/表。

原始 JUnit 保存 **5次执行：3PASS、2FAIL；3个唯一节点最新均PASS**。首批 display142.862秒、共享 text/table253.198秒通过；guards191.934秒因100秒驱动watchdog后收尾异常失败，缺失最终日志不补造。其续验164.821秒失败保留（37检查/5图，测试撤权POST漏JSON正文，原400正文未保存）；最后仅补该请求正文/响应日志，guards219.284秒通过。测试记录/收尾和有界watchdog修改未删业务断言，首批两个PASS未重跑，不称单批全绿。

通过节点共有118条检查记录（32+40+46），并非118个测试；9份已绑定图形快照（4+5）。新图表两场景85次loopback页面GET、81份资产；共享回归119条ASGI记录已包含50页面GET、54资产与15夹具请求。可选protocol400及实际READ403明确保留。通过夹具12个捕获Worker各单claim/fence1：3个Mock生成任务、9个NoModel业务任务，6份合成模型请求；全部5次保存执行共10份合成请求。页面POST/Worker和真实模型均0，不误称生成阶段无Attempt/Reservation。

独立对比完整55表JSON：display与共享回归全等；最终guards仅指定一个READ Grant由revision1→2、revoked false→true，其余54表及其他Grant完全一致。已重算实际citation值、图形坐标/文本、HTTP原文SHA、历史Run/Release/typed绑定、资产与安装来源。负数/全零/非法数值为明确合成展示输入；错指纹为真实200后的受控前端污染，不冒服务端拒绝。`.svg`是JSDOM的outerHTML快照，以HTMLParser核验，**不是独立XML导出或原生视觉验收**。

作者封存941项/40,683,574字节中，918个非DB原件/36,110,365字节逐SHA核验，23个DB路径（5物理、18压缩副本）仅stat，4链接核字面目标；未打开或重算DB。作者清单完整SHA为 `ce00537bc3c7a5bbaa737d29e6c1a57cd4c603b8203decbd42823c4c995c5561`。189输入中183项直接hash、6旧压缩DB仅stat；141包文件与源/安装一致，wheel960382字节，SHA `bdd222e96b37be35c33a309c86f4bd33aec4505a628775d9eb89327e1a9ef3fe`。最终文档/Plan未见实质夸大。

作者XML观察器错误及HTMLParser更正均保留，非产品失败或新测试；本独审初始缺文件rg查询也保留。本人仅纯文件复算，未执行产品、测试、Node、Worker、DB、Git、网络或模型，未读私有留出集。依据见 [机器结论](final-verification.json)、[原件复算](raw-final-verification.json)、[封存核验](author-seal-verification.json)及既存静态报告。

本结论不提升任意chart、跨账号/项目/重连完整矩阵、服务器冷启、Windows/PG/原生浏览器/CI/LIVE/语义/真人验收/正式发布资格；人工PENDING、真实语义UNKNOWN。原旧缺失审查不恢复。后续归档、Git提交与推送由作者另证，本报告不预先背书。
