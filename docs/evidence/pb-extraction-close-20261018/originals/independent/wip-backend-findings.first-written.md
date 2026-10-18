# 新关闭模块 WIP 后端独审发现

只读审查，未执行产品/HTTP/Worker/模型，未改仓库。尚未冻结，无动态复现。精确读取字节快照及hash见wip-backend-source-readback.json；若root已同期修源，本文件只指所存WIP，不冒充最终。

## P1：共享marker整行在目标授权/家族分类前读取

pb_extraction_terminals.py:95–96以select(task_extractions)读取完整snapshot，line129才检查主体，line137才逐app的原target scope_gate。此共享表其它家族snapshot含proof/target/request（ordinary_csv_extraction.py:231），不能预设task_id==已授权sourceRun就意味着该snapshot是安全PB metadata。wrongkind/foreign/partial row会先读正文才拒。改成ID/header+kind等scalar discovery，exactkey检测不用正文；scope_gate成功后再取对应marker完整snapshot做原一致性比较。其它旧完整EXTRACT wire目前位于137授权后，这是已采纳正确顺序。

## P1/P2：terminal只靠可损坏PK定位，独立原scope残留不能fence

fenced():54–55只查app_id==rid/request_key==key。若只剩一半terminal且其PK app_id或key被污染，snapshot.request.identity和response仍保存原rid/key，新_extract可能找不到任何terminal而接受原已关闭key。用KIND两种及PK、request.identity、response（含identity）的scope标量OR识别疑似terminal，任何残留都拒POST；read发现错位/额外/缺半应VERSION_CONFLICT，不可None或可forgetclosed。无需恢复受损terminal。

## P2：同related app的额外PB接受journal被正常marker四pair掩盖

_absent:107–151将links仅折叠为aid，循环只重核该aid唯一marker对应的4pair，没有检查link记录集合是否恰为这些pair。正常aid/keyY旁存在额外EXTRACT keyX或单seal，sourceRun仍rid，关闭keyZ时正常Y仍通过而X被忽略。每related aid应scalar枚举全部4类PB journal header，严格等于META(scope)两份+EXTRACT(markerKey)两份；额外/缺半/主体不符UNKNOWN。exactkey残留识别还应联合journal PKkey、snapshot.request.review.request_key、response.request_key独立标量，不能只PKkey。

## 已确认正确及可用性限制

_extract共享写入口已在同project事务锁/source_gate之后且review/oldkey/所有写之前检查fence；pa_trial_dispatch直接调用同函数，未另开绕行。closedreceipt明确分开原fullExtractInput hash、CloseInput hash和receipt hash；CLOSE需原17metadata及显式consent，未使用token。samekey已接受marker直接冲突，不写terminal。Strict pair/receipt重新计算用于成功closed读取。source重核在metadata写后，失败事务回滚。双half任一存在（仍canonical PK时）会fence；closed+accepted同时存在会拒而非覆盖。没有新executor、Grant或模型路径。

related accepted app仍需原target授权门；sibling撤权/stale或scan预算64apps/256journals导致close保守UNKNOWN，是明确可用性限制，不应绕门。新未受理intent自身targetGoal未被读取/重算，过期目标不会独自阻断无sibling的关闭。全source proof exact-match另使来源变化的关闭保守拒绝。实际并发/latePOST/撤权barrier/UI资格均尚未执行，不写PASS。
