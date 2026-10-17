# 普通人工拒绝 → 显式新修正Run：有限工程验收

源码及测试冻结 `d731199a1fd6272e1a79e1c761a1461500fd5227`，基于已接受 `4747ff24ca7fee2dd4bed0d503f15ea13a6a0945`；普通分支 `dev/ordinary-goal-rejection-correction-20261017`。其后仅使用说明及证据归档，交付提交以Git/实际远端核对为准。

[使用说明](../../ordinary-goal-correction.md)：当前有效的REJECTED逐项声明 → 显式只读预览原Goal、全部标准、精确材料、原结果及拒绝理由 → 另行勾选确认 → 一个新Run → 显式打开、查看成果并另行人工声明。反馈由服务端从原不可变DECIDE提取，进入原Worker用户JSON，不能删除标准、改Goal或授权。旧Goal/Run/声明/封印及旧文件原字节保持。新Run仍技术PARTIAL、自动NOT_RUN、语义UNKNOWN，人工从自身PENDING开始，不宣称语义改善或正式发布。

每父最多一个child、只接一层；新增metadata表ordinary_correction_links以parent主键/child唯一，与snapshot/ACCEPTED/context独立引用共同约束。原key原body取原Run，改body冲突；不同key不建兄弟，失败不释放位置。没有新executor/Principal/角色/Grant类型。原MD政策成功保存会新增**一个Resource及两条resource.read Grant**，不是零新增Grant或零副作用；v1保留只读。当前双主体材料/成果权限、原Goal头、精确拒绝、结果回读和预算逐次重验，Mock route及Worker双门，真实模型额度0。

## 最终实际执行

| 批次 | API | 页面及必要回归 | unique | 输入 | 实际并行墙钟秒 |
| --- | --- | --- | ---: | --- | ---: |
| 作者d731 | 23PASS，JUnit175.164秒 | 14PASS，JUnit219.807秒 | 37 | 590个src/tests/schema/pyproject，前后相等、工作区干净 | 222.932 |
| 独立d731 Git archive | 23PASS，JUnit177.144秒 | 14PASS，JUnit210.032秒 | 同37，新增unique0 | 591（多一个明确导出的既有goldfixture），全体Gitblob/SHA与前后相等 | 212.428 |

两子批各RC0、0失败/错误/跳过，union37且overlap0。不把JUnit之和当墙钟，不把作者/独审两轮计74unique。[作者命令/RC](raw/author-meta/final-execution.json)、[精确收集节点](raw/author-meta/final-collected.json)、[API原XML](raw/author-meta/final-author-api/junit.xml)、[页/回归原XML](raw/author-meta/final-author-pages/junit.xml)；[独审结论](raw/independent-final/review.json)、[独立union](raw/independent-final/union.json)、[独立API XML](raw/independent-final/api/junit.xml)、[独立页XML](raw/independent-final/pages-related/junit.xml)。没有重复旧PA/PB长矩阵。

37 = 23新API/真实原网关 + 6新整页 + 8必要回归。新API覆盖显式预览无写入、同原Goal/材料/标准的新Run、反馈确实进入用户消息、旧父数据保持、同key/异body冲突、不同key并发只建一个child；材料/旧成果/项目save撤权、Goal/结果/封印/拒绝变化拒绝；受理后权限和反馈/恢复消息损坏、LIVE Worker零模型派发；模型读后save前撤权；最终提交前撤回父拒绝时拒绝整体结果且已保存的child文件/两条读取Grant保留。父正常Grant集合因child保存改变不改写原拒绝，受理后只去掉Grant集合比较项，仍独立检查全部必要当前权限和稳定父证据，不追认父动态STALE声明。

原key两个入口的读取顺序曾被独审BLOCK：现在先查ID及精确父绑定，父/子来源ID和独立local_effects保存ID先鉴权，再读取整行。对父/子成果分别撤权并损坏receipt.refs后，直接Run读取、原key GET、同body POST各403；原SQL证明拒绝前无完整Run/contract/context正文SELECT。原件：[SQLtrace 1](raw/author-final-api/test_parent_effect_authority_p0/authority-before-body.json)、[SQLtrace 2](raw/author-final-api/test_parent_effect_authority_p1/authority-before-body.json)。

