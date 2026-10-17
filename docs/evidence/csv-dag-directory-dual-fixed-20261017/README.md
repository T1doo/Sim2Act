# 双求和与项目固定报告的目录用户闭环

承接已获父追加有限独审接受的 `118aefa6c9dad95311c8739e1fda8b151293c213`。[原产品§2](../../平台产品设计.md)的应用使用界面、[分阶段计划F2-T05](../../分阶段开发计划.md)统一入口，以及[双求和合同](../../F2/CsvTwoSumInstances20261011.md)/[项目列版本合同](../../F2/ProjectColumnVersions20261011.md)，是本轮依据。四个版本允许集和全部产品src已在118存在；本轮推进此前未在新目录实际验收的两个家族，不把仅缺少测试称为新执行能力。

## 两条路径

双求和：原 `internal.csv-read-two-sums.v1`，固定同一CSV，两个稳定节点交换amount/quantity；合成小数独立结果为0.3和2.250，保留两份完整五字段对象和单次原子typed结果。

项目固定报告：原 `internal.project-csv-read-sum-report.v1`，选择整组版本中的peer应用及其自己的Release/来源，不先打开旧项目修改键面板。批准默认quantity，明确另选amount得到30，再确认quantity得到15；报告文本来自该同Run原证明，typed仍为五字段聚合。

两者均目录精确选择实例、打开零POST、改列撤回旧确认、另行确认及双击单POST、每次独立Run、新cold NoModel Worker、同Run/typed appRun/实例/revision/Release/input/结果version/完整output/record fingerprint绑定；冷页面零POST找回同两Run和v1/v2。无新executor、Grant、schema、执行家族、模型、部署或正式发布。夹具真实来源Worker Run分别1和4；后者另有两次同步preview，不计Worker。目录新冷Worker每家族2次，单列统计。

## 冻结与审查记录

首源 `c628c874bcf195e4328e285421236475cca620cd`：作者新增2PASS363.40秒、相关原use/report两项2PASS165.88秒，均RC0。独立同四节点4PASS546.977秒/RC0，但整体仍因覆盖缺口BLOCK；[原独审报告](independent-blocked-c628c874/independent-review.md)和完整原件保留。

独立dual实际selected等于首个权威dag-instances.items[0]，所以“第二创建实例”不等于非默认选择。此为实际观察；标签匹配整panel（含proof文字）、可见行仅匹配sum集合则是另外两项静态断言精度缺口，不冒充动态错误UI复现。修订从权威列表第二项决定target，并精确断言两个可见label及每个版本行的sid/column/count/sum。静态复核已接受这三个修正。

最终测试冻结 `b670cb0c2a25dc363ffdaa0ea8d8a1d747c99d39`，全部产品src与118相同；本次仅测试驱动/夹具和FirstUse说明修改。作者、独立侧各跑dual/fixed/use/report四节点，均RC0、4PASS/0FAIL/0ERROR/0SKIP。最终有限独审通过见[独立报告](independent-passed-final/independent-review.md)。唯一节点共4项：新增2、必要相关2；独立同四项重复，不另增唯一节点。

| 最终冻结节点 | 作者秒数 | 独立秒数 | 各侧JS检查 |
| --- | ---: | ---: | ---: |
| 双求和dual | 109.612 | 106.694 | 32 |
| 项目固定报告fixed | 254.697 | 243.408 | 32 |
| 原求和use（相关） | 89.362 | 96.311 | 23 |
| 原报告report（相关） | 102.763 | 102.820 | 25 |
| XML批次总时间 | 556.927 | 549.508 | — |

两侧两个新家族均从实际授权列表选择第二项，初次及冷页面选择框index1断言完成；双求和两个实际可见标签分别绑定稳定节点ID，可见版本行逐项匹配sid/column/count/sum。JSDOM断言完成记录及冻结驱动保留；没有另行录制DOM文字快照或原生浏览器操作。作者17个冻结文件保持不变，独立20个源/依赖/测试文件前后匹配冻结Git，全部产品src与118零差异。此冻结后的提交仅归档本轮证据。

旧wait、带真实回复时间戳的waitHeld和原guards方法与118逐字相同；12秒真实回复间隔/当前空闲、60秒总上限保持。本轮不选择旧guards、conditional/恢复、private callback/barrier矩阵；空intent Map不作未知请求恢复证明。

## 原始证据与范围

本目录归档只覆盖此轮自己新生成的作者/相关/独立原件，不重新签署此前377原件或历史各源。原路径/大小/SHA→gzip或identity归档路径/大小/SHA逐项映射，原目录保持；最终[SHA256SUMS](SHA256SUMS)覆盖本目录其余文件。本轮原件共188项（作者/相关74、初版独立57、最终独立57），逐项验证归档字节、解压字节及当前原件一致；校验表192项，含上述原件归档、3份映射和本说明。三个映射分别保留[作者/相关](author-related-archive-manifest.json)、[初版独审BLOCK](independent-blocked-archive-manifest.json)、[最终独审PASS](independent-passed-archive-manifest.json)的本轮原件。

[终态汇总](author-and-related/final-batch-results.json)列出精确节点、两侧非首项实际ID、独立52项payload manifest大小/SHA验证及Worker分项统计；[最终独立证明](independent-passed-final/independent-proof.json)和[静态原件来源](independent-passed-final/static-source-provenance.json)保留。每个独立目录的完整原件同时归档，包含manifest范围外的报告、证明和打包脚本。静态文件是与实际served响应SHA相同的冻结Git副本，非原始网络传输抓包；result.json保留实际ASGI请求/响应观察。

前一切片的8f7静态缺陷、212可选脚本兼容缺陷、880迟到错误门具体调度原因未明，仍按[原记录](../csv-dag-directory-20261017/README.md)解释，不统称抖动；84修订等待合同不变。PARTIAL仅显式关闭报告，本轮不新增其验收。

PG、原生浏览器/IME/剪贴板、Windows、真实模型/语义、Actions/远端CI验证及部署不执行。不重试被拒下载或平台前置，不修改main、费用、凭据、安全权限。原满盘独审报告缺口未补回。
