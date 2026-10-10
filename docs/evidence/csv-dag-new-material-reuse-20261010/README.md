# 已核闭合 CSV 流程的新材料复用（限定）

最终源码 `709e0978c15236ed86bafc095d4cdf1301ad756c`，开发基线 `977f88e2fd41630bd61298735c7ec4bad773de6a`，旧源码 `50b10417a99a070f6bcd614471cc00ec102b7836`。只普通提交/推送开发分支及新候选 `dev/csv-new-material-reuse-20261010`，main保持 `6f688e4dd80b5c81d41aecde90e360d3629f9c21`。产品合同及旧文件依赖见 [F2说明](../../F2/CsvDagNewMaterialReuse20261010.md)。

## 范围与字节

从已有成功、已核版本提取严格无条件 read→sum[→report]，显式绑定同project另一份已有注册、当前授权、当前图的不同CSV及数值列；不同rid与真实hash，按原executor显式执行，成功后另外确认保存独立Release/Instance。新材料计划本身零Grant/Principal/执行/typed写入，既有CSV注册仍是原create-and-authorize合同。来源仍要求旧CSV真实字节/当前授权，不满足完整AT10“无固定旧文件依赖”；材料转移限一跳。旧历史不覆盖，来源冻结cap不扩张，LIVE/真实模型0。

`author/source-freeze-complete-readback.json` 给出373非文档/70src逐文件bytes、SHA256、Git blob。838初始产品经bfb/c9两次test-only修夹具；392/e76/709仅JS变化，其余69src及全部Python与838相同。旧365与本轮373清单的定义不同，不靠文件数判断实现变化。373整个最终源码清单与前后Git/worktree相同；证据提交只docs，冻结源码及根.gitattributes不变。本目录nested.gitattributes保留原CRLF/二进制字节。COPY_WHITELIST逐文件保留原来源；不改旧签署文件。

## 作者实际结果

最终709 SQLite真实HTTP/jsdom页面12PASS/0FAIL/0SKIP（248.272s）：8个新材料场景及4个原两/三步实例丢POST/read兼容场景。每页实载index.html与全部JS校验实际源SHA，原worker真实写入新CSV数值及冷列typed结果；详情见author/final-test-result.json和sqlite12-final日志/JUnit/15个最终SQLite及PG结果文件（总251项页面检查，分别归属各跑次）。

原SQLite30是原运行15项PASS观察加纠正后剩余15项PASS，原Limits夹具写max_tool_calls而非max_tools的FAIL保留，不能说单次clean30。22项后端覆盖目标新CSV/列、同key换目标/列、撤权、版本、foreignowner、冻结预算、origin双seal缺失/重签、reserved-prefix联合删除origin+marker及真实旧50b升级。所有Python精确桥接最终709；这些后端不宣称在最终JS重新执行。

PG c9实际单次30项29PASS/1FAIL/0SKIP（545.411s），22后端及7页面通过。最后invalid-budget三步冷实例接受读回DOM idle10；同源同预算重试仍FAIL（67.79s）。392删除重复perRun GET后仍在Instance→Release→plan链idle10（45.66s）；e76接受读回通过、实际worker已写新列typed17，但最后manual重复链idle10（82.47s）。全部原FAILURE/log/JUnit、14项前置检查及请求留存，不能称夹具错，也不将中止当完整通过。

709修正仅当前context、material-prefix范围：fresh Instance GET后匹配sealed immutable release id/fullfp，缓存完整核过的计划key/fullfp最多50；每次重新ReleaseSeal/PlanSeal/jobSeal/input/ID/typed校验、全部await/current与expected接受链接通过后才cache/paint。缺cache正常GET；旧nonmaterial原路径保持。原DOM10/Node90不提高。最终PG原失败invalid-budget三步1PASS42.18s，再两/三步丢POST+冷新列实际结果2PASS86.67s，0SKIP；新CSV求和40/count3、新列units17/count3，旧15/count2不可替代。专项3PASS不撤改四次失败，也不签完整PG性能。test-only PG17.9 networknone/Unixsocket/0ports，前后schema/role/public0|0|0，owned容器及anonymous卷已清理，服务器启动/关闭日志保留。

