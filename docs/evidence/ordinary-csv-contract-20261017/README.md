# 有限普通任务：CSV精确汇总与完整MD事前验收

本次从已接受的 `eff2b160aefd0c5caf1c28e47df7fededd50b573` 创建普通开发分支 `dev/ordinary-csv-contract-20261017`。新增一个用户明确选择的完整纵切：在普通任务页选择CSV材料与数值列，先保存并展示事前合同，再明确确认后台执行，最后在同一Run查看、下载原始MD。保留独立自然语言Goal草稿；未把任意自然语言目标缩成合计正确，也未追认旧Run。

执行与后端检查源为 `599052cbadae21b4a7ba8738fb889ea970c11e84`；最终产品源为 `402f3eb5f80be73ddc57d4bb6123fdd6157726e0`。两者严格只差新页面PASS展示谓词的一行及对应driver的两项纯负断言；其余全部tracked文件逐字相同。后续提交仅包含本说明与原始证据归档。交付SHA和实际远端状态由最终回复及工作区的交付核对JSON提供。

## 原方案与实际缺口

`docs/平台产品设计.md` 的GoalSpec/CheckSpec、编译预检/冻结、durable Run、权限交集、回执以及第11节验收原则要求先冻结验收，独立数值计算与语义人工判断分开。现有普通任务已有提交、Worker、三注册工具、durable operations/intents/local_effects、结果原文及下载能力，但任意Goal仍是PARTIAL/NOT_RUN。原固定合成checker只覆盖自己的精确固定目标，CSV DAG也已有独立目录使用路径；本次不重造这些能力。

基线实际调用新入口返回404。该基线为eff2b160加初始typed模型声明及初始测试，尚无新API/控制器/Worker/UI接线；`raw/author/baseline/tracked-source.patch`与初始测试可准确复现这个有限基线，不能声称所有产品字节等于eff2b160。

## 可见行为与安全边界

- 新入口明确名为“CSV精确汇总并保存完整MD报告”。选定材料、选列后准备合同，Run持久保存为WAITING_APPROVAL；确认前没有operation、成果文件或模型请求。
- 冻结来源ID、revision1与SHA-256、列、UTF-8/无BOM/严格CSV/空行和记录规则、有限十进制精确相加规则、预期记录数/合计、完整MD原文/hash/格式、注册工具版本及定义fingerprint、保存与逐字回读要求。拒绝超过原CSV/8000字符文本/32768字节工具参数JSON界限的完整报告，绝不截断后称完整。
- 用户另行勾选并确认精确Run版本与contract fingerprint。沿用原submit_tx、Run、Worker与resource.read→data.aggregate_csv→artifact.save_text，固定同Run call_id，复用原VERIFIED回执；未知结果停止，不自动重发。未新增executor、表、依赖或Grant策略；保存成果仍按已有save_text派生读取授权。
- 确认、每步分派/事务末及最终成功提交重新检查当前权限、来源、版本、lease与原/当前较小截止时间。执行Worker收紧工具额度即拒绝；heartbeat使用原Store入口并限原/当前截止。全局Limits.max_requests最小值保持1，新合同另行冻结0请求，原reserve入口禁止此合同做模型请求或预留。
- 独立checker重新用原有integer-scaled精确oracle核查记录数/合计，逐项核对三原工具intent/fingerprint/receipt、来源内容/hash、同Run保存效果/local_effect、资源scope/MD格式/hash及完整原文回读。最终提交与冷inspect均再次核查。只有这个明确有限合同能SUCCEEDED/PASS_CSV_REPORT_CONTRACT；general semantic NOT_RUN、owner PENDING、正式发布关闭。
- 页面后台刷新同一来源版本保留已显式选列；来源改变则失效。准备与确认各自冻结原key/body，未知回执只能手动恢复原请求。账号连接、项目选择、Run选择、工作区代次围栏隔离迟到回调。结果复用已有同Run授权回读/下载；失败或取消后已验证保存的成果仍可按原权限显示，不称无副作用。
- 旧fixed-csv-goal-acceptance.v1 checker与其边界、旧普通任意Goal的PARTIAL/NOT_RUN、安全权限策略均未扩展。

