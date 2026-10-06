# AT02预算等待期间的有限离线准备

产品基线b91e4e318418fe107195500501d4cbf690ea3f02；源码/脚本/原cases/V5/历史LIVE完全不改。当前真实预算0，父线程最多2请求/每次2048输出token上界申请尚未批准，本轮external_model_requests=0。仅本地文档/一份自动清理SQLite双fixture/一份已有真实MD段落gold合同；不触发CI，不启用发布或Win11验收。

[执行方案](../../F1/AT02ExecutionPlan.md)明确2请求可容纳单A选择→反馈后修订闭环及同库完整双初态/本地隔离；两主体各闭环最少4，不拆成各一调用冒充反馈链。当前平台cap1024，方案512/2requests/1tool/0repair/5000reservation预算/2000完整字符/响应结束后6秒，保持原守卫。两请求不能保证正确/不截断/形状适配；只有明确批准及新PG最小角色/独立服务/全局硬守卫预检后可真实执行，当前SQLite不冒充该环境。旧单owner成功与别库失败不拼接。

[offline-preflight.py](offline-preflight.py)显式MOCK/live_enabledFalse，不构造InternModel/外部transport、httpx.Request仅序列化不发送、不读真实环境token。12原LIVE归档bytes/SHA全匹配；实际本地认证API/Store/Worker/工具回执/coldStore链及四principal双project/runtime、八双向API拒绝、foreignruntime/owner或runtimeread撤回、B84不变/不引用、Grants不变、模型policy纯函数及owned清理，[最终26checksPASS](offline-results.json)。回放使用旧公共assistant形状，仅换合成资源ref，两体1170/1958字符、reservation4206；本轮MOCK identity NOT_ENFORCED_SYNTHETIC、usage unknown，绝不记成真实用量/实时模型能力。旧LIVE原始身份策略和两个RECEIVED/VERIFIED/PARTIAL42保持。

初helper误用不存在Store.get_run导致AttributeError，在新owned临时fixture退出清理，没有服务/provider调用；改为现有inspect后22PASS，扩交集撤回/ownB资源与资源完整snapshot后26PASS。初错误[first-local-error](first-local-error.json)保留。ruff check/format仅这两份文档内离线辅助脚本，不动产品。

[非CSV建议](../../F2/NonCSVTaskProposal.md)：原授权V5 MD§10.1→带来源检查清单，有真实本地输入、开发方预置固定4段gold草案（待owner/独立验收确认）；[合同](noncsv-contract-results.json)1正/5负PASS，实际模型提取NOT_RUN。该822byte段落真实外发、>=3调用/输入上限/最小artifact授权须另批，不挪用AT02两次合成预算。此oracle证明固定gold草案合同，不能替代未见文档的独立人工语义评价或P-A/P-B真实成功。
