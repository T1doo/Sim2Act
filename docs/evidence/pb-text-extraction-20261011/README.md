# 有限非CSV P-B：成功文本 AppRun → 独立新材料应用

基线 `e17d7c44098492745b23a57adaa715adb490119d`，独立分支 `dev/pb-text-extraction-20261011`。root 是唯一产品写入者；现有独审只读产品、只写自己的 /tmp，未启动新的并行产品作者。默认工具环境与网络实际成功，环境重连核验见 [environment-check.json](environment-check.json)。

## 合同和实现

[有限合同](../../F2/PBTextExtraction20261011.md)依据 F2-T03 / AT-10 与原 V5 P-B。复用原 text.literal_evidence@1、source.literal_evidence.v1、正常 Worker 和生产 API；无新算子、模型能力、凭据、Grant、部署或数据表。只认可原目标生成应用的实际 SUCCEEDED 持久文本 AppRun；核对当前授权、身份/项目/实例、来源与版本、类型化输出、实际步骤 intent/receipt、完整引用和材料 hash。字面 AppRun 真实模型 Attempt=0，上游生成 Attempt/wire 另按原独立校验核查。

新材料通过同项目初始目标应用的既有授权域选择，TXT/MD 不同内容、4096字节/64行以内。事务只插入独立 app_drafts/task_extractions，原逻辑 Schema/限额/只读效应不变，原完整 GoalCard 仍属来源 provenance，新执行绑定与依赖指向新材料。目标变化、取消、撤权、版本竞争、污染和迟到计算不能提交新结果。

文本 task_proof 封印完整 extraction_request（含原 key）。未知提交结果仅用原 key GET 读取；新草案真实 SHA-256、完整来源 proof、目标授权域/绑定和完整 request 必须与回执匹配后才交给 showApp 安装。受控错误回执不会通过错误 app ID 的通用回读恢复绕开校验；原 key 保留，必要时通过可见应用列表重开来源后显式恢复。编辑及撤销、工作区/身份/应用/目标/实例/Run代次变化后，迟到响应不得安装状态或转移焦点。

API 共用 scope_run 在同一事务内先按 Run ID/principal 仅取项目身份并核验项目 owner，之后才取完整 Run；控制不要求材料 Grant。真实私有单元屏障覆盖六入口×外国owner/受控外国project两范围，均403且零受保护单元读取/零DB变化；另实测已提取应用撤权后控制状态与取消可用。

新应用/内部版本/实例 owner 为 PENDING；当前 owner 签收入口限定原 goal_application，未以 task_proof 自动继承声明或冒充适用。历史保留；原来源授权和证据仍用于保守审计，不宣称来源数据已退休。技术语义 UNKNOWN、正式发布 false、LIVE0，测试人工选择为 SIMULATED。

## 第三冻结候选实际验证

第三候选 manifest [candidate3-source-freeze.json](candidate3-source-freeze.json) SHA-256 `5f1785b3afc33b30e13b80f6239d6bc86e539853ef9691bb780e5f2f7906f570`，365个实际源码与测试文件。只在上一作者进程结束、独审确认自己的进程全结束后解冻修复，再冻结并执行。原 [候选一](candidate1-source-freeze.json) 和 [候选二](candidate2-source-freeze.json) 均撤回，不接受为最终结果。

作者完整关联轮实际463 collected / 462 selected / 1 deselected，健康结束exit1：418 PASS / 34 FAIL / 10 SKIP / 0 ERROR，pytest690.71秒、进程692.10秒。34FAIL全部为既有test_goal_text_ui.py继承系统NODE_PATH，启动即找不到jsdom，未执行其页面脚本；[完整原始XML](candidate3.xml)、[日志](candidate3.log)和[分类](candidate3-full-result.json)不改写。10SKIP均为明确PG角色前提缺失。仅修runner NODE_PATH=/workspace/node-tools/node_modules，实测require.resolve(jsdom)成功；完整34个失败节点在完全同一365源码上复验为34 PASS / 0 FAIL / 0 ERROR / 0 SKIP，exit0，pytest271.75秒、进程273.07秒。原失败(classname,name)集合与复验集合完全相同，且不与首轮418PASS重叠；两个实际轮次在同源下闭合452个唯一PASS、10SKIP，另1deselected。不是一次完整全绿重跑。[复验XML](candidate3-pa-corrected.xml)、[明确runner环境与命令](candidate3-pa-corrected-command.json)、[两轮节点集合/源码证明](candidate3-two-run-coverage-proof.json)。复现命令见 [candidate3-command.json](candidate3-command.json)，使用 SQLite，明确移除 SIM2ACT_TEST_DATABASE_URL。关联16模块包含原 CSV 提取、目标文本生成/来源、owner、版本/持久运行与受影响页面，不是全库或PG测试。

独立最终维护43 PASS / 0 FAIL / 0 ERROR / 0 SKIP（34后端+9页面，pytest340.01秒、进程342.00秒）；[原始XML](independent/candidate3-maintained.xml)与[进程回执](independent/candidate3-maintained-result.json)。另外独立keyed恢复3 PASS（35.95秒）、来源污染7 PASS（27.63秒）、跨范围/撤权控制3 PASS（14.24秒），分别保留原XML/log/回执；不与作者重叠维护节点加总成唯一覆盖量。独立365文件前后完全一致，after证据SHA-256 `2c1a418b963d66b20f535df39b9c5f5c4fb33648d316816e139c3c9bcca2298d`。

