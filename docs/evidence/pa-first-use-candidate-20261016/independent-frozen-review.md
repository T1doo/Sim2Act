# P-A逐次材料演示及普通Worker生命周期冻结独审

审查源fc69c863f57f0cdf9a8dbfeaeb5fdc567e42c675，基线e7dcdb4ff25e5765be5dc34a4edc72ecba1929bc。工作区干净；仅脚本、固定fixture、指南和新轻测变动。src与e7、986799d及原0f逐字不变；没有产品executor/Grant、权限、版本、lease/fence/clock/预算或心跳修改。

有限结论：冻结静态审查、独立21项轻测及实际新包同源核验无剩余阻断。**新安装包prepare-pa首新材料v1/同实例第二新材料v2及独立冷verify仍需根实际完成并核原件，轻测不替代这条新执行链。**旧prepare的P-A原材料/P-B范围本轮未重跑，不改签既往证据。

## 生命周期及隔离

serve_accepted_run只调用普通Worker.once/Store.claim，按原worker.main一秒服务间隔，固定原accepted id/owner/project/created_at/deadline。True/False仅进度，目标实际SUCCEEDED/PARTIAL才结束服务；失败、阻塞/未知、异常、时间或stop即退出，finally置worker.stop。没有重发受理、换key/Run、resume、清unknown、人工改状态或扩大等待预算。每轮原接受时钟与前后metadata落盘，所有原CLAIMED/WORKER_LOST/RECONCILED和fence/claim_count公开。原Store.claim若合法回收可多claim，文档明确不再限定一次claim，不把它称旧故障已修。

运行中仅读取已知合成Run的调度标量；完整HTTP证明只在终态后读取，避免新增全证明writer轮询。原在途Worker的授权、lease和deadline仍由产品guard裁决，服务没有获得延长它们的能力。

WIP发现的具体旁路风险已修：每轮前后检查非target QUEUED/RUNNING/PAUSE_REQUESTED/CANCEL_REQUESTED active行，核此service实际worker_id对应Run ID只能是target；完成时须确实领过target。finally保留target全部claim/recovery事件、本service全CLAIMED ledger和last_observation。新增实际CSV双queued负例证明最老非target存在时两个Run均仍QUEUED且无CLAIMED，不执行/重排其他工作。此隔离只适用于脚本自己新建的合成库，非通用生产调度安全机制。

## P-A新材料范围与保留

prepare-pa与旧prepare分明。新路径保留原0f CSV/生成前缀，在空P-A实例上先pa_use(原0f材料/Goal/recipe、base0)经原pa-use-review/run，再另一个固定pb_use材料仍经P-A逐次使用，独立原intent重复提交核同Run；预期同app/Release/instance v1/v2。3生成+2runtime固定mock，总5，零真实模型。Mock handler每次use仅允许一条响应，不会通过重复模型返回掩盖未知结果。

第二Run前捕获首typed完整行，之后核versions[1,2]且首行完全相同，receipt保存两rowhash；coldverify核两artifacthash/版本/同Runowner PENDING、两typed rowhash及前后全库持久行不变。这里是受审代码合同，不预先宣称未结束的实际新链通过。

## 独立实际轻测

命令：/workspace/sim2act-venv/bin/python -m pytest -q tests/test_local_candidate_demo.py tests/test_local_candidate_worker_service.py --basetemp=/tmp/f2-pa-service-independent-fc69c863 --junitxml=/tmp/f2-pa-service-independent-fc69c863.xml。

实际21PASS、0FAIL/ERROR/SKIP、RC0，终端4.39秒，精确JUnit时间见manifest。原10项目录/环境/loopback边界加新11项：受控True→RUNNING/False→第二实际终态、合成fence变化如实记录、五类阻塞/失败停止、原deadline停止、不接受改变原clock、异常不重启、实际CSV普通服务/真实claim、实际两个queued隔离拒绝。

受控状态/clock案例仅验证脚本合同，不是自然失租/恢复复现。实际CSV案例无自然模型、无强制锁或时钟故障。已有FastAPI/Starlette弃用warning保留，未改依赖。

原件：/tmp/f2-pa-service-independent-fc69c863.xml 和 .log；源文件hash、原件hash及JUnit原始属性在/tmp/f2-pa-service-independent-fc69c863-review-manifest.json。

## 新包只读核验

/workspace/pa-use-running-candidate-artifacts/Sim2Act-local-candidate-fc69c863f57f.zip：134条目/133manifest，131Git来源文件逐字匹配fc；wheel113产品文件与包内src逐字相同。无缺漏、额外文件、重复或越界路径/link，不含私有配置、DB、日志、tests、历史evidence、venv或node_modules；build.log仍在载荷外。

zip SHA256 0ff78bc7330bcbbd5cc2a9fff76bb3cd2d2cd4e9ec37a3a0e1873acd50c74507。
wheel SHA256 3f7b7b527dfdf3dca64c2953daf61464dbbd259278287b8c95fa89f22bb37a0f。
manifest SHA256 6dda3942d9e6f20d6c89fa8b5444262362912159887301aa23563eab8fb35993。
只读proof：/tmp/f2-pa-service-independent-fc69c863-package-proof.json。未解压安装或执行包。

## 因果及执行边界

原0f FAIL及RUNNING/errornull最初异常未知仍保留；精确原前缀一次新基线自然PASS/Worker.once22.479秒只证明该路径能成功，没有复现旧失租。本次是候选服务生命周期与恢复P-A新材料演示范围，不是生产lease/guard修复。旧F9时序未复现；旧45P1F、定向2P、独立9P和自然双Run未触发恢复继续分列。

本审查者没有新跑自然/Worker重链、旧Run、锁恢复矩阵、真实模型/凭据探测、PG、Windows、原生浏览器、远端CI或部署。源码轻测通过后仍须实际新安装prepare-pa/v1v2/冷读原件，才能签本次可用候选；不以旧c9包或另一条prepare范围替代。
