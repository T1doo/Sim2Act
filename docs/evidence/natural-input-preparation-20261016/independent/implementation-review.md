# 应用内材料与 Goal 准备：实现只读独审

2026-10-16 UTC。仓库基线 `5d6afe2fd23f6fbc059d5243323a071030e5f36d`；首实现冻结 `044144c9344206b1200fc48091e59e264e79dbdf`；最终静审 HEAD `a56db717d34b9425f7701ee971e5214678e24b5d`，工作区干净。a56 产品字节与 `9cac89c998731dc0983d9e8daa005e795f13c62d` 相同，已用 `git diff --exit-code 9cac..a56 -- src` 确认。根为唯一仓库写入者；本独审无仓库改动，无真实模型/Worker/重测试运行。源码静态命令 `git diff --check 5d6..a56` 及 app.js/internal.js 的 `node --check` 实际通过；另独立轻 probe 实际结果见下节。

## 已核实现

1. `pb-use-prepare` 只在原 per-use 当前且无 busy/旧未知请求时启动。原 `resource-form` 和 `goal-card-form` 是移动单一 DOM node，记录位置锚点、直接子节点隐藏状态及各控件 disabled 状态；结束准备恢复位置，不克隆重复 ID。材料/Goal 公共保存 API 和原项目授权路径复用。
2. `naturalPreparationCurrent` 捕获身份 token、连接代际、项目、工作区、engineering view/appSelectionGeneration、原 instance object 和 instanceGeneration。返回时仅允许原代际或本次预期 +1；内部实例选择换到别的 id/view 会清准备。所有保存采用及返回关键 await 后均核 current；已保存但导航后失效不自动填新实例。
3. 材料预校验遵守 TXT/MD、UTF-8 2048字节、40 splitlines、非空白及 Unicode C 类限制（LF/CR/TAB 例外）；保留共享通用 32768 入口，inline 隐藏通用尺寸说明。文件仅本页读取/编辑，显式保存才 POST。
4. 材料保存复用 `resourceSaveRequests` 的 saving/unknown/accepted；未知不会自动重新 POST。接受后进入 material-saved，只有独立下一步才打开 Goal。Goal resource_refs 固定一份刚保存材料；另建 `naturalPreparationGoalRequests` 保存未知锁，POST 无幂等键时禁止自动重发；旧回执/列表只读核对，不凭标题/相同内容自动认领。
5. 原 Goal handler 的项目页保存收尾仍调用 showGoalCard；inline 分支走独立收尾，避免 clearApp 拆实例。新 Goal 精确读取其 id/project/current version1/fingerprint/content/ref，返回时再次 GET Goal 核版本、指纹与唯一材料。
6. 返回显式 fresh GET 应用并核家族/草案 fingerprint，重开原 iid，核 Release ID/fingerprint、实例 revision/data_version 均未变；只回填原 per-use 材料/Goal 选择，dispatch change 清旧 review/ack/proof，仍需点击原 preview、阅读后显式确认提交。
7. 准备、保存材料、保存 Goal、返回均无 Run POST 或模型调用；原 per-use 受理控制器、permission gate、Release/版本、pbUsePending、engineeringPending、durable Run intent 和执行后端未改。新普通 Goal 请求 Map 是页面内锁，不能据此宣称跨冷页面持久幂等或新后端恢复协议。

## 发现与修正

### 产品缺陷：已修正

044 的材料保存后由 `naturalPreparationRender` 禁用表单，但每轮后台 refresh 直接调用原 `renderResourceMaterial` 会重新启用已保存材料字段。用户可编辑可见文本，而提交因 step!==material 静默返回，Goalnext 仍绑旧 p.material，导致可见输入与实际绑定不一致。

已即时报根；9cac 将 preparation 的非 material 阶段/Goal pending 锁统一纳入 `renderResourceMaterial`，覆盖后台刷新与其它共享调用入口。静审确认修正位置正确，不仅依靠 panel 收尾再次禁用。根已另安排轻 renderer 回归，结果未由本报告冒充实际运行。

