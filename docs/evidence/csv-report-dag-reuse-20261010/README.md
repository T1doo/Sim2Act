# 三步报告 DAG 内部复用与类型恢复修复

最终源码冻结：`50b10417a99a070f6bcd614471cc00ec102b7836`，基于已推送候选 `5588a94faeb90abb2052a8ae5327810b8d27c287`，起始开发 HEAD 为 `f13ff8d7661490a7e42a1f7ce3e9179bda54da4b`。正常提交、普通开发分支推送；main 不变。产品实现见 [F2 说明](../../F2/CsvReportDagInternalReuse20261010.md)。根 COPY_WHITELIST 覆盖实际公开文件字节；各子目录白名单保留原来源、范围及 SHA256，不能把不同 source 的结果合并为一次通过。最后封存提交仅证据/文档，本证据目录内的 .gitattributes 保留字节（-text/-whitespace），防止真实 CRLF/日志被 Git 文本过滤改写；root .gitattributes 与冻结源码相同，不触发其原生 CI 路径，不更改冻结365文件、产品或执行配置。

## 范围与来源

严格无条件 read→aggregate→report 的已完成真实来源，可保存为内部 immutable 版本并由冷页面确认新列、完整实际执行三步。五字段 typed result、三个 VERIFIED 回执和唯一报告 sink 分别保持原合同；现有授权、预算、Run/version/fence、幂等和最终事务均继续验证。条件 DAG、额外边、额外节点、发布、语义验收不在范围。实际旧 f13 数据升级触发既有图基线 VERSION_CONFLICT，原始历史行不变，需要新成功来源；不承诺旧版本跨源码无缝复用。

最终 365 源码/配置/测试文件逐字节与实际 Git commit 匹配；产品 69 文件仅 adapter、csv-dag.js、index.html 三个变化，其余 66 与 `47388f573746daa27f8d5790ca358eef91378ad5` 相同。相对初始候选，最终只有 adapter 两行严格 JSON 指纹比较和四个类型篡改回归新增，其他产品字节不变。见 [字节桥](type-fix-author/source-byte-bridge.json)。冻结清单继承的 changed/product_changed 说明列表实际对应原 f13/473 基线，不能作为其 base5588 字段的差异清单；实际 base5588 两路径为 delta_from_5588。原冻结文件保留，[元数据补记](type-fix-author/source-manifest-addendum.json)列出实际 Git 差异及各基线，不改已签源字节。

## 旧候选的有限证据及后续 BLOCK

`author/` 保留 source5588 有界作者范围：SQLite 100 PASS / 3 SKIP / 0 FAIL（402.27 秒）；PostgreSQL 103 PASS / 0 SKIP / 0 FAIL（506.54 秒），另有原 resources-history 单例 PASS（3.76 秒）。三个 SQLite 跳过均为真实 PG 角色检查。实际 HTTP/jsdom、原 67 与 f13 源码升级、回执/权限/原子性均在各 XML 和 runner 中逐 node 记录。

`independent/` 为 source5588 原 61 项白名单：独立不同 CSV/报告 step 的 12 API 场景、49 检查，以及 5 HTTP/jsdom 场景、6 页面、141 检查。原 LIMITED_PASS 限定在这些范围，未覆盖 typed count 浮点共同篡改，未独立跑 PG/native/整库升级。`design-independent/` 保留真实产品缺口与既有容量边界的独立静态审查。

`native-5588/` 为 source5588 实际 run38034912187/job114163227401：Windows Server2025 的固定 remaining11 全 PASS，完整收集2266、2255未执行；JUnit60.934秒，Engineering步骤70秒，Edge104秒，总作业241秒。9个浏览器文件由原日志完整块解码、字节/SHA校验。原 4,810,218字节日志 SHA256 `aa552176ef2c81cbe5e4b0b2ec2520634d1e54b2c214b40fdd71f6cd468e251d` 私有保全。它没有运行新增16项报告 feature cases；图像不是 owner/语义验收。

`type-block-5588/` 明确覆盖随后真实发现的 BLOCK：row-only 与 row+AppRun 两种 `count=2.0` 共同改签，6个公开 GET 全返回200，冻结 schema 拒绝浮点值，真实 Operation 未改，GET全库零写。完整响应、数据库 JSON/schema、前后365文件、两例 runner 与原 BLOCK 白名单保留。此前有限通过不撤改原件，也不用于否认此缺陷。

## 最终修复的限定复核

`type-fix-author/` 的 runner/XML 记录最终 source50b 的有限双数据库回归：SQLite12 PASS（108.655秒）、PostgreSQL12 PASS（190.927秒），均0失败/0错误/0跳过。范围为两步/报告版本 × row-only/joint 四种共同改签类型攻击，正常冷输入两列、报告 typed 五字段和三个回执、最终事务失败回滚、实际 f13 旧数据库升级保护，以及两步/三步四个真实 HTTP/jsdom 页面案例。ruff/mypy通过。`type-fix-independent/` 为6场景38检查有限通过：四种攻击的12个公开GET全409，Operation未改、全库零写；另有两种正常新列/冷Store/sink/schema正例。初次独立脚本缺validate_value导入的NameError原日志保留，改正后一次完整6场景通过；未独立跑PG/native/额外UI。最终精确结果见各终态 JSON/XML，不把旧候选103套重写成最终source全量通过。

