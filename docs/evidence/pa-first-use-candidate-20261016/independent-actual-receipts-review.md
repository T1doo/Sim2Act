# fc69候选：首次P-A新材料v1、同实例v2及冷读独立补充审查

实际执行源fc69c863f57f0cdf9a8dbfeaeb5fdc567e42c675。对应zip SHA256 0ff78bc7330bcbbd5cc2a9fff76bb3cd2d2cd4e9ec37a3a0e1873acd50c74507。

有限结论：新包、新venv、新合成目录prepare-pa实际完成，独立verify进程随后实际PASS（根确认两进程exit0）；本审查者只读核原回执、实际安装字节和数据库，支持签收**本次合成mock P-A两次新材料v1/v2及候选脚本生命周期**。没有本范围未修阻断。不签旧首次失租根因修复、自然恢复分支或普遍可靠性。

本报告补充/tmp/f2-pa-worker-service-final-fc69c863-review.md的静态/21轻测/包同源结论，后者当时将新自然链列PENDING保持原样。审查者没有再跑Worker、自然任务、原Run或恢复矩阵。

## 安装与实际Run

/workspace/pa-use-running-clean-install/Sim2Act-local-candidate为新包安装目录；runtime-origin记录Python3.12.14、fresh_venv、来自installed wheel、checkout src不在sys.path。独立逐字比较113个installed产品文件=wheel；unpacked demo脚本/fixture=fc Git冻结，无源码替换。

实际scenario PA_NEW_MATERIAL_TWICE：

- CSV run_d39435ce914b4246977b9fdac89318c9 SUCCEEDED，sum30/v1。
- 自然生成 run_2d73f756b6074bb6b150825b0c2c710a PARTIAL，3条固定mock，实际保存P-A/Release/空实例。
- 第一次新材料P-A run_97e4565fb73b46c2a2fddd1b5b40d795 SUCCEEDED，accepted pa_base_data_version=0，结果v1。
- 第二次另一材料P-A run_5f36e0ee795c4618974ac84077967b2e SUCCEEDED，accepted pa_base_data_version=1，结果v2。

两次均原pa-use-review/run、各新Goal版本1及独立原key，重复相同提交返回原Run。同app app_6cc805c165c3879cf7cf8e737d43c3d9、Release irelease_8c4724540a8f42d48480a25af36ddf31、instance iinstance_9cd6bc6cea5a2d13d87da77dee2f9915。没有执行原材料PA Run，也没有PB提取/执行旁链；旧prepare路径本轮不重验或改签。

4个实际Worker均1turn/1claim/fence1，无WORKER_LOST/RECONCILED。实际普通服务本轮没有重领，不能以合成unit的多turn/fence3序列冒称自然恢复通过。各turn原created_at+300秒截止完全一致且完成前未过期；两次PA服务调用分别25.6709秒、25.5924秒。它们含metadata读取开销，是本次观测，非延迟保证。

5模型响应全部MockTransport（3gen+2PA），真实请求0、formal_publication false。两成果owner PENDING、semantic NOT_RUN。

## 固定案例与持久保留的独立核查

使用sqlite3 mode=ro、query_only=ON读取已完成合成库，不导入产品或调用业务。实际runs/events/attempts/绑定/typed/artifact与回执相互一致：

