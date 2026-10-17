# 普通成功CSV合同 → 显式仅求和应用：有限验收

基线 `f3fa91702ef79114557b8db6e2dcdbcf262de101`；测试及源码冻结 `f3d0e96487f57941255f68f6c501b6956cc5f31b`；普通分支 `dev/ordinary-csv-sum-pb-20261017`。冻结后仅增加说明及本证据包，交付SHA以实际Git和推送后核对为准。[使用说明](../../ordinary-csv-sum-apps.md)。

本片闭合原方案P-B的一条有限来源路径：普通CSV任务先经事前明确确认，读取、求和、完整MD保存及独立回读真实成功；用户从该Run明确选择**只提取求和步骤**，绑定同项目另一份已有授权CSV，独立验证新输入，再沿已有内部版本、实例和统一目录运行。原完整报告PASS仅是来源证明；候选及新应用不承诺生成/保存MD，不继承完整报告验收，也不把人工ACCEPTED当技术SUCCEEDED。

## 实现与边界

`ordinary_csv_extraction.py`新增明确来源kind `ordinary_csv_sum_source.v1`，复用原 `ordinary_csv.accepted_result` 核对完整合同、原明确确认、三步intent/receipt/effect及MD原字节；证明绑定真实GoalSpec ID、合同/确认/结果/回执/hash。普通CSV报告没有GoalCard，本片不补造GoalCard或旧Run的internal binding。候选单独声明SUM_ONLY范围，manifest的source_run_ref指真实普通来源。没有复用要求iid的旧registered journal或伪造AppRun。

新kind在apps来源分类和冻结validator中精确分派；metadata gate先投影源材料、独立local_effects保存ID及目标引用并当前鉴权，再读取Run/candidate正文。保存回执refs损坏不能隐藏独立保存ID。候选读取、原key回读、内部版本和实例沿原生命周期重算来源、目标和候选；不对已成功来源重新施加执行截止时间，当前必要权限仍逐次检查。

提取只写一个app_draft和task_extractions提交回执，同项目锁及原key/原指纹保证并发幂等；改正文冲突，GET原key不提交。沿用目标已有runtime和授权，不新增Principal、Grant、Resource、table、权限动作或executor。**该零新增范围从原报告执行及目标授权完成后开始**；原报告保存及目标准备仍使用既有Resource/Grant政策，不是整条夹具过程零副作用。

页面有默认未勾选的SUM_ONLY同意、明确保存及明确打开，源证明和目标hash/runtime可见；正常同scope/Run版本后台重画保留表单，导航返回重新读取并清除确认。UNKNOWN保留原body/key，用GET恢复；显式重试仍只用原body/key。打开时先核对回执及候选，再将临时Run scope交接到已选应用scope，已有版本控件可继续使用。目录显示CSV单步汇总且注明普通任务提取、不含MD。API/UI不改变旧natural、registered或local来源合同。

## 最终实际执行

| 批次 | 新API | 新整页 + 既有回归 | unique | 输入 |
| --- | --- | --- | ---: | --- |
| 作者f3d | 9PASS，JUnit25.321秒 | 6PASS，JUnit65.083秒 | 15 | 593个，前后相同；测试结束工作树干净 |
| 独立Git快照f3d | 9PASS，JUnit26.811秒 | 6PASS，JUnit65.824秒 | 同15，额外unique0 | 594个，Gitblob及前后相同；多一个同SHA既有goldfixture |

各子批RC0、0失败/错误/跳过；union15、overlap0，不计成30。作者两隔离子批并行墙钟67.197秒，JUnit之和不是墙钟。593=src120+tests465+schemas7+pyproject1；独立另加重建所需gold1。[作者命令/RC及检查](raw/author-meta/final-execution.json)、[精确节点](raw/author-meta/final-collected.json)、[作者API XML](raw/author-meta/final-api-junit.xml)、[作者页面/回归XML](raw/author-meta/final-pages-related-junit.xml)。[独审报告](raw/independent/review.json)、[独立proof](raw/independent/proof.json)、[独立API XML](raw/independent/api/junit.xml)、[独立页面/回归XML](raw/independent/pages_related/junit.xml)；独审结论 `PASS_BOUNDED`，无未关闭静态阻断。

9新API覆盖：完整成功来源、SUM_ONLY证明及原Goal ID、提取只新增草案/回执；另建Store/API客户端通过原key恢复候选并独立预览不同材料/列得到15，无效非数值输入失败；原版本/实例/Worker建立新Run与结果v1，原来源仍无internal binding且原结果不变；缺失/错误同意拒绝；同key并发仅一个候选、异正文冲突、GET不写；原材料/原已保存报告/目标runtime撤权及来源结果改变拒绝缓存和提交；旧PARTIAL MD任务即使真实合成账本ACCEPTED仍不准入；来源执行期限已过后仍可在当前权限下提取。排队后来源撤权沿既有Worker进入WAITING_RESOURCE/GRANT_REVOKED，没有新保存/模型/结果，也不会自动领取重试；未擅称FAILED。