`native-final/` 为最终冻结实际 run38035830928/job114165927573，attempt1 SUCCESS。固定 remaining11：11 PASS、0 FAIL/ERROR/SKIP、33个阶段报告；完整2270收集、2259未执行，JUnit91.405秒。Setup42秒、smoke15秒、Engineering103秒、Edge127秒、总作业312秒，报告/清理均SUCCESS。9浏览器文件完整解码并按实际块数/字节/SHA校验，源365前后不变。原4,811,976字节日志 SHA256 `9f4951d31759eb99f710b80c6370e4f969d4b15f7c0cb66f06421c4789355cc7` 私有保全。完整收集只是覆盖清单；新增20项报告 feature/类型测试不在这11项中，已完成的是有限本地双DB/独立场景。Win11 NOT_RUN，移动设备只有viewport、图像没有owner/语义验收。Windows900/Edge240/Node150 整体验收仍为 NOT_ACCEPTED。

`publication-independent/` 保留先完成七组289项原件、来源字节、元数据补记及范围归属的12项审计白名单（当时native尚未终态，未代签）。`terminal-publication-independent/` 独立自编原日志解析，核完整2270/114块、固定11节点/59事件/33通过阶段、9浏览器文件重组、终态时间及365源字节，7项白名单单独封存。首轮审计捕获旧287计数快照更新，以及首轮终态脚本错误要求 Report 发出的 fullcollection 在 selection 之前的原脚本/日志均保留；纠正后有限审计闭合。两者均只读封存审核，没有再次运行PG、CI或产品测试，不增加验收范围。

## 失败、跳过与未执行

所有初始作者夹具错误保留：缺 basetemp 导致2 setup ERROR；CSV oracle把实际2行误写3；错误直接 lifecycle 返回形状；误期待旧 f13 升级无缝200，实际既有保护409；controller product_files形状错误导致未启动 pytest。纠正后相应原有限范围通过。最终类型新测试首轮错误使用不存在的 ledger id 主键导致4 FAIL，未完成篡改；原 XML 在 `type-fix-author/probe.xml`，修正实际复合主键后4 PASS，随后冻结实际有限12例验证。

初始 source5588 PG作者批次在500秒控制器超时中断，仅94个进度点、无终态JUnit，不能计为通过；日志、控制器终态、唯一自有schema dump及清理记录保留。源码未变，结束其他作者/独立页面工作后单独700秒有限同103项完成。测试预算没有修改原生900/Edge240/Node150，未定位或关闭原历史超时。两个临时 PG 均是自有 test-only、network none、Unix socket、零发布端口；终态0 schema / 0 test-role / 0 public-table，保存服务器日志后移除自有容器及卷，详见各 cleanup。

没有全量原生重跑、真实模型调用、平台伪装、共享可变fixture或未授权分片；没有 main、强推、部署、凭据、安全网络修改。完整当前测试集合、未执行尾部及条件/反馈/其他 HTTP200损坏响应能力不因本有限证据自动通过。

## 900秒容量与仍开放事项

`author/capacity-diagnosis.json` 只使用既有实际测量和 fixture/SQL 资料。原9002全量2234收集、592开始、591完成（589P/2S/0F），第900秒仍1例active、1642未开始，Edge跳过；591个已完成节点到后续启动间隔共801.110秒，不能拆成纯SQL/setup/call。原完整PG1586/1591时代范围与当前源码/平台/集合不同，旧实测总1089.253秒、setup221.214/call847.252/teardown16.810秒，1346个function env共213.864秒，不能外推当前完整集合的准确最小预算。

可证明下界只针对原同覆盖、同串行实测流程：大于900秒；最终完整原生最小耗时及未测尾部为 UNKNOWN。最小后续决策是是否批准一个保持独立schema/权限/历史/冷启动的有界分片实验；需先证明完整 node union，并把所有 Setup、Engineering、Edge、Cleanup 的整体端到端墙钟计入同900秒，不能每job900秒或重复串行Setup后声称达标。尚未启动分片。共享可变session fixture会改变原验证含义，现有材料没有证明等价收益。

原 Report GET idle6 与 PG resources-history Future10 均 OPEN；这次相关有限 PASS 没有重现原根因，不是根因修复。HTTP200 其他损坏响应、反馈/item-map 限制保留；Windows900/Edge240/Node150 未验收。PROJECT PENDING/BLOCKED_PARTIAL、整体 NOT_ACCEPTED、semantic UNKNOWN、owner PENDING、正式发布关闭。LIVE=0，真实模型调用0。
