# F2-T02 / P-A 有限非 CSV 核心工程证据

2026-10-11；开发基线 `1dadba831a4d15fc164398e2f1070f22d7a5d77d`，独立分支 `dev/pa-text-goal-20261011`。根代理唯一写产品代码，独审另进程只读审查及实际测试。上一轮共享私有读取修复已获接纳；本轮回到原目标生成应用主线。原 V5 方案与验收门未改写为完成。

合同见 [PATextGoalPlan](../../F2/PATextGoalPlan.md)。支持一份 TXT/MD 材料的大小写敏感字面检索：4096 UTF-8 字节、64行、词1—80字符且无首尾空白、至多16命中；输出所有命中完整行与行号。无命中返回空列表。语义状态 UNKNOWN，完整目标语义验收 NOT_RUN。

## 实际链路与实现

- [goal_applications.py](../../../src/sim2act/goal_applications.py)冻结完整GoalCard、项目/主体/运行身份、材料hash、服务端app/action ID及预算。Intern协议先返回tool_call，实际 `resource.read` 的VERIFIED回执进入下一次请求，随后响应完整ActionSpec/AppManifest。无效候选保存原Attempt、响应和诊断，再允许一次修订，最多3请求/1读取/1修订。
- Worker沿用真实持久队列、保守字节预算、Attempt、lease/fence和取消意图；生成不进入其他protocol池。实际发送wire、收到响应及来源有独立事件锚。未知响应不导入候选或自动重发；取消/暂停/撤权/版本竞争/迟到不提交候选。已收到但拒绝的原JSON（包括tool_calls、finish_reason）限32768 ASCII字节保存；没有收到的响应不捏造raw。
- 生成仅为 `PARTIAL` / candidate-ready，没有应用或语义成功。精确Run版本/候选指纹确认在一事务内创建独立app身份、唯一材料读取grant、草案、来源表和确认事件；缓存确认及只读恢复也复核当前来源/权限。API不执行DDL；新增表经既有显式 `Store.initialize()` 迁移。
- [text_apps.py](../../../src/sim2act/text_apps.py)登记有限纯变换 `text.literal_evidence`，消费授权后的实际材料，使用现有独立证据检查器。生产没有候选模板、任意代码或intern.agent隐式替代。应用的执行不需要模型或Replay。
- 既有compile/preview/internal release/instance/AppRun Worker被复用。提交事务复核当前权限、来源、lease/CAS和结果，保存完整工具回执、类型化结果及失败历史。[text_run_checks.py](../../../src/sim2act/text_run_checks.py)独立复核成功历史，即使Job状态被改成FAILED/CANCELLED也不跳过已保存成果检查。
- [goal-application.js](../../../src/sim2act/web/goal-application.js)展示完整已保存目标、来源、有限生成合同及候选；显式确认后进入预览与内部版本/实例。未知POST只用原key GET恢复；known Run/app ID、指纹、主体/选项代次防止替换及A→B→A迟到操作；引用按textContent呈现。

工程发送只在显式 `Store.test_only`、mock mode和 `httpx.MockTransport` 条件下允许。生产默认provider disabled，LIVE allowance=0，普通MockModel不会变成规划器。测试fixture选择完整候选响应，仅证明协议/工具/编译/执行工程链，不能证明自然语言规划质量或真实provider的token可行性。

## 可审计实际结果

[core-trace.json](core-trace.json)由 [capture_core.py](capture_core.py) 新建纯MD项目实际执行产生，含完整GoalCard、三次实际合成provider请求、原失败候选及诊断、工具回执、最终清单、确认、最小grant、内部Release、空实例、冷Worker输出和数据库账本。没有CSV资源、上传答案或Replay；原始请求没有凭据/header，材料和身份都是合成。

1. 第一次请求自主选择resource.read；第二次收到真实材料回执后产出缺少term绑定的无效清单，原 `INVALID_MANIFEST` Attempt保留；第三次收到该诊断后产出合法清单。
2. Alpha样本预览命中第1/3行，内部版本产生空实例。重新打开Store后的普通Worker以未见词Beta重新读取MD，返回第2/4行；小写beta返回空列表，Alpha再次生成不同完整结果。三条类型化历史均保留。
3. 六种错误输入（缺term、非字符串、空词、首尾空白、81字符、额外resource_id）均实际FAILED、无result；结果表仍仅三条，失败任务历史保留。模型Attempt仅生成阶段三条且全MOCK，LIVE请求0。