原50b升级用真实旧archive建立历史；新源读/重放409，raw JSON历史字节未迁移/覆盖，重新derive/exact确认新Run通过。SQLite及PG升级证明分别在sqlite15-rest和pg30-corrected子目录；不声称旧版本无缝跨源码。

## 独立复核及故障

`independent/final/FINAL_REVIEW.md` 原c9/838限定18场景161检查（14 SQLite/API64，4真实HTTP/jsdom97），独立3行Decimal net7.000/units9/count3，未采用作者40/17 oracle。18个实际拒绝API400/403/409全DB零额外写；覆盖共同删除/重签origin、预算、source/target授权/版本、foreignowner、五种自签坏200、UNKNOWN重试403原body/key、合法迟到source-target-sourceABA与same-target打开ABA。104项原白名单（含26个隔离合成SQLite DB）全部逐字节公开；不是PG/native复核。

`independent/final-readback-fix/FINAL_REVIEW.md` 精确709最终新delta LIMITED_PASS：5真实HTTP/jsdom场景、9document、213检查；两/三步冷新列真实结果、坏accepted ID、坏Instance input、接受后Instance503；后两者已知接受回执GET-only恢复。失败不得cache新plan/paint，fresh Instance证明仍必要，cache命中避免重复GET，冷新document零POST；373/70前后匹配及69后端字节桥接。原18未全重跑，不能合并为709单次23场景或PG签署。合法形状但虚假的accepted runID仍UNKNOWN且不paint，独立复核没有签收该ID自动恢复；整体HTTP200损坏响应提示及恢复限制保留。

所有作者/复核者夹具错误与控制器中止保留：原登记顺序使旧source权限基线过期、冻结Settings/goal字段/预算字段错误、source manifest list误当dict。392独立运行中root改变JS，资产守卫正确拒绝，该次无最终签署；e76独立1PASS24检查/4 coldversion oracle硬编码错误封存，最终修私有oracle仅新delta5完成。其原白名单17及38保持，不隐藏失败、不算产品通过。初始实现read_origin key差异与prefix/cache/openABA修复均在838前完成。独立范围未覆盖完整跨project攻击、全部worker fence/原子失败矩阵、旧文件独立性、PG/native及总体性能。

## 原生固定诊断

精确709实际 [run38040485404](https://github.com/T1doo/Sim2Act/actions/runs/38040485404) / job114179570689 SUCCESS。remaining11工程11PASS/0FAIL/0SKIP，33setup/call/teardown reports全PASS，JUnit 113.061s，Engineering步骤127s，Edge步骤150s，job370s；完整收集2300，2289未执行。原解码UTF8/CRLF日志4,912,214bytes，SHA256 `1a493cef86b0af03781b1f2968dd72ee78fe49060ed5caf219dd36123deb8169`，原transport JSON一起保留。9个browser文件逐chunk base64完整重组，bytes/SHA完全匹配，实际WindowsServer2025/Valid signature/ChromiumSandbox/model0与各JSON全PASS核验；原native-result/summary/events/collection及9个文件在author/native-*。根日志、PNG等由nested.gitattributes保留Git blob实际字节，不能改写日志newlines后称同一SHA。

固定remaining11不会执行本次新增22后端+8页面；完整inventory只收集，其余未执行。Windows Server2025/实际签名Edge日志和9个解码文件只签该实际诊断范围；Win11未运行，Windows900/Edge240/Node150整体NOT_ACCEPTED，语义/owner未验收。无全量重跑、预算上调或CI重试。

PROJECT **PENDING/BLOCKED_PARTIAL**、overall **NOT_ACCEPTED**、semantic UNKNOWN、owner PENDING、正式发布关闭、LIVE=0、真实模型0。历史Report GET idle6与PG resources-history Future10继续OPEN；新材料实例读回整体性能观察仍OPEN，只有上述709小集通过。无改main、强推、部署、实际凭据/安全网络改动或真实模型调用。最终推送SHA/无未推送差异由交付回报和私有postpush receipt给出。