独立9页面每次开页真实HTTP获取19资源（每场景2次开页、38GET），合计180检查、265可见且enabled的DOM动作、18次开页、342资源GET，各status/MIME/bytes/hash匹配；提取POST每例恰1。三条另加恢复探针45检查、57可见动作、57HTTP资源GET、每例原key两GET/一POST，专验安装门不重复调用Worker。页面冷链按新材料/新Gamma输入启动实际普通Worker，新的Run/结果版本1精确回读，两行新引用与旧任务结果区分。原始[页面指标](independent/candidate3-page-metrics.json)和[实施独审](independent/implementation-review.md)。

作者修正路径后的34分为29个实际IPC HTTP/JSDOM页面和5个受控本地源码microtask调度测试；后5不声称HTTP/Worker。29页1307检查、1261可见enabled DOM动作（另2条input_events诊断摘要不计为动作）、59次开页、1121实际资源GET（每boot19），逐项核对当前源hash/status/MIME/bytes；[分列页面指标](candidate3-pa-corrected-metrics.json)。驱动字段的native DOM dispatch指JSDOM标准事件，非原生OS/浏览器。作者新PB9页为180检查/265可见动作/18boot/342实际资源GET、9次提取POST，各资源status/MIME/bytes/hash匹配；[作者PB指标](candidate3-pb-author-metrics.json)。作者新PB9页及独审9页仍分开保留，不混同后端技术PASS与真实人工语义。

改动 Python Ruff PASS；三份 JavaScript node --check PASS。全库 Ruff10既有诊断与e17封存JSON逐项相同；mypy5既有错误与原log全文相同，不能报告全库lint/typecheck绿。实际 [static-exits](candidate3-static-exits.json) 与 [基线比较](candidate3-static-baseline-comparison.json)。

## 失败与撤回候选保留

- preflight pytest命令不在PATH：未执行测试，改用仓库venv。
- red.xml：目标生成夹具误用相同key，产品请求前409；red-corrected.xml为真实初始 API 不支持文本提取的红测。
- backend-first：最小冷计算1PASS，为修复过程中间候选，不能覆盖最终整组。
- backend-matrix-first：25PASS/1FAIL。额外record插入被DB唯一约束先拒绝，改测已存record内容污染；不宣称可插入重复记录。
- ui-first：精确中止exit2，Node原15checks成功但Python IPC清理阻塞；pytest0完成用例，不能计PASS。
- ui-provisional：4PASS/2FAIL。夹具分别漏重选目标、暂停了目录读取；完整日志保留，修正真实可见动作与明确应用读取位置。
- candidate1：精确SIGINT撤回、exit2，完成127PASS/1FAIL/1SKIP另1deselected；FAIL为新SQLite barrier测试过早dispose的清理错误。JUnit另有1个无name的中止节点，不能计PASS。独审维护37=36PASS/1相同夹具FAIL；页面6PASS不代表恢复已安全。
- 独审实际受控HTTP红探针证明错误第三应用ID、全0 candidate指纹，以及同来源/目标/名称另key的真实P-B应用ID+指纹协调替换均可能安装。原红探针、加强actual_text/controlled_text、原候选源码均保留在 independent/；不能只留下修复后的绿轮。
- candidate2：作者精确SIGINT撤回exit2，40PASS/1deselected，pytest321.24秒、进程322.69秒；独审43新增前维护41全部PASS，也仅作撤回候选子集。实证foreign owner提取入口虽HTTP403，但scope_run先选完整外国Run私有字段，独审foreign-private红1FAIL；仅证明未授权内部SELECT，不声称403响应泄露原文。原SQL/log/XML保留，按同事务metadata门修复。
- scope3：两新增定向节点2PASS/32deselected/6.31秒，第三候选的中间定向验证，最终关联/独审另列。
- pa-debug3：定向1FAIL/1.35秒实证模块路径缺jsdom，原log/XML保留；没有产品源码改动。完整candidate3的34环境FAIL及修runner后的实际结果分开列于上述关联验证段。
- smoke2：10PASS/1FAIL/30deselected；新candidate-fp夹具将正确未安装activeApp=null与空poison_app比较，误报FAIL，已修断言；原body与日志保留。
- 独审source首轮6PASS/1自编夹具FAIL：误用存储assistant response的wire字段，在产品请求前KeyError。新v2实际7PASS；旧原日志不覆盖。

[各中间轮JUnit摘要](provisional-rounds-summary.json)排除了中止产生的无name节点，原XML/log始终保留。

## 验收边界

PG、Windows、原生浏览器、旧源码升级、真实模型/付费API、真实owner语义、完整P-A/P-B/AT-10、部署/正式发布均 NOT RUN。JSDOM为离线DOM，加载实际进程内HTTP的HTML/CSS/17脚本及实际API，不能冒充原生浏览器。合成test-only provider用于准备上游原生成应用，不能冒充真实模型；冷字面Worker不调用provider。新SHA远端CI尚未验证，不宣称CI绿。

正常推送只操作上述独立开发分支，不修改main/core dev，不强推、不配置网络安全权限。原证据各tree/blob与e17基线交付前逐项核对；推送与远端完整SHA/干净状态交付时另核。独立原字节[224档封存清单](independent/archive-manifest.json) SHA-256 `d553d4942b5a2425f04a6534c4b529d9020ef44636a97c94f4446906596ede72`已逐项复制核对；包含pytest自带README元数据文档，不含实际cache数据或DB。

仅提交可复核源码快照、命令、原日志/XML/JSON及HTTP回执。额外复制的合成fixture数据库不进入仓库，其原/tmp文件仍保留；[排除回执](independent/fixture-database-exclusions.json)。
