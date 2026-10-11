# P-A 确认页面、原键恢复与原始响应留存纠正

2026-10-11；基线 `dd26d5fec4643362f7bd0fe32b8a5d23001c3136`，分支 `dev/pa-text-goal-20261011`。根代理为唯一产品写入者，独审只读源代码并在另一进程执行测试。本次只修复已交付有限 TXT/MD P-A 的三个具体缺陷，没有扩大执行器、材料、预算或语义范围。完整合同见 [PATextGoalPlan](../../F2/PATextGoalPlan.md)。

## 原证明的纠正

旧轮 [README](../pa-text-goal-20261011/README.md) 中 4 场景/102 检查直接调用 `onclick`/`onsubmit`，没有检查祖先隐藏或真实表单约束。因此它们不能证明用户能操作确认→可见预览/实例链。确认/恢复只 `showApp`，当前 projects 工作区并未切到 apps，实际预览控件隐藏。本次撤回旧 102 检查对可见用户链的证明，不改写旧成功日志。

旧轮「已收到但拒绝的原 JSON 均保存」也超范围：原实现仅在 STARTED 的异常分支保存完整 raw，RECEIVED 后拒绝只剩 normalized message。此次明确撤回这一宽泛表述。旧轮其他后端测试仅按其实际节点/断言保留，不据此认领这两个缺口。

[old-evidence-integrity.json](old-evidence-integrity.json) 将旧轮全部 109 个已提交证据文件与 `dd26d5f` Git 原字节逐一比对，变化 0；历史 FAIL、脚本和原账本保留。

## 三项修复

1. [goal-application.js](../../../src/sim2act/web/goal-application.js) 在精确确认或原 key 恢复后，打开精确应用，再切到可见 apps 工作区、显示 app ID 并聚焦词输入。点击开始时冻结工作区/应用代次和完整目标编辑值；各异步阶段复核身份、项目、目标和该状态。新导航（含 A→B→A）、草稿编辑、别的目标或应用使迟到结果失去接管资格；只保存回执，不夺取当前页面/焦点。未保存目标草稿保留。[app.js](../../../src/sim2act/web/app.js) 核对返回的精确 app ID，并在内部实例读取完成后再次复核，普通应用入口保留默认行为。
2. POST 受理回执核对精确字段、状态、目标/版本/指纹及有限策略，其 Run ID 只是提示。首次必须通过原请求 key GET 证明完整保存目标和运行合同，再比对提示，成功后才提升到已核 Run ID。合法但错误 ID、对象 ID、错误状态/额外字段不污染后续恢复；只原 key GET，不再发送生成 POST。
3. [goal_applications.py](../../../src/sim2act/goal_applications.py) 将真实收到的完整 JSON 对象保存在受保护 Attempt，而非只保留 normalized message。新合同冻结 `protected-json32768.v1`：canonical ASCII JSON 上限 32768 字节；RECEIVED 保存原文，错误目标、二次 tools、目标不符、无效候选和修订均保留 finish_reason、tools、usage、model 与未知字段。公开事件只保存 hash，不公开 raw/私有 reasoning。读回核对 normalized message、usage、model、metadata 及独立 GA_RECEIVED hash；重签 raw/metadata、删档案/锚、删策略并重签合同均不通过。

超 32768 字节在解析/工具执行前拒绝，原文省略但保存 `OMITTED_OVERSIZE`、实际 canonical 字节数和 SHA256；非 JSON/没有真实响应不捏造原文。该上限针对解析后的完整 JSON 对象，不能声称保留上游原始 HTTP 字节或无限大小响应。旧无策略、无 raw 的合法记录按旧合同兼容，不补造历史缺失字段。

## 实际验证

[final.xml](final.xml) / [final.log](final.log)：66 PASS，0 FAIL / ERROR / SKIP，137.61 秒。包含原作者 13、既有故障 26、原响应留存 14、实际页面 13，重复执行不相加为唯一节点总数。

[final-ui/](final-ui/) 的 13 个场景共 488 断言，使用实际 SQLite、普通 Worker、IPC/进程内 HTTP、实际页面脚本和 CSS。每次动作以 DOM `.click()` 或输入事件发出，先核祖先 hidden/inert/aria-hidden、computed style、details 及有效 disabled；原生 required 表单约束也实际参与。它仍是 JSDOM，**不是原生浏览器或视觉验收**。

场景为 valid、lost-generation、lost-confirm、late-generation、3 种 poisoned acceptance、late-confirm 的导航/编辑/别的 app/别的 goal、late-app-read、late-internal-read。每场景均走可见目标入口→候选确认/恢复→可见预览→内部审批/版本→空实例→冷页面打开→新词 Beta 实际 Worker 结果→错误输入。空词被浏览器约束挡在 POST 前；浏览器允许但合同拒绝的前导空白词实际 FAILED，不追加数据。preview 后用户重新填写 Alpha 才申请内部版本，这是既有 preview 重绘清空样本后的实际用户步骤。每条链恰好一个生成 POST、一个精确确认 POST，恢复仅 GET；迟到场景保持当前选择、草稿及焦点，再以原 key 显式恢复正确应用。

14 个原响应回归包括 STARTED 的 usage/model/truncation/refusal、RECEIVED 的错误目标/二次 tools/目标不符/一次修订/两次无效候选、超大未知字段、三种档案/策略降级及 legacy 形状回读。完整未知字段与 private reasoning 仅在受保护 Attempt 中核对；公开 Run/外来身份响应没有该标记。旧未收到响应不捏造 raw 和 stale fence 的证据-only 留存由既有故障节点继续核验。

