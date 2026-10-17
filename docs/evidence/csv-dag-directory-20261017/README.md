# 已保存 CSV DAG 实例的统一使用目录

基线 `6aa815dd72f3bb975e0c554d3a8b6725e00f8eeb`。同一普通 CSV 草案可以保存普通和 DAG 两类内部实例；原目录只读取 `/api/internal/apps/{aid}/instances`，该路由明确排除带 execution_source 的 DAG 实例。已有 DAG 实例路由、canonical seal 和 `dagReuseHistory/Read/Submit`，用户却不能从统一目录找到。本片接通这个入口，复用[原合同](../../F2/CsvDagInternalReuse.md)与控制器。

## 可见行为与验收边界

目录分别标注“CSV 单步汇总”和“CSV DAG”，DAG 行显示完整实例、原图种类、固定授权材料/允许列、结果版本及未发布/UNKNOWN/PENDING。打开重新鉴权并核对原计划、来源、版本和回执，只执行 GET。用户选择新列并另行确认后，才提交原 durable Run；双击只产生一个提交，同一 Run 的完整证明和 typed 结果历史经原 seal 核验，冷页面能找回。

允许集恰为已有四版本：`internal.csv-read-sum.v1`、`internal.csv-read-sum-report.v1`、`internal.csv-read-two-sums.v1`、`internal.project-csv-read-sum-report.v1`。目录端到端本片只实际执行前两种。双求和和项目固定报告依赖原核查器，本片没有重新完成其目录端到端验收。未知图/版本没有可运行按钮，提示不是执行授权；普通实例不能从 DAG 入口打开。

账号连接、项目、工作区和应用选择围栏覆盖整个打开链；读取实例另有局部代次。迟到成功和错误不能覆盖或清空新选择。工作区离开、当前目录缺失/明确排除、同应用权威读取拒绝或未知图提示会清空 protected DAG 视图，原 intent Map 保留。临时 delivery 围栏仅用于原支持的 CSV source，字面文本往返工作区后仍能发起显式鉴权读取。普通 CSV 仅加载原四脚本时也能使用。

没有新增 executor、Grant、Principal 策略、API、schema、运行器或 DAG 表达能力。原内部实例只接受无条件闭合图。原条件报告的 typed boolean true/false 分别 SUCCEEDED/PRODUCED、PARTIAL/SKIPPED；关闭报告时 output=null，两者保存内部版本均实际409、实例列表为空。PARTIAL 在这里仅是显式关闭报告，不是异常恢复。没有选择私有 barrier/callback 模块、旧 lost 或相邻故障/恢复矩阵。

## 执行源与独立结论

最终测试冻结 `84d0f923a7706da84baf010a4e217e28cae48f5e`。相对 `8800aa800d71a2d389a4283796e8a62271e06b4d` **只有 DAG 测试驱动变化**，产品及相关测试源码逐字相同；后续交付提交只添加本目录证据。作者4项、相关3项、独立6项重复验证在此有限范围通过；各轮是不同执行记录，旧绿不提升旧源准入，旧失败不被覆盖。

| 实际执行源 | 作者新增 | 相关三项 | 独立重复 | 整体状态 |
| --- | --- | --- | --- | --- |
| `8f7ffd93…` | 4 PASS，239.76s | 3 PASS，126.72s | 4 PASS，221.694s | 静态 BLOCK：非CSV临时围栏遗留、目录拒绝后旧DAG缓存未清 |
| `2128454e…` | 4 PASS，229.90s | 1 FAIL / 2 PASS，116.95s，RC1 | 5 PASS，271.053s | 兼容性 BLOCK：未加载可选脚本时直接引用全局，原CSV组件超时 |
| `8800aa80…` | 4 PASS，356.70s | 3 PASS，106.33s | 5 PASS / 1 FAIL，430.712s，RC1 | 独立 guards 等待精确拦截点超时，后续断言未完成 |
| `84d0f923…` | 4 PASS，194.31s | 不重跑；沿用实际880源3 PASS | 6 PASS，269.752s，RC0 | 有限范围 PASS；产品字节与880相同，仅修测试同步 |

最终[独审报告](independent-passed-final/independent-review.md)、[准入统计](author-and-related/final-batch-results.json)和[独立原始载荷清单](independent-passed-final/raw-manifest.json)可直接检查。表内作者/相关时间来自 pytest 末行，独立时间来自其XML；各 XML 的完整精度另保留。相关三项恰为普通 CSV 使用、字面目录 use、闭合文本目录 use，在880实际执行，检查数分别30、22、29。[有界同步及源码比较检查](author-and-related/static-checks-hold-sync.json)的 Git 比较证明整个 `src/` 与相关驱动、Python 测试及 conftest 在84保持相同。独立84仅重复新增四项＋字面 use＋普通 CSV，共六项，不另算唯一节点，不声称重跑闭合文本。

