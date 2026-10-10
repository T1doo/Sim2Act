# 剩余11项原生实跑与历史超时诊断（2026-10-10）

精确源码 `180a4710405b9c06d1e7cc7213b3ffd073d05567`，363冻结文件；69产品文件逐字节等于 `47388f573746daa27f8d5790ca358eef91378ad5`。本轮只改固定目标入口及其证据检查，不修改产品、HTTP、数据库结构、真实模型设置或测试门槛。正常推送候选 `dev/native-remaining11-20261010` 和 `dev/f1-foundation`，main仍 `6f688e4dd80b5c81d41aecde90e360d3629f9c21`。

明确提交标记 `[native-remaining11]` 请求 `DIAGNOSTIC_ONLY_REMAINING11`；无标记的原工程入口仍执行全套。真正Windows/GitHub guard、固定JSON及canonical digest、缺节点/重复节点拒绝、完整收集清单/哈希/显式deselected计数均保留。所选11个原测试、夹具和断言未改，串行执行，无xdist或新分片。Setup、MOCK原生PG/应用角色、job-owned jsdom探针、完整Ruff/mypy、原Edge/always Report/Cleanup保持。总作业900秒、Edge240秒、Node150秒未改。限定11通过不构成全套或Windows11/R0验收。

## 独立复核与保全的失败

初版 `d49aab3e8023b3bf47a7f66577e557d2874c24ae` 独审BLOCK：四种缺失/错误选择元数据仍误通过。第一次闭合 `5385ac9293737cca8ed5dfeec990b760b240bf63` 独审BLOCK：原四种拒绝成功，另六种外来节点/额外事件/错误顺序仍误通过。两个版本均未单独推送或执行native；其提交作为最终180a祖先一起正常推送。各自冻结、实际CLI日志、正式BLOCK及55/64文件白名单保留。

最终180a严格验证实际事件顺序、固定清单、同一PID、全量/所选集合及哈希、start/finish集合、33个setup/call/teardown通过报告、唯一exit0完整session。独审17个实际Report CLI案例：1个真实Recorder完整生命周期接受、16个负例拒绝；另2个旧源码敏感性、3个实际Recorder接线检查通过。363前后精确、361未改字节桥及69产品字节桥通过，仅LIMITED_PASS；独审不声称执行native11或PG。作者最终20项诊断回归PASS、完整Ruff PASS；中间19PASS/1FAIL是外来start的未启动数测试预期错误，已修正并保留日志。早期collect-only记录不是测试通过。

## 实际原生结果

