# 成功注册 CSV Run → 服务端生成草案：HTTP/UI 本地实施记录

2026-10-06；独立 worktree `/workspace/Sim2Act-generation`，分支 `registered-run-generation`，起点 `a6f68e1`；未 commit（父线程统一审查）、未 push/CI/LIVE/native browser。范围按 [RegisteredRunGenerationSlice](RegisteredRunGenerationSlice.md)；本记录不签收完整 P-A/P-B、语义目标、正式发布或 Windows。

## 实际变化

`internal_api.py` 新增当前身份、instance/run绑定核查下的 GET extraction-options / POST extract。POST仅接受 expected_proof_fingerprint、target_app_id、expected_target_draft_fingerprint、name、request_key；extra严格422。来源证明、目标材料、既有runtime、模板、检查、预算由后端确定；用户不提供candidate、wire、gold、运行权限或能力字段。接口调用另一并行后端的registered_run_extraction.options/extract，未建立另一个运行器。

`web/internal.js/index.html` 在非agent、无cancel意图的SUCCEEDED内部CSV Run详情显示“将这次任务保存为可复用草案”。GET通过后显示来源proof/hash/检查范围和目标应用既有授权域。用户只选目标已有CSV应用及名称；声明共享撤权影响、不新授权、0模型请求、语义未验收。身份/project/app/instance/run/version及接受配置共同锚定请求；改变名称/目标配置产生新的key，原配置恢复仍可手动恢复原key。源选择/身份变化的迟到响应不呈现；轮询同源状态不替换当前表单。丢POST回执不自动重发；已接受生成后丢草案回读复用原appReadRecovery，仅重新GET，不再生成。

`web/app.js` 按task_proof.proof.kind=`completed_registered_csv_apprun.v1`区分新真实持久AppRun来源和旧LOCAL_DECLARATIVE_TASK来源；显示可信求和、独立精确数值核查、新CSV+column运行参数、NOT_RUN/未发布。应用区简介同时如实描述已有TXT/MD字面agent只接受Replay；没有模型自主生成声明。未改app.css或Windows脚本。

## 实测及原始失败

命令均在此worktree，Python使用既有`/workspace/sim2act-pb-venv/bin/`依赖；无下载/权限扩展。

- `pytest tests/test_registered_run_generation_http.py -q --disable-warnings`：17 PASS / 1旧Starlette/httpx warning。实际后端HTTP：成功CSV Run生成新app、新action；同key返回同app；额外13种candidate/wire/权限字段422；跨身份/错误iid403；同key改name或stale目标fingerprint409；撤权后GET及cached POST403。冷Store/新HTTP会话打开生成app→内部批准/Release→instance→worker→新column `other`，结果15，与源4.00不同，结果版本1；生成不增加Principal/Grant/Run，已有Grant内容不变。
- `pytest tests/test_internal_api.py tests/test_registered_run_generation_http.py -q --disable-warnings --maxfail=1`：35 PASS / 1 PG专属SKIP / 1旧warning。
- 最后新增草案GET回执丢失与目标撤权DOM检查后：`pytest tests/test_registered_run_generation_http.py::test_real_http_dom_generation_entry_and_lost_receipt tests/test_agent_ui_replay.py -q --disable-warnings --maxfail=1`：21 PASS / 1旧warning。其中真实本地uvicorn HTTP驱动jsdom检查14项全部PASS：真实SUCCEEDED入口、服务proof/目标、共享授权文案、POST回执丢失、封闭发送字段、改配置/恢复配置、原key原body重试、accepted app只读回读恢复、新app来源/ID、迟到源响应、身份变化不提交、GET选项后目标撤权拒绝并清空。新草案仅由实际POST生成，未seed衍生candidate。
- `ruff check src/sim2act/internal_api.py tests/test_registered_run_generation_http.py` PASS；`mypy src/sim2act/internal_api.py` PASS；Node语法检查internal.js/app.js/DOM脚本 PASS。

第一轮HTTP曾16项中1 FAIL：冷生成app内部审批GET进入后端validator，冻结draft无name导致KeyError。另一并行后端已修为有name时核name，冻结对象仍以独立接受request fingerprint绑定；实际冷链重跑PASS。新增DOM第一轮实际12检查全通过，但Python误期望11，曾报告1 FAIL；修正计数后通过，随后有意义新增GET回读故障/撤权两项，总14。保留失败事实，不作为源成功证据。

DOM驱动脚本在`tests/registered_run_generation_dom.cjs`，使用标准`require('jsdom')`；Node/jsdom仅开发测试依赖，不加入产品依赖。可在自己的开发工具目录安装jsdom后设置`NODE_PATH=<开发node_modules目录>`，测试探测Node模块可解析性，缺工具明确SKIP。此环境运行方式：`NODE_PATH=/workspace/browser-tools/node_modules /workspace/sim2act-pb-venv/bin/pytest tests/test_registered_run_generation_http.py::test_real_http_dom_generation_entry_and_lost_receipt -q --disable-warnings`。先前已运行命令使用当时绝对require，本次已改标准模块解析并按显式NODE_PATH复验。不能用此项证明Windows/原生浏览器。启动的本地uvicorn线程在finally停止/join。

## 未测与边界

本轮SQLite实际HTTP/冷Store/现worker与HTTP-backed jsdom已测；PostgreSQL并发、Windows原生、native浏览器截图与布局未测。共享既有目标app runtime，不是独立新授权域；撤权默认拒绝来源/目标/cached访问。来源只支持已核验初始registered CSV内部AppRun，不接受普通F1 PARTIAL、agent、递归来源或语义推断。模板由可信来源自动选择和生成，但不是模型自主归纳；模型预算0不变。正式发布/部署关闭；无新Principal/Grant/表/DDL、无provider请求。父线程待统一审查/commit和决定进一步验证。

## 最小私有名称清理修复（父线程复核发现）

父线程发现clearRegisteredExtraction虽清来源proof/目标选择，但保留了用户编辑的名称。现在每次清理恢复固定默认“从成功任务保存的汇总”，因此项目/app/instance/source/identity重新打开流程触发清理时不会把上一主体名称带入新表单。同source、同Run version轮询不会触发清理，当前编辑仍保留；请求key仍由token/project/iid/rid/version及body配置共同锚定，未更改key范围或手动恢复策略。

真实HTTP-backed jsdom新增两项：同source同version回读保留`Private prior-owner name`；来源切到另一个已有app且旧options迟到后，name恢复默认。当前总16检查。显式NODE_PATH focused命令实测1PASS/1旧warning/10.17秒；Node语法检查与diff-check通过。此修复未提交；已请求现有只读审核者专项复核。未新增native/visual/Windows/LIVE/CI证据。

修复后SHA256：
- `src/sim2act/web/internal.js`: `e67cd987d3559031f3e1280098362de9d027201a46ad1c9bf85aea6f995bfc19`
- `tests/registered_run_generation_dom.cjs`: `29e27c7db7d18c5652012fbbe8c85bb424df51b8999affb47ec9da713edff01e`
- `tests/test_registered_run_generation_http.py`: `631d4718cc7293ba495b2c624f4e52363b735416785c2fc1de3d6cd2d4b44006`

只读审核者 `/root/readonly_boundary_review` 已批准上述最小清理改动，并核对三文件hash全一致；确认clear覆盖内部视图/实例/失去内容/来源版本切换，同源同版保留编辑，原请求key范围未改。审核者未再次运行专项，实测归属上述开发验证。