[shared-regression.xml](shared-regression.xml) / [shared-regression.log](shared-regression.log)：261 PASS、7 SKIP、0 FAIL / ERROR，163.16 秒；覆盖冻结合同、GoalCard、自然目标规划/确认、私有读取、内部生命周期/API、既有 agent 页面和持久 AppRun。7 个 SKIP 全部是需要明确隔离 PostgreSQL 应用角色的既有节点，精确原因见 [test-history.json](test-history.json)。本次两个作者包节点无重叠，合计 327 PASS / 7 SKIP；不把红轮或独审重复节点加进此总数。

独立终审 [PASS](independent/final-review.json)、[说明](independent/FINAL_REVIEW.txt)：73 pytest PASS / 0 FAIL / ERROR / SKIP，包括后端39、响应留存21（作者14＋独审另写7）、实际 HTTP/JSDOM 页面13；另14个受控、非HTTP可见 DOM场景 PASS。独审自己的14个源/测试路径前后SHA不变，又独立核查作者冻结全部358路径及每份HTTP加载源码。上述页面13是同作者场景的独立执行，不叠加为26个独特场景。四份合同/说明已审，无未解产品缺陷/阻塞；其52份原字节文件和清单本身经hash核对归档，见 [归档回执](independent-archive-receipt.json)。

独审还从上一轮已封版实际 SQLite 数据库只读 backup 后回读应用，HTTP200、旧 raw 不补造、原数据库 SHA 未变，见 [实际旧记录回读](independent/legacy-actual-sealed.json)。这仅证明该实际保存记录的读取兼容，不是旧源码完整升级测试。

[core-trace.json](core-trace.json) 是本次新建纯 MD 项目的实际完整账本，由 [capture_core.py](capture_core.py) 生成：3 次合成 Intern MockTransport 请求、实际 resource.read 回执、无效候选 Attempt/诊断、一次修订、PARTIAL 候选、精确确认和唯一材料 grant、预览/内部版本、空实例、冷 Store 普通 Worker 的 3 个新/变词成功、6 个错误输入 FAILED 历史、3 条结果。CSV 资源 0、LIVE 调用 0、应用运行模型调用 0；新 Attempt 包含完整 bounded raw 与冻结策略/hash。没有用候选模板代替生产模型、上传结果或 Replay。

## 失败历史

- [red.xml](red.xml) / [red.log](red.log)：旧 `dd26d5f` 产品源上，新节点 4 PASS / 18 FAIL。17 个是页面/RECEIVED 留存缺口；1 个 late-confirm-app 在夹具创建另一个 CSV app 时漏传 goal，422 尚未触及产品。补夹具后单跑旧源 [red-other-app.xml](red-other-app.xml) 得 1 FAIL，实际复现迟到确认覆盖当前另一个 app；12 个未选节点 deselected，不算 SKIP。
- [green.xml](green.xml) / [green.log](green.log)：首轮修复源 53 PASS / 13 FAIL。页面已通过相应可见交接、迟到保留和 ID 恢复检查，13 条链都在内部审批步骤失败：驱动没有像实际用户一样在 preview 重绘后重新填词。原驱动版本 [driver-first-pass.cjs](driver-first-pass.cjs) 和全部中间页面 JSON/log 留存；补这一步后同产品行为 66 PASS，不把夹具失败重写为产品失败或成功。
- [mypy-initial.log](mypy-initial.log)：首次静态检查为原 5 项基线加 1 项新局部字典推断错误；增加明确类型后新项消失，全树仍是原 5 项。
- 独审 [legacy-actual.log](independent/legacy-actual.log) 的早期探索实际返回409并失败：误选上一轮更早未封版数据库，Run repairs=0、已有diagnostic但没有GA_APP_CONFIRMED锚。原FAIL和 [分类](independent/legacy-preseal-409-classification.json) 留存，未伪装修复/升级成功；另选已封版旧记录只读回读才得到上述200。

## 静态、源码与边界

[static-comparison.json](static-comparison.json) 从 `dd26d5f` 临时归档重新运行全树检查，与当前逐项比对：Ruff exit 1 / 10 错误，mypy exit 1 / 5 错误，诊断身份完全相同。对照 PASS 不是静态全绿。[final-checks.json](final-checks.json) 的改动 Python Ruff、3 份 JS 语法和产品/测试/合同文档 whitespace 检查均通过。

完整暂存区 `git diff --cached --check` 实际 exit2，仅六份 red/green 原始失败 log/XML 报尾随空白；原字节不清洗，准确路径与输出见 [回执](raw-evidence-whitespace.json)。没有把该完整检查记作通过。

[source-manifest.json](source-manifest.json) 冻结 358 个 Git 跟踪源/测试/pyproject 文件（src 81、tests 276、pyproject 1），不含 ignored 文件或证据；最终测试后与后续检查字节一致。页面加载的 HTML/CSS/JS SHA256 另在每条实际页面回执中保存。

只验证合成 provider 下的有限工程链和确定性字面证据。生产 provider 默认 disabled、LIVE allowance=0；完整目标语义接受 NOT_RUN、candidate-ready 为 PARTIAL、semantic UNKNOWN。真实模型/付费 API、语义或 owner 验收、PG/角色、Windows、原生浏览器/视觉、旧源码完整升级、完整 P-A/P-B、远端 CI/部署均 NOT_RUN。未配置凭据、扩大安全权限、部署、改 main/coredev 或强推。

复验（新建本地合成夹具，不改旧证据）：

```bash
PYTHONPATH=src:tests .venv/bin/python docs/evidence/pa-text-handoff-20261011/capture_core.py
SIM2ACT_PA_EVIDENCE_DIR=/tmp/pa-text-handoff-repeat NODE_PATH=/workspace/node-tools/node_modules .venv/bin/pytest -q tests/test_goal_text_ui.py tests/test_goal_text_rejected_raw.py tests/test_goal_text_applications.py tests/test_goal_text_adversarial.py
```
