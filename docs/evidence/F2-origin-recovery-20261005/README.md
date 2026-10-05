# E13 来源请求锚定与回读恢复

2026-10-05，基线5d58951文档/d3de155源码，事前范围commit1151362。仅邻接修复，无新表/DDL/模型/发布/对外业务写入。

合成复现：同卡v2候选协调替换为合法v1的snapshot/version/fingerprint/goal并重算候选hash，修前GET200、preview SUCCEEDED，撤回v2新增条件材料仍通过；两个新负例修前FAIL。属于既定DB篡改防御范围，非已暴露API攻击或真实泄露。修前direct POST201后GET503的DOM错误状态断言FAIL，选择世代被内部clearApp改变导致catch失效。

修复使用独立持久goal_candidate_requests.request_fingerprint绑定已接受card/version/resource/capability，不以候选自身hash充当来源证明，不强制合法冻结v1跟随新v2。direct/preview明确区分已创建/已执行与读取失败，GET-only恢复可再次失败并继续重试，创建表单在恢复期间不会重复POST；内部showApp世代被调用者跟踪，项目/草案/目标卡切换使迟到恢复失效。

5个专项覆盖协调降版（含撤权）、合法旧版本正例、材料/能力重绑定拒绝及拒绝无副作用。Node/jsdom33项含既有20项、接受后回读失败、重复失败、GET恢复只创建/执行一次、三类导航迟到隔离。脚本最初同名变量和恢复样本默认旧CSV但断言新CSV数值的问题已纠正，属测试脚本错误；最终明确选择new.csv并核对40。此为DOM+实际本地HTTP，**不是浏览器/视觉/手机PASS**。

真实渲染仍沿E12 BLOCKED：受保护Chromium无可用sandbox，平台浏览器通道不可调用；未关闭sandbox/修改安全策略。源码回归与精确Server终态见随后归档。

当前来源读取仍重新打开旧CSV/源候选审计，并不满足AT10旧文件独立；[后续路线](../../F2/NextSteps.md)明确来源退休权限策略和已完成合成task fixture尚未实施。真实请求0，F1/Win11/完整P-B/AT10/Release未签收，历史AT02不改。

本地完整回归219PASS/5平台SKIP/1旧Starlette警告25.22秒，[JUnit](sqlite.xml)；ruff、mypy17模块、JS语法、diff通过。[DOM脚本](dom-regression.cjs)与[33项结果](dom-results.json)可复跑，使用E11合成fixture，仅本地HTTP。
