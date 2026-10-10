# 失败与未测账本

最终冻结与初始探测分开；全部初始日志/库/驱动输出私存 `/tmp/sim2act-resource-file-20261010`，摘要及原JUnit SHA256见 [初始账本](initial-run-ledger.json)。失败未删、不作为最终PASS计数。

初次候选证据提交c5929cd8受仓库既有 `* text=auto` 影响，将14份独审CRLF CSV在Git blob内归一为LF；工作区/私有原件仍逐字节一致。此问题在推送后Git blob核查中发现，添加仅该证据目录的换行保留属性，并普通后续提交恢复14份原件，不改原白名单hash、不强推、不改产品。最终集成须同时核对工作区及Git blob全部白名单文件。

| 初始运行 | 结果 | 原因与处置 |
| --- | --- | --- |
| initial-sqlite | 0PASS/5FAIL，6.620秒 | 新resource-files.js没有既有服务路由，HTTP加载hash不匹配，未进入文件选择。复用已注册app.js承载功能，未新增后端路线 |
| revised-sqlite | 4PASS/1FAIL，13.161秒 | business驱动错误假定创建新项目会自动切选；既有loadProjects保留旧项目。改为真实显式选择新项目 |
| business-repair | 0PASS/1FAIL，2.906秒 | 页面已完成业务链，作者数据库统计漏算项目创建2条Grant，误断言6。核对实际生产路径，改为project2+Save4+draft2=8，后台不改 |
| business-corrected | 1PASS，2.610秒 | 校正上述统计后的阶段探测，尚非最终冻结 |
| author-probe | 4PASS/2FAIL，27.614秒 | read-after-save揭示加入generation后Save清表使捕获context过期，列表失败提示未出现：清表后新捕获读回context。save-ABA驱动等待所有I/O为0但故意持有原Save，等待矛盾：只等待导航自己的动作完成，保留原I/O |
| final-probe | 7PASS/1FAIL，15.026秒 | save-ABA驱动硬写材料选项数量1，漏算env原CSV和返回项目的真实读取；改为释放迟到回执前后请求数完全相同，直接证明无自动refresh/新写 |
| aba-corrected | 1PASS，5.681秒 | 校正断言后的目标探测；最终双库按fdc91282全8新例及必要关联重验 |

冻结前独审静态检查还要求瞬态408/425/429保持UNKNOWN、精确32hex资源ID及Save/后续读ABA；均实现并有最终真实HTTP反例。不能把静态修复建议或初始探测算为独立最终签收。

原PG Future失败根因仍OPEN，本轮仅当前667原节点一次通过，不加预算/不盲重跑。HTTP200其余坏响应形式/入口和逐item历史map仍未闭合；原生Windows900/Edge240/Node150、真实provider/用户材料/语义/owner、完整F2/P-A/P-B/R0均未验收。SQLite一个PG角色SKIP明示；未跑全量及未变化Python的mypy。独审自行发生的失败另按其原件保存，不混入作者正式27集合。

独审自身失败归属：第一轮business worker漏JSON body，被原strict_json实际400拒绝；accepted-ABA/read-ABA在故意持有响应时等全局idle自超时。第二轮accepted-ABA通过，business/read-ABA仍有自己的idle条件问题；最终仅修私有harness后两者通过。全部三轮controller logs、failures和source before/after按114文件白名单保存，6首轮PASS仍保留首轮归属，不能称独审首轮全绿；见[独立报告](independent/FINAL_REVIEW.md)。
