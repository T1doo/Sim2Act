# P-B 连续保存与目录复用：本轮原始证据

基线 `4855d5250fd576bb04f81faad22ca6a4ccdfcbdd`，唯一仓库写入者 root，分支 `dev/natural-pb-reuse-guide-20261016`。实现、三个新测试文件及初始说明冻结于 `e039e0e3ec3add3e23eeb75fc9085ea017780c6d`。其后仅归档证据和更新说明；544 个生产/测试/构建文件的原始 SHA256 映射见 [冻结映射](pb-guide-freeze-source-hashes.json)，最终逐项核对另存。未读取或修改旧满盘实例、旧 bundle 或共享文件。

本轮先核对已有 P-B 来源、review/extract/by-key 与内部版本控制器，仅改 app.js 和 internal.js。没有新 executor、后端协议、Grant 类型或模型批准。可见链为成功成果 → 准备自己的材料与 Goal → 原精确审阅/确认提取 → 原内部版本/独立实例 → 统一目录 → 另一份材料的 per-use 明确运行和同 Run 结果/人工入口。产品行为见 [说明](../../F2/NaturalPBProductFlow20261016.md)。

[实际命令和选择器](commands.json)、[环境](execution-environment.json)、[冻结预检](freeze-preflight.json)、[收集清单](pb-guide-final-collection.log) 保留原始范围。测试使用当前环境的锁定依赖、合成数据、生产页面脚本、JSDOM、实际 TestClient HTTP、SQLite 和真实 Worker + httpx.MockTransport。页面可见性断言不等于原生浏览器视觉验收。

三批主测试在同一 e039 冻结并行执行；最终结果和逐节点分母见同目录 final-verification.json 与 JUnit。受影响首次创建完整模块 4 项，共享入口 5 项；新 P-B 产品模块 2 项。独审重复运行其中一个导航节点，单列而不重复累计。

| 冻结后实际范围 | 结果 | 耗时 |
| --- | --- | --- |
| 新 P-B 产品模块完整 2 项 | 2 PASS / 0 FAIL / 0 SKIP | 575.45 秒 |
| 原首次创建模块完整 4 项 | 4 PASS / 0 FAIL / 0 SKIP | 357.60 秒 |
| 共享准备、目录分类及 Goal 入口 5 项 | 5 PASS / 0 FAIL / 0 SKIP | 41.75 秒 |

共 **11 个唯一节点 PASS**，没有跳过。P-B 完整 HTTP/Worker 页面正例实际 63 checks、68 次可见交互、3 次页面启动、63 个实际资源加载 hash；主模块另有完整 DOM/合成 API 导航 38 checks。原首次创建正例 54 checks、61 次交互、3 次启动、63 个资源加载 hash。P-B 来源与新逐次 Run 均一次 claim 实际 SUCCEEDED，没有使用该夹具的重取分支。生成 3 次、来源 Worker 1 次、新 P-B Worker 1 次均为合成 MockTransport 请求；新 runtime wire 只有新材料，没有 desk lamp/garden sensor 旧材料内容。全部真实模型请求 0。

P-B 重正例仅预置一个成功 P-A 来源。新目标材料/Goal 由真实页面分别保存，不预置目标或 P-B 应用；编辑稳定节点 ID 后，双击确认只有一次实际接受的提取 POST。合成丢失该实际 201 响应后，本页保留冻结意图，只按原 key GET 恢复。版本、实例、目录返回及后续新材料运行均单独明确点击。新 P-B 实例此前没有成果，后续材料产生其首次 v1；这不证明已有 P-B v1 保留后产生 v2。

来源保留断言逐行比较原 app、Release、instance、typed-v1、artifact 资源行，并保留原 Goal/version 行；未逐字比较所有原 runs/internal_app_runs/attempts/events，不将 source_run 字段误作全部旧账本比对。人工入口核对新材料/Goal/Run/结果版本并保留 PENDING，没有实际人工决定或真实语义验收。结尾通过正常 API 撤销精确原来源 READ，随后新的来源提取检查和 P-B app 读取拒绝，旧来源页面打开拒绝并清除受保护正文；没有重发提取或新 Run。

独立审查见 [最终有限报告](f2-pb-continuous-extraction-final-e039-review.md)。同字节实际 21 项隔离真实函数检查，以及独立完整 DOM/合成 API 的 1 PASS、38 checks、10.29 秒；原始 [XML](f2-pb-independent-e039-nav-correct.xml)、[JSON](independent-navigation.json)、[日志](f2-pb-independent-e039-nav-correct.log)。其范围无剩余未修阻断，不提前替代主线程的 HTTP/Worker 结果。

保留了 WIP 三项问题和修复证据：配置 GET 等待后与默认运行意图竞争、准备返回时缺 instance、打开已存草案失败后残留步骤状态。最终分别重新核 pending/unknown/busy、先核 instance 存在、要求完整 historyReady 并仅收尾自己的当前向导。源码和测试都包含修复。新 P-B 配置 gate 仅是 GET 预检，不能授予模型发送权限；实际后端仍要求既有 mock-only 条件和 MockTransport。

所有早期轮次单列，不计入冻结最终分母：navigation-wip1 的测试错误假设“编辑提示应为空”导致失败，修正为无旧 review/ack 后 wip2/wip3 通过；独审首个隔离夹具遗漏 appPreviewRequests 导致失败，修正后 21 checks 通过；独审第一次 pytest 节点拼写错误 RC4、0 selected，改正后实际 1 PASS。相关 JSON/log/XML 和 WIP 报告均保留，未覆盖或把零选中计通过。WIP 共享 2/6 项及早期 32-check 导航也不累计到最终结果。

未运行：全仓测试、旧多夹具 P-A/P-B UI/恢复矩阵（包括 test_pb_natural_spec_ui.py、test_pb_natural_uses_ui.py 完整模块）、Windows、原生浏览器、PG、远端 CI、真实模型/真实场景/真实人工语义、部署。Ruff 和 19 个生产 JS 语法检查另存；未把既有类型问题冒称全仓 mypy 通过。旧多历史 fixture heartbeat/SQLite 锁问题保持 OPEN_NOT_RETESTED；旧满盘环境最后独审未落盘的证据缺口没有补回。提取 pending 仍仅本页 Map，不宣称冷页自动发现未知提取请求或来源退休许可。

SHA256SUMS 包含本目录除自身外的全部归档文件；最终远端精确 SHA、主分支/基线不变和工作区差异在推送后另外核对。
