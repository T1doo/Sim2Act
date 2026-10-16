# 普通P-A已收到回包在reservation/归档失败后的证据保全

基线 `16bf15cc8f9b7cf282470b34abe3157c8e4a66e7`；独立分支 `dev/pa-received-evidence-20261016`。本轮修复普通P-A既有真实Worker回包路径的旧F2-T09缺口，不走Trial V2、不放行资格。最终实现冻结 `ff6d703f9dc21f59ec905098e82be80caef0db13`。没有改main/core、资格锚/pin、原owner WIP或旧失败原件。

## 问题与实际复现

旧 `natural_source_archives._write` 把RESPONSE事实归档也连接到reservation。MockTransport已经回包时若slot被删除，归档身份查询无行，抛VERSION_CONFLICT。`natural_spec_runtime`又把RECEIVED/raw/usage与该归档放同事务，结果回滚已收raw、usage及NS_RECEIVED，Attempt倒退STARTED。此前开发期missing_slot原XML的失败不是软件资格导致。

本轮在16bf原字节上仅选原missing_slot与原普通冷新输入正例，实际1FAIL+1PASS，exit1，77.25秒。失败仍STARTED而原测试要求REJECTED_KNOWN；原API→实际Generate Worker/MockTransport→确认/发布/实例→重开Store冷新材料正向通过。它和被严格资格阻断的新Trial路径不同，未替换资格函数。

## 最小修复

`natural_source_archives.receipt_owner`共享原scalar身份/请求wire检查：仅本Run的principal/project/runtime、该Attempt id/run、MOCK模式及原wire hash/字节数；晚到事实不要求当前material权限或lease。REQUEST仍必须有原reservation；RESPONSE仅去掉slot存在的依赖，仍要求原request archive配对header/摘要、不可覆盖和终态不可补档。没有补slot、原账或旧归档。

runtime在原RECEIVED事务先核owned scalar guard，按STARTED+response NULL条件写入raw/实际usage/模型/elapsed与NS_RECEIVED；提交前再核身份和scalar事实一致性。RESPONSE归档移入后续现有try范围的独立事务。其验证/写入DomainError只回滚归档，不能抹掉已持久化raw；后续完整bound/counters/receipt/来源/额度/lease/Goal/最终事务门仍决定是否成功。request archive失败仍是发送前整笔零发送；接收事务本身提交失败仍不能冒称持久化，本修复不承诺不可写存储能保存任何数据。

独审发现拆分后的新交接风险：RECEIVED提交后、归档前所有者/wire/竞争回包可能变化，旧reject分支还会把竞争Attempt改为REJECTED_KNOWN并追加错误事件。3条真实Worker外部红测明确复现全部3FAIL（74.19秒），原件保存。本次最终修复在reject同事务重新核原owned guard，并用原response+usage条件写、要求rowcount=1；失败整笔回滚，不能串写竞争历史。pa_trial.reject的任何副作用仍在同一事务回滚范围，但本轮没有执行Trial绑定Worker。

完整回包且来源/slot等验证失败：保留实际raw/known usage，但业务失败，无实例成果。不完整/无解析raw的prefix/invalid/empty/oversize继续STARTED/unknown；可保留原收到前缀/摘要而不能补造完整回包/usage，原键可读状态仍不重发、不退款、不续期。slot缺失后不重建，slot移给其它Run后保留故障注入后的外来行原字节，不能修回本Run。

## 测试与证据边界

新增5条普通实际Worker损坏/原键测试：missing/moved slot、原请求seal缺失、cancel+missing slot、prefix+missing slot；另3条真实receive提交后owner/wire/竞争回包交接测试。新测试只在明确隔离SQLite注入故障；后3项以包装原Store.tx在真实事务commit之间插入故障，事务本身仍实际SQLite，未替换资格/发送/归档/验证器。MockTransport是显式合成provider回包，语义仍未验。

旧source archives测试的response_write_failure预期有意从“STARTED/raw None、已收证据丢失”改为“REJECTED_KNOWN/raw和NS_RECEIVED保留、归档原事务失败、无成功”；这是修复要求的行为变化，旧源码与原预期已在基线提交永久保留，不把它冒称旧测试原封不动。其它request_write_failure、invalid/prefix/取消/撤权原断言继续执行。

