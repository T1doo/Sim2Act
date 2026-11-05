# 新P-A4096正式接线

在e6f0b6eb合同/策略基础上，准备请求可明示pa-natural-output4096.v1，仅P-A V2接受；P-B拒绝。原键回读同时比较准备请求与冻结合同的profile，不能只改冻结响应绕过输入身份。旧缺省字段不新增序列化键。

正式readiness返回原profile；API仅在桌面启动选择已批准、目标版本/指纹和原生成键全匹配时选择natural-checked-candidate4096.v1。不接受调用方直接传预算。Worker在原production绑定下重核profile；序列化、预留、sender wire白名单、提供方settings及同aid历史核查共同使用分阶段上限。实际顺序为read1024/check4096/final4096，应用Source/Cold限额1024，3/2/2槽、每Run64000、总192000、总接受输出7168和原期限不变。

前端新P-A准备明确展示候选预算与运行预算差别；旧回执按旧预算显示。新profile查账使用正式production-journal，核对原合同/批准/主体/项目，再显示原始账本；不存在账本时按原拒绝反馈，不能显示伪造零用量。

验证：最终后端与协议11项通过，含准备/原键回读/跨scope批准拒绝、生成阶段budget与旧scope/读阶段拒绝、旧自然合同兼容，以及原API+Worker+MockTransport完整三请求生成PARTIAL。该Core正例用合成readiness投影，不冒充真实生产permit；实际请求参数为1024/4096/4096，应用限额仍1024。新prompt同时说明候选4096和默认/运行1024，保留完整Goal/材料。

界面恢复26场景通过，使用相同前端字节与前一后端测试快照。最初26项在旧驱动未打开目标卡分区时失败；改成点击实际分区导航，不取消隐藏。另修复JSDOM matchMedia桌面夹具和Windows读取UTF-8测试结果。失败XML保留。正式新账本展示分支尚未用真实账本做DOM验证；最终同包组合、实际PG4096/模型、Source/Cold新输入仍待完成。

此版本源码已改变，原资格清单不再匹配。下一步明确审阅、封存新清单、构建同源包后新建范围验证；不修改任何旧未知任务或批准。未签UI-ready或R0-ready。
