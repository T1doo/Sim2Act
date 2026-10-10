# 本地 CSV 文件入口独立复核

结论 **LIMITED_PASS**，精确产品/测试冻结 `fdc91282b2107164ba33624246be6f50e007cd13`，基线 `66709612d5acd2e4b0dc41f75ef5c9f769508b0c`。独立只修改本目录自编 harness；未修改仓库、作者测试、Git refs 或使用作者 PG。352 文件与 Git/工作树前后逐文件 SHA256 一致；68 个产品文件中只有 app.js/index.html 改动，其余后台、API、Schema、执行器与基线字节相同。source-before/source-after 与 product-byte-bridge 为原件。

独立 SQLite 实际 HTTP/jsdom **8 新场景、9 页面、201 检查 PASS**；数字包括每页真实 HTML/script 冻结字节校验。另精确原667 HTML/app.js 实際 HTTP 页面 **1 个负对照、17检查 PASS**：正断言 `actual local CSV selector exists` 在旧页预期失败，原失败stack已保存。旧负对照其余资产/后台为当前冻结版本，仅证明新入口敏感性，不是旧数据库升级。

business从磁盘独立文件（中文、CSV引用逗号、负小数、CRLF）经FileReader→显式Save→草案创建→preview→精确内部快照/人工确认Release→创建实例→应用使用页两个新列运行，全部实际页面处理器及真实HTTP。独立拒绝模型provider的worker两次执行成功；SQL原资源bytes/hash、独立csv/Decimal期望1.75与4、两个不同持久AppRun、版本1/2及两typed记录一致。冷页面重新认证并打开实例，零POST、两个旧结果保留。fixture预建项目因此本次Grant增量Save4+draft2=6，未混算API创建project的既有2条授权；项目创建/资源保存/草案既有授权范围不扩张。

其余独立范围：空/超限/精确32768字节/多文件/非法编码/BOM/NUL/名称/后缀；取消、新文件胜过旧读取、项目ABA、身份切换；接受回复丢失后原意图冻结、双击及只读核对零重复Save；实际已接受再替换408/425/429/无效ID/损坏JSON保持UNKNOWN；迟到accepted保存不自动refresh、显式GET核对；accepted后列表错误遇新文件/ABA不能覆盖；手工修改解除文件原字节绑定。SQL资源/授权计数及AppRun/结果零额外新增均独立核对。

初始及第二轮 harness 失败全部保留：自己的worker请求漏{}，被原strict_json真实HTTP400拒绝；自己的idle在故意持有响应时等待全局网络清空造成超时。仅修私有harness，再跑对应失败场景。6个首轮PASS保留原归属，accepted-ABA第二轮PASS，business/read-ABA最终PASS；没有以作者测试或重跑掩盖初始结果。正式 source freeze 在每轮前后均匹配。

本结论不签PG/角色/历史Future10根因、旧数据库升级、原生/视觉/Windows900/Edge240/Node150、有效形状伪造ID的完整来源验证、刷新后持久UNKNOWN恢复、完整F1/F2/P-A/P-B或正式发布。Save原无幂等键，UNKNOWN仅页内Map；页面重载前应核对材料历史，不能声称持久exactly-once。HTTP200其他入口限制保留。PROJECT PENDING/BLOCKED_PARTIAL，semantic UNKNOWN，owner PENDING，overall NOT_ACCEPTED，LIVE=0。

证据根：/tmp/sim2act-resource-file-independent-20261010。COPY_WHITELIST.json列出允许复制的有限原件及SHA256，排除所有临时SQLite数据库。复制需同时保留初始/第二轮失败，禁止只留PASS。独立源、harness、磁盘合成fixture、每页network/hash/checks、SQL写入审计及持久DB投影齐备。