来源材料及已保存报告撤权时，3入口均在完整Run/candidate正文SELECT之前拒绝；saved-report例另损坏receipt.refs，独立local_effect仍先鉴权。4份scope SQL原件在[作者API夹具](raw/author-api/)，方法为合成夹具SQL撤权/损坏，不是本次可见撤权按钮验收。

3新整页以实际HTML/CSS/全部23项页面资产、authenticated ASGI RPC及原Worker运行：

- deliver和lost各经可见控件执行新列预览 → 精确版本批准/保存 → 创建实例 → 统一目录选择 → 明确提交新列 → 新Run实际结果15/v1及既有验收状态区域 → 导航重开零提交。
- lost在实际201受理后丢响应，双提交仍只有一次提取POST；工作区返回保留原key并GET恢复，没有第二次提取POST。
- navigation持有实际options回复后切项目、持有实际candidate回复后切换身份并重连B，迟到回复不安装应用、不新增提交。该例不执行版本/实例链。

合计**40条可见断言、248次实际页面API回复、69次资产校验**，不含夹具及Worker RPC。[逐页统计](raw/author-meta/final-scope-summary.json)、[deliver原件](raw/author-pages-related/test_visible_sum_extraction_th0/page-result.json)、[lost原件](raw/author-pages-related/test_visible_sum_extraction_th1/page-result.json)、[navigation原件](raw/author-pages-related/test_visible_sum_extraction_th2/page-result.json)。原完整来源任务由Python夹具预先真实执行，页面从其任务历史起步；不是原报告GUI从零创建验收。驱动关闭interval计时，以实际showRun/API手动触发正常后台重画；不声称实测2500ms调度或原生浏览器。没有下载手势或Blob验收。

验收状态断言仅证明既有区域存在并显示PENDING，**没有证明CSV人工声明可提交**。实际owner-review返回200元数据、`content_access=false`及`invalidation_reason=UNSUPPORTED_CAPABILITY`（见deliver请求原件），这个CSV家族目前不能提交人工声明。本片不新增其人工验收合同；原测试/独审中“入口”的表述按此只读状态区域理解，不能扩大为已可人工签收或同Run完整声明验收。

3既有回归精确为ordinary prospective完整CSV报告、registered成功AppRun提取新列、旧natural回执候选durable runner新结果及错误输入；没有旧故障长矩阵。本片CSV来源及派生主路径为NoModel；manual-ACCEPTED MD负例使用旧ScriptedMd合成响应，旧natural回归使用MockTransport。真实模型0，不能把整批称为零合成模型请求或全部NoModel。新Store/客户端/Worker仍在同一Python进程内，不是独立进程重启。

Ruff、单个新模块mypy、四个JS语法检查通过，范围见命令原件，不代全项目静态检查或远端CI。此前37项、终态3项及作者额外SQLite迁移探针均未在本片重跑；未扩大其独审或迁移结论。没有PG/运行角色配置、Windows、原生浏览器、真实模型、真人/真实语义、正式发布、部署或远端CI。本片只准入这条有限SUM_ONLY P-B桥，不关闭通用P-B、模型自主生成、记录CRUD或新权限动作。

## 原始资料与失败保留

本目录封存**182份资料、185个文件、184条SHA256SUMS**，含54个SQLite（首红/开发/两轮最终夹具，不能按54例计数）。[artifact-map.json](artifact-map.json)逐件列原路径、长度、原SHA、类型及编码；DB和大文件mtime0 gzip，其余原字节保留。解码后逐件等于原件；资料包括运行输出、派生审查及复现辅助脚本，未混称全部为运行输出。

首轮归档辅助脚本按文件名排除SHA256SUMS，误漏了嵌套的独审原清单；已改为只排除顶层自身，现184项全部校验。原清单、运行原件及首轮Git提交保留，没有改写独审封印。

独审manifest58项，加manifest/sums共60件；[封印核对](raw/author-meta/independent-seal-verification.json)、[原manifest](raw/independent/raw-manifest.json)、[原SHA清单](raw/independent/SHA256SUMS)。其SQLite路径指原未压缩件，按artifact-map解码后校验。

首红在原f3fa生产源码、测试提交 `490008ec301adef0253783974e1466a7eadbe144`，真实完成来源后新options路由HTTP404：[首红日志](raw/author-meta/red.log)、[来源](raw/author-meta/red-provenance.json)。保留开发期SQLite嵌套HTTP夹具锁、HTTP400/409及WAITING_RESOURCE/FAILED断言误期、隐藏connect夹具手势失败原日志/XML/SQLite；它们不是最终准入失败。静态handoff、后台重画、原key响应绑定及confirmation指纹改进均在f3d冻结前完成。[准确说明](raw/author-meta/development-notes.json)为派生说明，不伪造未执行的旧UI红测或缺失报告。

[开工真实checkout、容量、default Git网络与23条保护引用](raw/author-meta/preflight.json)、[原8fc祖先核对](raw/author-meta/ancestry-check.json)。未访问旧满盘实例、旧bundle或旧共享文件；已知旧独审未落盘缺口未声称补回。交付及远端差异在普通推送后另按实际SHA核验。
