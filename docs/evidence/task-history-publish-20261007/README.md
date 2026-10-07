# UI 发布与既有 Windows 验收：进行中

本轮已获普通快进同步与一次标准CI授权。发布候选基于d3d4fa5，仅回执恢复/任务历史/UI/browserfixture测试和证据，不含activation68443或空白gate修复；不复用失败真实实验额度。

PG新路由专项6PASS/1browserDESELECT，应用角色真实CRUD读取及DDL42501拒绝，临时schema/role实际0。全量本地/新Edge/像素/CI终态正在等待，不能预写成功。

本地冻结闭合：907 collected，869PASS/38SKIP/0FAIL，3warnings，250.86秒；显式SQLite+Mock/HTTP/JS混合，非全PG。164源码/脚本/测试前后hash一致。Ruff全src/scripts/tests、mypy34、Node双helper语法、diff PASS；模块独立真实HTTP/JSDOM39PASS，7Run/2MOCK/1VERIFIED，计数不变，模块中间失败日志保留。

独立发布边界复审PASS（新renderer审计原先仅记录的缺口已关闭），前后均断言原保护；workflow15min/browser4min/runner/contentsread、fixture/audit/emit限名2MB保持，mobile错误/外域监听补足。snapshot helper只读，normal Mock Worker产生真实PARTIAL。无activation68443祖先，无protocol_egress/db/workflow变化。PG专项6PASS与临时schema/role0、owned服务器--rm删除已实测。尚未运行新CI或宣称Edge/像素通过。当前仅准备普通fast-forward同步精确候选SHA。

唯一CI37574285701/head00a46969终态FAILURE：907收集、900PASS/6SKIP/1FAIL（621.05秒）；Setup/应用role smoke/Report/ownedCleanup SUCCESS。唯一失败是既有可选registered-generation jsdom依赖探测10s TimeoutExpired，栈在WindowsPopen stdout reader join；底层为何延迟UNKNOWN，不虚称模型/产品失败。Edge因工程失败SKIPPED，无新PNG/像素验收。失败raw excerpt及run/job完整状态已保存，未重跑。普通gh日志redirect403，已授权GitHub connector成功取回实际日志；未改代理/安全策略。