## 已实际执行的范围

完整冻结599批次，作者与独审各运行同一28例：

1. 新路径22例：19项API/合同/检查边界及3项完整服务页面链路。包含确认前0效果、精确同键确认、冷NoModel Worker、不同列/Unicode/超过JS精度/小数抵消/空输入、版本/fingerprint/来源变化/实际save授权撤回/取消/他人账号/截止拒绝、错误合计回执/保存内容损坏/合同移除的冷拒绝、不重写成果、原保存工具与oracle上界、当前Worker额度收紧、旧Run不可追认及禁止模型reserve。
2. 原普通任务结果4项直接回归：正常原文交付、账号/项目/Run/工作区迟到隔离、真实fixture成果读取Grant撤回、工作区返回后立即查看下载；仍使用scripted Mock并保持PARTIAL/NOT_RUN。
3. 原固定checker的2项既有精确目标/冷读取回归；复用原MockTransport与正常Worker，保留general NOT_RUN/owner PENDING。

作者RC0，28PASS/0FAIL/0ERROR/0SKIP，JUnit82.237s；独审RC0，28PASS，JUnit76.911s。599批次有7个完整页面例、100个页面断言、384条实际页面API请求、154个实际服务资产hash。新CSV功能各例使用NoModel，attempt/reservation为0；该批18个模型尝试全部来自直接回归（16个scripted ordinary Mock+2个原fixed MockTransport），真实模型0。

599动态全绿后，独审仍指出页面PASS投影在双方fingerprint或checker均缺失时可能空值相等，这是有限展示阻断，不能用动态全绿掩盖。最终402要求双方64hex指纹且相等、明确checker版本，并在每个已有新页面例增加两个纯投影负断言。服务器checker与权限未变。

402最终只重复受影响3条完整新页面链路，作者RC0/3PASS/20.585s，独审RC0/3PASS/16.802s；各44个页面断言、126条实际页面API请求、66个实际服务资产hash及3个原MD Blob捕获，0模型请求。普通后台refresh显式执行，确保同源选列不被清空。双缺fingerprint/checker的两断言仅在实际Run克隆上纯计算，不冒充实际服务器篡改或额外执行。

其余25条未重跑节点保留599执行SHA，绝不改签为402通过；599→402全仓diff及独审delta原件证明相关后端、Python测试、原回归driver等逐字相同。作者两个冻结批次各571个tracked源/测试文件before/after与其Git blob一致；独审各125个相关tracked文件一致。Ruff（所有改动Python）、两产品JS语法与diff检查均通过。

## 原始证据与局限

`originals-manifest.json`逐项记录原件路径、归档路径、字节数和SHA-256；SQLite及较大文件采用确定性gzip，解压字节与原件一致。`checksums.sha256`覆盖归档文件。`raw/author/`保留基线及全部探索失败/通过，不覆盖失败；`exploratory-runs.json`明确其未冻结源与不适用的验收信用。早期API失败曾在已提交工具效果后触发NameError，其DB保留，不称0效果。首次页面失败是未初始渲染确认按钮禁用态，修复后复验。探索过程中的HTTP400误预期、未冻结源变化均如实保留。

`raw/independent-599/`是28例预验证与展示BLOCK原件；`raw/independent-402/`是最终有限接受与3页复验原件。完整命令、RC、日志、XML、source before/after/delta、合成SQLite、请求/回执JSON及原MD均可检查。scope-summary中一个看似legacy SUCCEEDED是“移除合同”负例刻意改写的坏snapshot，实际冷读取被拒绝，绝不代表任意普通Goal被接受；见scope-summary-explanation.json。

仅实际运行Linux/Python3.12/SQLite test_only、FastAPI TestClient真实ASGI、本页服务资产、Node/JSDOM与Blob捕获；未运行原生浏览器/Windows、PostgreSQL、真实模型、真实语义/真实场景、人工语义签收、远端CI、部署或正式发布。未扩展相邻故障/恢复矩阵。旧满盘环境未访问；其最后独审报告未落盘的证据缺口仍未补回。本环境为唯一写入者，独审只读；17条受保护远端引用保持原值。
