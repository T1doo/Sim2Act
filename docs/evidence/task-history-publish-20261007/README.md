# UI 发布与既有 Windows 验收：进行中

本轮已获普通快进同步与一次标准CI授权。发布候选基于d3d4fa5，仅回执恢复/任务历史/UI/browserfixture测试和证据，不含activation68443或空白gate修复；不复用失败真实实验额度。

PG新路由专项6PASS/1browserDESELECT，应用角色真实CRUD读取及DDL42501拒绝，临时schema/role实际0。全量本地/新Edge/像素/CI终态正在等待，不能预写成功。

本地冻结闭合：907 collected，869PASS/38SKIP/0FAIL，3warnings，250.86秒；显式SQLite+Mock/HTTP/JS混合，非全PG。164源码/脚本/测试前后hash一致。Ruff全src/scripts/tests、mypy34、Node双helper语法、diff PASS；模块独立真实HTTP/JSDOM39PASS，7Run/2MOCK/1VERIFIED，计数不变，模块中间失败日志保留。

独立发布边界复审PASS（新renderer审计原先仅记录的缺口已关闭），前后均断言原保护；workflow15min/browser4min/runner/contentsread、fixture/audit/emit限名2MB保持，mobile错误/外域监听补足。snapshot helper只读，normal Mock Worker产生真实PARTIAL。无activation68443祖先，无protocol_egress/db/workflow变化。PG专项6PASS与临时schema/role0、owned服务器--rm删除已实测。尚未运行新CI或宣称Edge/像素通过。当前仅准备普通fast-forward同步精确候选SHA。