- 4Run状态/owner/fence和各唯一CLAIMED吻合，Attempt数0/3/1/1；全部MOCK，生成RECEIVED/runtime VERIFIED。
- 第一source hash e58f3f30f484db701fb3189029be1328ab10cc848bbad2bdce42d42f51b91303，对应原0f pa_use；第二hash 014af6a56f7d21c5aa462f74439fc24973c5b50c48e86af64d39a5df6db52709，对应原0f pb_use。原source、recipe、两material完整内容/引用与0f JSON逐对象相同。
- 第一Goal内容与原0f失败Run已冻结Goal全部字段一致，只替换新库具体resource ID；第二按同一原模板、MOCK pb_use title、唯一新资源ref，完整goal/constraints/16unresolved/acceptance等一致。实际Goal id/version/fingerprint与对应review和accepted spec_goal相同。
- 当前typed版本恰[1,2]，rowhash逐项匹配prepare过程中在第二次写前捕获首行并核保留的receipt。v1 row SHA fc6ada3d72f6870da83678354350371cc85cad402126a0486c8a884610f48bbb；v2 f36f4284864c5d921ac4a8f6366f630151b8845841d31d52590a437f5a1ebc90。
- 两实际artifact content SHA与首次取得的receipt相同（v1 e441e20d36fb967139ff693744da32bb2bdd5a3ea39e9f0541c959e122682a62，v2 960376ee525216fb470be9be0f688c0b63aa8bb199988648f345ff907129c906），source_content确是各自材料；owner/semantic状态未替换。
- metadata只读查询前后DB文件SHA均32126639abe886f5e3b2f2af1cb76b0365c00890c9a7bbf71fcef18626ac3780。本hash不替代root冷verify的过去before全库行快照。

## 独立进程冷读与serve探针边界

verify-pa.log及cold-read-receipt实际PASS：cold_process=true、existing_results3（CSV+PAv1+PAv2）、persisted_rows_unchanged=true、workers_started/model_requests均0。受审代码逐项GET两artifact/版本/同Runowner，另核两typed rowhash和全meta表前后行相同；本审查者读取原件，不再次启动verify。

本轮首serve外部探针FAIL原件单列保留：15秒启动窗口内与cold检查重叠，Python仍在导入Pydantic/model_protocol；探针自己的SIGINT清理留下KeyboardInterrupt。没有进入API/Worker，不将它叫自然业务失败或因该探针修改业务预算。原件/workspace/pa-use-running-clean-install/serve.log和serve-smoke.log。根在cold退出后按相同15秒窗口仅一次串行重试；本报告落盘时未核重试最终原件，serve-retry结果另行补充，不假定通过。

## 旧失败及因果仍保留

old-failure-preservation.json记录原Run五表1runs/3events/0attempts/1operations/1bindings完全一致；原失败DB当前仍为bf2293cb3d5f96d9a054596d7e1cccd9905e1088f69620e9fc4e2989375b1d4c，与本审查者前次只读hash相同。原0f Run未重放、未改历史，FAIL继续保留。

精确0f新baseline本身一次22.479秒PASS、两BUSY+终态晚STALE而无fail_owned，只证明同链能够成功，没有自然复现最初异常。fc产品src未改，是候选脚本普通服务能力和恢复明确P-A演示范围；不宣称修复旧长事务/租约根因。旧F9时序仍未复现；前轮45P1F/定向2P/独立9P及自然双Run未触发恢复继续分期，不合并全绿。

## 独立原件

/tmp/f2-review-pa-service-fc69-actual-receipts.py（SHA827217009cd1d40bedff3bab0a6af8dcfb3bb3ea9262cff670a488c28914460a）只读核验脚本。
/tmp/f2-pa-service-fc69-actual-receipt-independent-proof.json（SHA6087bdb2b3d7e4538b6da518114d5dd96a85f54fbd7b6ffa5c22915f1e35ebd2）记录所有回执hash、实际DB核对及cold PASS。
/tmp/f2-pa-service-fc69-prepare-only-proof.json为冷读完成前PENDING时刻的独立记录，保持不改。

原件在/workspace/pa-use-running-clean-install：data下demo/worker/mock/http、四worker-service和cold-read；根目录prepare-pa.log、runtime-origin.json、verify-pa.log。旧保留证明位于/workspace/pa-use-running-investigation-20261016/old-failure-preservation.json。

未执行真实模型/凭据探测、Windows、PG、真实场景/人工语义验收、原生浏览器、远端CI、部署。以上均NOT_RUN；不得由本次合成mock结果推断通过。