### 新测试合同错误：已修正

044/9cac 的 `tests/test_natural_input_preparation.py` saved-input-checkpoint 访问 `goal_cards.content`，但内容实际在 `goal_card_versions.snapshot.content`，会产生 KeyError。已报根；a56 只读复核确认改为同 card_id/version1 的版本行，核 content.resource_refs 和 resource_snapshots 的唯一材料，不扩生产表/schema。首轮 KeyError/中断日志应留存，不能当作新产品保存失败或通过证据。

同时核对 a56 的旧资源 guards `x.txt -> x.bin` 调整：基线共享导入器已经支持 TXT，旧断言要求 x.txt 被拒绝与实现合同矛盾；改无效扩展保留拒绝断言符合原合同，不是降低产品校验。

## 独立实际轻验证

```text
/workspace/sim2act-venv/bin/python -m pytest -q tests/test_natural_input_preparation.py::test_natural_preparation_navigation_synthesized_api --basetemp=/tmp/f2-preparation-independent-a56 --junitxml=/tmp/f2-preparation-independent-a56.xml
```

实际 1 passed、0 failed、0 skipped，7.42 秒，一条 Starlette TestClient 弃用警告；**39 条检查 PASS**。XML `/tmp/f2-preparation-independent-a56.xml` SHA256 `06cdc5d1237aa37f390e7650b155304feaddd5aced605d84bc90804e1902db26`；原始 JSON `/tmp/f2-preparation-independent-a56/test_natural_preparation_navig0/navigation.json` SHA256 `59381d0738ff784a4c25e595a9d3e292fc486b96b8f72c4289b4986e70320514`。

分类为实际 index/app/internal/use/owner 脚本、合成 API/保存 view、无 HTTP/Worker/真实模型/原生浏览器。实际涵盖材料/Goal 保存后项目和身份 ABA 的迟到接受隔离、Goal unknown 不重 POST 且 GET 不认领相似卡、显式 reset、共享表单原 node/父节点/accept/格式与通用资源选择控件恢复、后台 renderer 保持已保存材料禁用、恢复后原 CSV 保存及通用 Goal 保存路径、冷页零写。实例/Release/revision/data_version 精确返回与实例导航守卫另经静审，不能把此合成 probe 夸大为实际 HTTP/Worker 证明。

最终实际加载产品 hash：app.js `5aa09f95f5ec84aaea138e331fb724fed2d29cfa2dc21853238bb9085dee6f0a`；internal.js `8ca31d748d5a2ff60210db3f6a1dcb897af76ad5b9acb9e9ebb261facfc489bf`。JSON 含五资源 hash，pytest wrapper 已与当前源码逐个核对。

## 当前结论与证据边界

a56 在本有限审查范围内无剩余必须修问题：单一共享 form 复原、导航 pending 隔离、无模型/自动 Run 路径及原 per-use 安全边界均已核。Goal 请求 Map 是页面内锁；保存 unknown 和 accepted 不自动重发/跨上下文采用。字段恢复主要由记录的 controls 状态恢复；代码随后把 goal-card-resources.disabled 设 false，符合当前可达通用表单原状态，不能额外据此声称任意外部注入 disabled 状态均逐字恢复。

两条 PA/PB 正常真实 HTTP/JSDOM/mock Worker 回执仍由根线程实际执行并另行归档，本独审没有独立运行或在本报告中冒称已通过。根提及的 18 项共享回归也应由其原 XML/log 支持，此报告不替代。本人未跑旧矩阵或无关广审。

必须在最终证据注明实际 served assets 的 hash：测试在 044 后开启而 9cac 修正文源码，不能仅凭最初计划 SHA 认定页面加载了哪版。不同冻结/批次分别报告，不拼装全绿。

不重复旧恢复矩阵；真实模型、真实材料/人工语义、PG、Windows、远端 CI 和部署未执行。旧多历史心跳数据库锁失败没有被本轮修复或解决的结论。