6新页为真实服务整页HTML/CSS/JS、authenticated ASGI和原Worker/工具：MD、只读、已受理丢响应GET恢复、合成发送前失败后原body/key显式重试、同Run重绘/工作区/任务/项目/账号导航与迟到回调、撤权恢复清理。合计**225可见断言、410次记录的页面API尝试=409次实际回复+1次合成NOT_SENT、138资产响应**。不把未发送一次计服务器请求；统计不含夹具、Worker与撤权控制RPC。

新页4份实际下载Blob原件均156字节，SHA256 `61e476dd4066650cc64f7a78b0b9a5f66861f9b827d36a7e17bebb739422db46`；保存filename/Run/URL/hash/size及URL释放、anchor清理，未从DB重建。独立同样捕获4份，属同4路径复跑。[逐页统计与原件路径](raw/author-meta/final-scope-summary.json)。6页11个Worker对象均在当前Store上，不是独立进程重启；14次child合成响应。作者CorrectionModel计数30包含上述14，不含父任务与其他旧Mock/MockTransport，不能称整体模型总量或另加14。真实模型0，合成人工点击不代真人/语义签收。

8回归为旧保存Goal未公告写拒绝、旧v1声明接受/拒绝2例、旧owner撤权整页、旧MD实际保存API、旧MD导航页、原确定性CSV报告API、普通成果工作区返回页。精确节点见收集清单；不并入未选历史矩阵，不声称旧owner原body/key重试按钮或恢复授权完整矩阵由本片补签。新修正的显式重试范围以以上6页为限。

[单独SQLite增量迁移探针](raw/author-meta/migration-proof.json)在d731仅移除夹具中已知空新表后initialize，旧50表所有行、父Run/Goal/声明原字节不变，新请求受理及同key幂等通过。它是作者额外探针，不计37；独立未执行此探针。未做PG迁移/运行角色授权配置，API/worker不自动DDL。

## 原件、失败与限制

本目录**633份已落盘原始输出、637个文件、636条SHA256SUMS**：命令、完整日志/XML、输入指纹、SQLite、实际页面请求/资产hash、SQLtrace及Blob。独立最终122项manifest+manifest/sums=124输出；7378独立109+2=111输出，两份封存清单逐条size/hash自核：[核对](raw/author-meta/independent-seals-verified.json)。源snapshot/node_modules是可重建输入，不冒称运行输出。

[artifact-map.json](artifact-map.json)列原路径/长度/SHA/编码；DB和>1MB输出mtime0 gzip，解压等于原字节；其他原件保留CRLF/尾空格/换行。SHA256SUMS涵盖全部其余归档文件，归档及Git blob另逐一核对。

保留首红HTTP404、测试辅助列名错误、开发不存在Store.revoke误用、工作区恢复控件真实失败及修复、受理前失败合成、首轮正式收集错写[revoked]导致RC4/零执行等原记录。7378作者36PASS与独立36PASS同时保留其静态**BLOCK**，不是准入：两个原key入口先读正文的问题仅由d731修复及37项关闭。相关原件在author-meta/superseded-7378和independent-superseded-7378；没有用绿色覆盖静态阻断。归档辅助脚本对封存verdict误期PASS（实际FINITE_REVIEW_PASS）的失败说明及原脚本也保留，未改原证。首红来源见[证明](raw/author-meta/red-provenance.json)。

[开工真实checkout/容量/default Git网络/21保护引用](raw/author-meta/preflight.json)。未使用旧满盘实例、旧bundle或旧共享文件；已知旧独审报告未落盘的证据缺口没有补回或重建。

当前未执行：真实模型、真人签收、真实语义/业务场景、PG/真实应用角色、原生浏览器、Windows、独立worker进程重启、远端CI、部署及未选历史矩阵。原文字样fresh/cold Worker仅按实际对象/Store理解，不代独立进程恢复。此为原F2-T01/T05/T06的有限产品闭环，不关闭完整P-A/P-B或正式发布门。
