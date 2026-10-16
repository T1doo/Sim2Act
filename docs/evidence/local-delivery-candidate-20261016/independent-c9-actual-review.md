# v2限定本地候选：实际安装、完整链及冷读回执独立补充审查

执行源：c9e9f3fc9787350d1e7997860234694b270a6a7f。对应zip SHA256 082d1e4dae16e0dece011f719fe22a9142b195f4464d46310c4ec44539f65701；wheel SHA256 824157288bc83d3e8cff7d0e0681d9c93d5038534aa590b47f2504166711e9b0。

有限结论：根线程实际用v2包、新venv、新目录完成限定prepare及独立进程verify（根确认均exit0）；本审查者已只读复核原回执、安装文件和持久数据库，支持将**c9限定合成mock候选**作为本地工程交付。没有剩余本范围阻断。并非真实模型、真实语义、普通PG、Windows或原生浏览器验收，不宣称一般自然任务可靠性。

此补充与/tmp/f2-local-candidate-final-c9e9f3fc-review.md分开保存。先前该报告把完整链记为待完成是当时准确状态；本报告基于随后实际原件补充，不改写之前证据。

## 实际链及持久结果

只读原目录：/workspace/local-candidate-clean-install-v2/Sim2Act-local-candidate/synthetic-demo。demo-receipt与worker/mock/http-receipts、stdout相互一致：

- CSV Run run_5a49abab3e4c403aae77524f8520f019 SUCCEEDED，sum30，result_version1。
- 自然生成Run run_9a3c7f4f404048fe9c9ca2847cf8cc65 PARTIAL，3条固定MockTransport响应，完成显式候选确认并保存P-A/Release/instance。
- P-A原保存材料+Goal直接实例Run run_aaba00f24767462abc8ba2e0d2eb340e SUCCEEDED，1条固定mock，持久成果v1。同Run人工入口owner PENDING、semantic NOT_RUN。
- 从该成功P-A成果按现有options/review/extraction合同保存P-B/Release/instance，第三材料+Goal明确per-use review/commit，Run run_9fb3f55e16f5462089eb93dec4defff7 SUCCEEDED，1条固定mock，持久成果v1。同Run人工入口仍PENDING/NOT_RUN。

共4个Worker一次驱动，各一次CLAIMED/fence1；46条prepare HTTP回执均200/201/202，P-A普通实例提交和P-B逐次提交各重复原intent但同Run。5条模型响应全部httpx.MockTransport，真实模型请求0，formal_publication false。receipt明确pa_new_material_per_use=NOT_RUN_IN_THIS_CANDIDATE；本轮没有调用/验证P-A新材料per-use。

## 独立读取的增强核对

本审查者只用Python标准库sqlite3的mode=ro连接和query_only=ON查询已完成合成库，不导入产品、不启动Worker/服务器、不发送模型或重放Run：

1. 4个实际runs行状态、fence、worker_id与回执完全一致，events各恰一条CLAIMED。
2. actual Attempt数依次0/3/1/1，全部MOCK且request/response model intern-s2；生成Attempt为RECEIVED，两个runtime Attempt为VERIFIED，符合现有不同阶段合同。
3. CSV/P-A/P-B internal_app_runs均SUCCEEDED/result_version1；自然两个实例typed data仅v1。两份artifact资源实际content SHA匹配receipt，内置owner_acceptance=PENDING、semantic_goal_acceptance=NOT_RUN。
4. 已安装venv中的113产品文件逐字等同该wheel，安装包没有额外产品文件（排除Python正常__pycache__）；解包demo脚本与固定fixture逐字匹配c9 Git冻结。runtime-origin另记录fresh_venv/来自wheel/checkout src不在sys.path；pip check无损坏依赖。
5. 独立查询前后DB文件SHA均82d109a96e5278e44cf6b5c6a752d686889bcaeafd178bf34182778d992dc9c9，证明本次只读核查没有写库。这个hash相等不替代根cold verify的前后全库行比较。

第一轮附加只读probe错误假设所有Attempt.status应SUCCEEDED，实际查询显示生成RECEIVED/runtime VERIFIED。已按正式阶段合同修正探针并保留此说明；这是审查辅助断言错误，不是产品测试FAIL，不涉及修改产品/原fixture、重跑Worker或改变实际回执。

## 独立进程冷读与只读serve

根demo-verify.log及cold-read-receipt实际PASS：cold_process=true，已有结果3份，workers_started=0、model_requests=0，原程序snapshot(meta.sorted_tables)前后持久行比较一致。该结论来自实际冷读程序受审代码与原回执；本审查者没有再次启动verify或凭当前状态虚构过去的before快照。

serve-smoke.json实际PASS：普通首页、app.js/use.js、项目/metadata目录、CSV详情和P-A/P-B同Run人工查看共8次GET200；POST /api/projects返回405；自有serve收到SIGINT后exit0，workers_started/real_model_requests均0。serve.log显示loopback127.0.0.1、公开合成身份及只读提示。native_browser明确NOT_RUN，因此HTTP可见性不等于实际浏览器逐按钮交互。

## 可复核原件

独立核验脚本：/tmp/f2-review-local-candidate-c9-actual-receipts.py，SHA256 ef2d6fa6a0a567e12b098140f6fce8567a93f10f517deccacdd8a2933177a68f。
独立proof：/tmp/f2-local-candidate-c9-actual-receipt-independent-proof.json，记录所有12原件SHA256及DB只读结果。

原件位于/workspace/local-candidate-clean-install-v2：synthetic-demo下demo/worker/mock/http/cold-read五份receipt，根目录demo-prepare.log、demo-verify.log、runtime-origin.json、pip-check.log、serve-smoke.json/.log、serve.log。

主要原件hash：demo-receipt d10df602b345f79d877a89f38cb278ec8afc76d9a5930edf90177fdfea9fb959；cold-read-receipt c64c07f48db7186e0adf663ea65e42e8d1c65086c43de86702fbedb4d3e3c91e；serve-smoke b027a6e519903816920cfcb469e7bf323199c0a1af4af6b82d2c7a90caf3b08a。

## 保留边界

前包0f0819a6完整prepare失败及原Run/目录/proof/log保持FAIL，未重放；本次成功只属于c9收窄链，不是该失败的产品修复。P-A新材料逐次使用在本候选NOT_RUN。旧F9具体时序仍未复现。前轮45PASS/1FAIL、定向2PASS和独立9PASS保持分期；自然双Run未触发恢复的事实不变，不合并为单次全绿。

本补充只读核回执，没有再次执行自然链、Worker、模型、锁矩阵、PG、Windows、原生浏览器、远端CI或部署。下一步文档/证据归档和普通分支推送不改变本次冻结执行源；交付包必须保留已核SHA及限定说明，不把本地合成库、venv、build.log或私人配置随包分享。