旧静态问题的修复和行为回归均保留：限制临时围栏的类型；实际撤权→刷新403清旧 proof/results→捕获旧回调再403；字面工作区往返后可见 delivery-read 发起实际 GET、零 POST；三个 typeof 存在性检查保持可选模块缺席时的组件兼容，不放宽模块存在时的守卫。

880独立失败仅完成 guards 前7条：三种导航与迟到成功。第二次迟到错误的精确拦截点未在总12秒内同步，最终记录目标 GET200，但没有错误注入，随后未知提示/真实撤权断言未完成。原记录没有时间戳，不能确定调度原因，也不能宣称该轮后半通过。完整[独审报告](independent-blocked-8800aa80/independent-review.md)与失败原件独立保留。

84的测试同步只接受精确 HTTP 门：实际回复记录时间戳；先拒绝任意>=12秒真实回复断档、当前空闲>=12秒或总>=60秒，再接受门。其余 wait、close、17条 guards 产品断言及所有产品代码未改。首个未执行原型因用轮询时间续期被静态拒绝，修订版才[静态接受](independent-sync-static-review/static-review.md)。原型diff/hash、实际驱动提取的合成时钟边界探针和五个探针结果另存，探针不是新的产品验收节点。

## 实际最小范围

新增四节点为求和 use、求和加报告 report、guards、既有有限条件分支不可实例化。两个正常目录节点各明确提交 quantity/amount 两列，逐次双击仅一条原 Run POST；queued Run 不复制旧结果；共四次冷 NoModel Worker 得到15/30、结果v1/v2、两或三条 VERIFIED 步骤、business_writes=1、model_requests=0。报告文本保留完整 Run proof，typed aggregate 仍为五字段。冷页面零 POST 找回同两 Run 与结果。

三个 UI 节点各有一次成功原 DAG source Worker 作为合成夹具前置，单列统计；有限条件分支节点另执行原 true/false 两次 Worker，不冒充冷目录 Worker 或故障恢复。新增批次不调用生成模型，运行模型请求0。

guards 经实际鉴权 ASGI HTTP 覆盖工作区ABA、同账号重连、项目ABA、同一面板切换实例后的迟到成功/错误隔离、普通实例误入 DAG 路由拒绝、未知/原型名 toString 提示无入口、真实合成授权撤回后刷新403清缓存及旧回调重新403、零产品 Run/Grant POST。原48表只读检查与 principals/Grant 边界保留，仅一笔明确合成撤权例外。

迟到错误403与未知版本是驱动有标记的受控交付变化，actual HTTP JSON先原样保存，不能冒充服务端真实403；真实撤权403是另一路服务端响应。正常 use/report 不修改交付响应。DAG use/report/guards 完整执行时分别23/25/17条检查；唯一节点分母仍为新增4＋相关3，独立重复不增加。作者84的5门实际338/1693/88/7363/5513ms；独立84的5门147/1044/53/2861/3073ms，均未触发边界。这不能反推880失败的调度原因。

## 原件、编码与未运行项

精确命令、执行SHA/文件SHA、log/XML、info/result/database-proof/branch-proof、SQLite DB、API响应JSON与静态资源SHA按批次保存。最终六份 archive-manifest（作者相关、三轮被阻断独立、同步静审、最终独立）列原绝对路径、原SHA/大小、归档路径、编码及归档SHA/大小。DB、大JSON、部分log/XML/diff采用gzip无损压缩，逐件解压匹配原件，原目录不改写。独立原始manifest和报告原字节保留；同步静审和动态独审分开。hold-sync源元数据的utc字段继承自880，实际84提交/执行时间见另存的时间字段说明与XML，不用旧utc当作84运行开始。SHA256SUMS覆盖本目录其他全部文件。

静态 HTTP响应保存路径/SHA；独立statics是与已记录响应SHA匹配的冻结源码拷贝，provenance明确，不冒充新增请求或原始响应流。所有新增DAG API响应JSON记录 actual response，受控变化另列 mutations。

PG、受保护原生浏览器、原生IME/剪贴板、Windows、真实语义/场景、真实模型、双求和/项目固定报告目录端到端、远端CI验证及部署未运行。没有再次诊断/重试此前被拒的PG/browser/cache/403下载，没有修改sandbox、凭据、安全、权限或网络配置。既有平台卡点、原满盘环境未落盘的最后独审报告仍是原证据缺口。