|实际执行包|PASS|FAIL|ERROR|SKIP|范围|
|---|---:|---:|---:|---:|---|
|[shared-backend](shared-backend.xml)|386|0|0|9|首轮共享回归，含冻结合同、安装预检、模型故障、私有读取、原agent/CSV/内部生命周期；属于较早修复版本|
|[final-backend-ui](final-backend-ui.xml)|343|0|0|8|后续受影响后端/私有读取/生成/内部实例及4页面，最终微调前版本|
|[sealed](sealed.xml)|47|0|0|0|最终产品源码：13作者+30独立故障回归+4页面；79.625秒|
|[independent seal](independent/seal-junit.xml)|47|0|0|0|独立进程同最终产品源码；77.98秒，含30独立回归+13作者+4页面|

各包有重复节点，不相加当作唯一测试总数。全部作者轮次与SKIP原因见 [test-history.json](test-history.json)：SKIP仅实际SQLite下PG应用角色等既有条件缺失。独审终结论 [PASS](independent/final-review.json)，另9项受控离线DOM检查通过，属于合成DOM probes而非HTTP；与4个IPC/进程内HTTP/JSDOM场景分列。

四个页面场景valid/lost-generation/lost-confirm/late-generation分别25/25/25/27检查，共102检查，使用实际TestClient HTTP及普通Worker。原key恢复没有第二次生成/确认POST，迟到旧目标不触发确认。页面源码加载SHA与最终独审封版一致，记录见 [独审页面](independent/seal-ui/) 与 [作者页面](ui-sealed/)；原生浏览器未运行。JSDOM来自当前已有 `/workspace/node-tools/node_modules`，未安装依赖。初次未指定NODE_PATH的模块失败日志保留。

全树Ruff实际exit1/10错误、mypy实际exit1/5错误，均与基线 `1dadba` 的路径、行号和诊断逐项相同；[静态对照](static-comparison.json)为PASS不等于静态全绿。修改产品/测试的Ruff、JS语法及产品/测试/新文档diff whitespace检查通过，见 [检查回执](final-checks.json)。完整staged diff检查exit2仅来自六个原始失败log/XML中的尾随空白，按原字节保留，输出见[回执](raw-evidence-whitespace.json)；未清洗失败日志。源码/测试Git跟踪清单包含358个文件（src81、tests276、pyproject1），见 [冻结manifest](source-manifest.json)，不将ignored代码计入Git可复验文件。

## 原失败与修复

作者原轮 `initial` 6PASS/7FAIL、`repair1` 11PASS/2FAIL、`repair2` 12PASS/1FAIL及全部日志/JUnit保留。真实缺陷为候选JSON字节界限错误地等同token界限，另含fixture期望材料字段/错误码/201状态的适配问题；修复后13项通过。字节几何界限与既有token预算分别核验，没有提高LIVE额度。

独审原失败在 [independent/](independent/) 原字节保留，包括预算计数篡改、来源Run失效、确认凭据篡改、畸形Attempt/恢复导致500、成功历史改状态绕过复核及页面合法错误ID；修复后原节点通过。超时未知不重发、旧fence迟到仅保留实际响应而不修改新owner、确认末尾注入失败无身份/grant/草案残留亦实际通过。夹具/导入/NODE_PATH错误单列在终审清单，未删失败记录或改成PASS。

## 复验与边界

从仓库根运行（仅合成测试）：

```bash
PYTHONPATH=src:tests .venv/bin/python docs/evidence/pa-text-goal-20261011/capture_core.py
SIM2ACT_PA_EVIDENCE_DIR=docs/evidence/pa-text-goal-20261011/ui-sealed NODE_PATH=/workspace/node-tools/node_modules .venv/bin/pytest -q tests/test_goal_text_applications.py tests/test_goal_text_adversarial.py tests/test_goal_text_rejected_raw.py tests/test_goal_text_ui.py
```

没有运行真实模型/付费API、语义或owner验收、PG及角色、Windows、原生浏览器/视觉、旧源码完整升级、完整P-A/P-B或远端CI；均NOT_RUN。没有配置凭据、扩大网络权限或部署。新表只在SQLite显式迁移测试，不能据此声称PG迁移通过。既有AppUse目录仍是CSV专用，非CSV路径由目标页、预览与内部实例页进入。未改main/coredev，不强推；普通独立开发分支推送及精确远端SHA核验在最终交付回执中记录。
