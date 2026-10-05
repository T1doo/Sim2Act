# E14 合成完成任务及来源退休切片

2026-10-05；基线c40b752/4d01fb7，事前范围bd27dca。E13独立静态复核已关闭两项，未独立执行/视觉；E14本轮主开发验证。实现范围与API/授权策略见[TaskRetirement](../../F2/TaskRetirement.md)。不修改V5/F1历史/AT02。

36新增工程检查：本地35PASS/1PG应用角色待CI；完成task/oracle、实际FAILED及FAILED/PARTIAL/UNKNOWN/RUNNING禁止提取、退休后新Store/冷API结果40与坏输入FAILED、源/目标user/project/app五类撤权及过期、跨owner/project、证明/版本/候选重新hash/删除来源/退休回执及内容复活篡改、明确consent/策略/版本/hash、既有F1/目标卡/应用共享源拒绝、并发任务/提取/退休幂等、不递归PREVIEW、证明不得夹带旧内容、LIVE创建拒绝。无F1 Run/attempt/operation伪造。退休前后grant逐项相同；旧resource content和本地任务input/output清空，旧GET/工具读拒绝；source授权仍逐次检查。

完整SQLite254PASS/6平台SKIP/3警告30.16秒，[JUnit](sqlite.xml)。ruff/mypy18模块/JS syntax/diff通过。警告是旧Starlette及并发构造FastAPI导致Pydantic alias warning（保留）。最初7项专项失败是新测试错用了HTTP409/503代替现DomainError400映射，实际拒绝已生效；纠正断言后专项通过，未修改现错误契约。HTTP脚本最初把`GET /api/projects`数组误当items，纠正后实际跑通，不是产品缺陷。

既有E13 33 DOM检查保持PASS，[当前复跑结果](existing-dom-results.json)。[新增脚本](dom-http.cjs)/[14项结果](dom-http-results.json)使用E11合成fixture的loopback HTTP与实际产品JS，新增隔离旧source CSV实际完成task、提取、显式退休、旧GET拒绝、证明不含原答案、页面显示LOCAL_DECLARATIVE_TASK、冷页新amount40/quantity5、FAILED历史及不递归；**Node/jsdom不是浏览器/真实像素或手机签收**。真实受保护浏览器沿E13 BLOCKED，0检查，不绕sandbox。

新应用执行仍PREVIEW_ONLY，来源为实际LOCAL_DECLARATIVE_TASK成功固定数值任务。只移除这个合成来源旧内容依赖，源授权依赖保持。完整P-B/AT10需原始规格全部证据、真实任务族/通用生成/正式发布等；本轮不签收完整P-B/F1/Win11/Release，真实模型请求0，未导出备份/上传额外包。

精确源码[c776fa2](https://github.com/T1doo/Sim2Act/commit/c776fa24dac957485a65337ed3d4b428848b584c)已普通push，[ServerCI37349609291](https://github.com/T1doo/Sim2Act/actions/runs/37349609291)SUCCESS/job111896821583/2m31s，PG260PASS/0FAIL/0SKIP/1旧警告69.05秒。36新专项含最小应用角色完成任务/提取/退休/新输入/FAILED历史/回读/重试；Setup三新表显式迁移、原生smoke、ruff/mypy18、Report/Cleanup通过、server stopped。实际平台/计数[results](windows-results.json)、完整步骤[run](windows-run.json)、[92源码指纹](source-hashes.json)。保留Node20动作被GitHub强制Node24警告；本地合成服务已停，未独立复跑/视觉签收。