[唯一run 38031437108](https://github.com/T1doo/Sim2Act/actions/runs/38031437108)，job114153034590、attempt1、head180a，实际终态SUCCESS。Setup/native API-worker-PowerShell smoke、owned jsdom探针、Ruff、mypy55源码文件、固定11工程目标、Edge、Report和Cleanup均成功。实际完整收集2250项，比原2234多16项诊断回归；选择固定11，另外2239明确deselected/未执行，不计pytest skip也不算通过。11PASS/0FAIL/0SKIP，全部33个阶段报告通过，11start/11finish、唯一exit0，strict selection_verified/required_targets_complete/suite_complete均true。JUnit113.781秒，工程步骤129秒；job359秒，原Edge步骤141秒，保留900/240/150秒预算。

实际Edge153.0.4234.48、Microsoft签名Valid、Nodev22.23.3、windows-2025，未安装替代浏览器。原浏览器证据9个文件的chunk顺序/字节数/SHA全部验证。嵌套checks按原scope分别为legacy69、taskHistory39、agent33、registeredGeneration29、integration16、protocol26、boundRuns19、conditional22，全部原结果PASS；存在父子检查摘要，不能把这些数相加当作互不重叠断言。sandbox过程证据、禁止开关、应用角色/fixture转接等原检查保持；真实模型0。作者只看本次6张末态截图，不替代全部历史milestone或用户验收；原JSON的visualReview NOT_REVIEWED原样保留。

原26节点中之前15PASS来自9002旧run，本次剩余11PASS来自180a新run，不声称26同一run或全套通过。2250完整原生nodeID清单、选择范围、所有阶段报告和浏览器文件已公开限定导出。4,797,111字节的decoded job-log UTF8/CRLF私有原件与JSON transport均保全，SHA256 `5d4dc70dbeebccd4e704f3fe65c366f99221691b9878fad6fa6449a0cf37ecd5`；公开excerpt为明确的LF行摘录，不冒充原件哈希。

终态独立复核仅LIMITED_PASS：重新从实际transport/log核2250/11/2239、33阶段、59可见事件、9个浏览器文件及359/129/141/JUnit113.781秒；363源码/69产品字节桥通过。267公开快照及六白名单260项+6名单+README逐字节匹配，历史2个重命名映射核验通过。独审未运行测试、PG或CI，只被动核验作者PG记录；三个自编审计器假设错误的原脚本/日志保留。最终出版只追加该独审的21项及白名单并重算根manifest；原267文件保持，不把审计器错误当成产品失败。

Git出版校验发现原d49 CRLF负例JSON被自动归一化，初次及普通git add后字节审核失败并保全。仅在本证据目录新增精确单文件 `-text` 属性，并对此负例刷新index，保持原13个CRLF及原白名单哈希；根/产品/CI属性未改。修复后的293项staged文档快照全部Git blob/worktree精确匹配，该阶段记录及失败原记录另按2项白名单公开。追加这些出版记录后，最终证据根manifest为293项（不含自身）；独审267仅指追加前原快照，不扩大为未经核验的全部文件。

最终296个staged文档全部逐字节核验。Git whitespace检查唯一提示是上述故意保留的13个CRLF行尾；该负例无真实尾随空格/tab，其余路径检查通过，原日志私下保全。产品/CI检查未放宽，原负例未改写为LF。

## 两个历史超时

对180a/473相同产品，在新建无网络/无发布端口、Unix socket的自有临时PostgreSQL17.9上，原same-checks实际HTTP/DOM页面与原resources-history锁顺序节点各执行一次：2PASS/0SKIP、pytest22.53秒。原idle6、Future10、SQL observer及statement timeout均未改；不是负载/稳定性验收。临时schema/role/public测试前后0|0|0，容器及自有匿名卷清理核验通过。完整临时服务器日志私下保全。

非空presentation history两次4010条应用SQL、920个FOR UPDATE、10次Report.load、1次完整scope；墙钟1.9447/1.9040秒，线程CPU1.6999/1.7038秒，SQL驱动0.5690/0.5182秒。resources-history1958条应用SQL、455个FOR UPDATE、墙钟1.6346秒、线程CPU1.3116秒、SQL驱动0.7500秒。嵌套函数时间有重叠，不能相加；CPU/SQL驱动也不是互斥分量。原observer额外driver SQL未计入应用SQL计数，但真实执行，不能用该节点比较生产查询性能。

807原Report失败仅记录最后GET未完成，没有原SQL/CPU/锁/主机时间线；42b原Future10失败记录锁跨度17.59秒而无HTTP结果。此次未复现两者，不能把正常重复完整授权/来源校验的成本认定为原根因。跨definition、DB读取或请求复用校验可能改变当前授权/版本语义，未做无证据缓存修改。**Report GET idle6和PG resources-history Future10继续OPEN**；以后出现真实慢读时需同时记录请求/事务/锁等待/CPU及主机并发，不能靠加长门槛或反复重跑关闭问题。

## 端到端900秒容量边界

按最新授权，900秒是保守端到端总预算。本轮不建立多个各900秒的作业，不降低全覆盖或隐藏skip。原9002单次完整收集2234项，工程pytest815.798秒只完成591项（589PASS、2SKIP、0FAIL），另1活动/1642未启动；准备阶段已耗其余预算，Edge未执行。该次实测900秒不足，所需预算下界严格超过900秒，但缺失1643项没有完整实测，无法给出能完成全套的最小预算。此次限定11的JUnit113.781秒及Edge141秒，是不同run的实际成本，不能填补整套尾部，不能与旧部分耗时相加或线性外推成全套保证。不进行无目的全量重跑；全套容量仍BLOCKED，尚须真实等价降本或另行明确调整合同才可能验收。

公开证据、精确白名单及审查边界见[证据目录](../evidence/native-remaining11-20261010/README.md)。HTTP200其他损坏响应/反馈入口/逐item history map限制保留；Windows900/Edge240/Node150 NOT_ACCEPTED。PROJECT `PENDING/BLOCKED_PARTIAL`，semantic `UNKNOWN`、owner `PENDING`、整体 `NOT_ACCEPTED`，`LIVE=0`、真实模型调用0。没有修改main、强推、部署、凭据或安全网络配置。
