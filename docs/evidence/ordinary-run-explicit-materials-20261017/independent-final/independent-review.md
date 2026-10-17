冻结源 `09155e6e3415acb1d53aff80248d745badd37805` 独立复验准入通过。仅运行 `tests/test_ordinary_run_materials.py` 三参数一次，RC0，3 PASS / 0 FAIL / 0 ERROR / 0 SKIP；JUnit 16.073s。重复作者同三节点，额外唯一节点0。117份 tracked src/相关测试文件执行前后与冻结 Git 完全一致，源码差异为空。

use/refresh/frozen 分别15/8/6条检查、53/60/35次产品API请求；共29检查、148请求（143 GET、5 POST），每例21份实际served资产均由pytest校验SHA。每例保留SQLite DB、info、完整请求响应result、空stderr、database-proof；命令、日志、XML、前后源码hash一并保留。

use 从9份材料中明确选择，实际API接受0/1/8三个Run，SQL确认各自Run refs与持久合同一致。仅1份材料的Run执行一次冷MockModel Worker，发生2次合成模型请求、0真实请求；读取意图精确绑定该材料，结果PARTIAL，整目标验收NOT_RUN。0/8两个Run仍QUEUED。9份选择保留并被UI阻止，未发送POST；GoalCard独立选材保持不变。

原静态阻断已关闭：列表未就绪时允许显式取消选择，非零仍禁新提交；refresh在真实GET200后模拟一次交付失败，验证保留ID、可取消至0，及刷新/项目ABA/身份切换隔离。frozen模拟真实已接受响应丢失，再过滤一次列表交付；原ID/原body/key保留，重复提交被阻止，恢复实际返回同一Run。列表过滤权限未改变，不是撤权。refresh/frozen各另有一次fixture保存第10份材料，沿用既有Save和Grant政策。

DOM初始化及GoalCard分离未见新增阻断；新提交读取当前显式选择，原sending/unknown恢复不受新草稿校验干扰。修复前c769作者2P1F和66786红例本独审均未执行，没有独立失败可归档。

范围是合成SQLite、实际ASGI/served JS、JSDOM事件；列表未就绪时0材料只验证UI可提交，实际0材料202在列表健康时执行。原生浏览器/Windows、PG、真实模型/场景语义、远端CI及额外恢复矩阵均NOT_RUN。原始manifest列出27份文件及逐件SHA/size；本目录封存后停止写入。