原开发first7PASS是未补交接guard的WIP结果，不作为最终冻结验收。该WIP快照在运行后捕获512项src/tests，不含pyproject；4份改动原件已在证据副本反向精确后续patch恢复并核同已存hash，其余508份逐字节锚定16bf Git，未运行恢复副本。它不是完整before/after冻结证明；最终514项闭包另含pyproject。Ruff初次1个新测试import排序错误，原log保留，修正后变更5文件PASS。mypy未运行。初始collection为87/89，两个已知受限节点明确deselected、未导入或执行；加入3handoff后，冻结主回归范围为99个允许唯一节点，外部单条组合链另有1个独立节点。最终数字只从冻结原XML和实际进程退出记录得出，不把排除项当PASS/SKIP。

最终两组范围：普通natural_spec_apps全部允许节点（包括实际正向与冷新输入、旧missing_slot）、新8项、pa_spec_apps全部共享提交节点、source archives原8个收包失败场景、1个真实严格资格拒绝原子性节点。完整source archive同Trial七槽主测试未跑，不声称它通过。已知两个受限私有SQL节点不重试；guard插件保留。原历史275P/4F不覆盖，本轮只重验并修复其中missing_slot，另外grant及两个受限失败不宣称消除。

## 不扩大验收

资格仍严格VERSION_CONFLICT：原qualification记录86文件、当前88；相对其新增两个trial模块、既有九个文件不同（本轮新增差异natural_source_archives/natural_spec_runtime），其余77核同；原anchor/qualification/pin字节未变。普通P-A路径可运行不等于当前新Trial有资格。

本轮不声明Trial V2或关联Source/Cold真实执行通过。独审还静态提示未来关联任务context marker与natural runtime精确context keys可能不匹配；这是后续真实资格/关联路径需验证的独立风险，本轮未修未验，不拿合成stage测试冒充覆盖。

PG、Windows、原生浏览器、真实模型/费用、生产resolver/sender、完整P-A/P-B业务/人工语义、部署、远端CI均NOT RUN。未配置凭据或扩大权限。

另有同一数据库上的单条普通完整正向组合测试已在同ff6冻结实跑1PASS、118.832秒、进程退出0且未超时：原API规划/确认/发布/实例，Source真实Worker两次Mock回包并保存成果，创建新材料绑定，新Store重开与原键恢复，Cold真实Worker两次Mock回包并保存第二成果，旧Source的instanceData与Attempts完整字典不变。514源码前后与独立driverhash相同，tree clean。规划3次+Source2次+Cold2次为普通Mock发送数量，不是获准Trial七槽；没有Trial、PHASE、资格替换或可信账户放行。

## 最终冻结实测

同一实现SHA `ff6d703f9dc21f59ec905098e82be80caef0db13` 共100个唯一节点PASS，0FAIL/ERROR/SKIP：普通组53P（另2个已知受限节点deselected、NOT RUN），共享提交/归档组46P，单条实际普通Source→Cold组合1P。三个进程实际exit0、无超时，三个导入回执均零受限尝试/加载。普通组1014.893秒，共享组664.056秒，单链118.832秒。514份src/tests/pyproject前后摘要完全一致、HEAD不变、tree clean；外部组合driver自身hash也前后相同。此100P不包含开发期红测，不替代或覆盖原275P/4F，也不表示新Trial/软件资格已通过。

## 可复算原件

[最终结果](../evidence/pa-received-evidence-20261016/FINAL_RESULT.json)、[普通运行原XML](../evidence/pa-received-evidence-20261016/ordinary-model-results.xml)、[共享提交/归档原XML](../evidence/pa-received-evidence-20261016/shared-archive-results.xml)、[单条普通Source→Cold原XML](../evidence/pa-received-evidence-20261016/ordinary-source-cold-results.xml)、[实际成果回执](../evidence/pa-received-evidence-20261016/ACTUAL_SOURCE_COLD.json)、[独审](../evidence/pa-received-evidence-20261016/FINAL_REVIEW.md)。

[完整原始证据](../evidence/pa-received-evidence-20261016/complete-originals.tar.xz)含所有红测/失败/开发WIP原件、完整SQLite/case包、命令/退出/stdout/stderr、source闭包及静审历史；逐一核验292个原文件，归档SHA256 `d3e335802d7509d3b386c01a490c8afef4b7c13d2ea65044cbc0ab286156e086`，详见[归档回执](../evidence/pa-received-evidence-20261016/BUNDLE_RECEIPT.json)。
