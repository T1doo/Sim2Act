# owner 读取顺序 P2 纠正证据

基线 `ed5cda2e341f0601879ad3f1e42ad1667022d490`，唯一产品写入者 root；既有 pa_independent_review 只读审查、仅写自己的 /tmp 输出。开发分支 `dev/owner-version-acceptance-20261011`，main/core dev 不写。具体合同见 [OwnerReadOrder20261011.md](../../F2/OwnerReadOrder20261011.md)。

## 实际缺陷及保留的失败

- `red.log/xml`：实际 HTTP 旧 ACCEPTED 初读在较新 REVOKED 刷新后返回，1 FAIL / 1 PASS。第一版 PREPARE 夹具提前编辑了草稿，已有编辑 fence 因而挡住旧响应，不能证明同 fence 的读取顺序安全；原夹具保留。
- `red-same-fence.log/xml/pages`：纠正夹具，在释放旧响应前不编辑，REVOKE 与 PREPARE 两种实际 HTTP 逆序均 FAIL。旧服务实际 GET、另一授权会话实际 POST、新 GET 与交付顺序都在 JSON 保存，人工声明为 SIMULATED。
- `green-first.log/xml/pages`：9 PASS / 1 FAIL。作者运行中修改源码，静态脚本前后 hash 不同，属于验证操作失误；此轮不能作为固定源码验收。
- `final.log/xml/pages` 与 `final-source-freeze.json` 是名字保留的**候选一**：固定361文件作者77 PASS；独审同77 PASS。独审实证 inner throw 与 outer catch 之间发起新读取仍会被旧错误污染；`microtask-red/` 四个 caller 均 FAIL。该整轮接受结论已撤回，见 `candidate-status.json`。
- `sealed2.log/xml`：固定362文件作者81 PASS / 0 FAIL / 0 SKIP，408.63秒。但同微任务窗口仅编辑再撤销、读取序号不变时，initial 外层仍只检查 ownerCurrent；`initial-edit-red/` FAIL。候选二页面接受结论撤回，见 `sealed2-status.json`。
- `sealed3-launch-error*`：作者提取后端子集时把实际 `tests.*` XML classname 误当不带前缀，断言失败后顺序 shell 误启动了旧33页面复测。精准 SIGINT 取消这一误启动，原 log/XML/page 输出保存；源码冻结检查实际通过，没有产品源码变化或工具授权拒绝。这不计完整 PASS。
- 独审自己的跨 realm 首探针未命中微任务窗口、附加脚本 SyntaxError/ReferenceError、原 transport disconnected 均须保留并按报告明确范围；修正后的实测另存，不能覆盖原错误。独审 CONTROLLED37-v2 为36 PASS/1有界等待夹具FAIL，过早关闭DOM后又有cleanup TypeError；原log/JSON/result均在238份档案中，v3使用5秒上限、5ms异步等待后37例实际通过。

## 最终验证范围

最终以 `sealed3-source-freeze.json` 的362个源码文件为准。最后一修只变 owner-review.js、维护调度脚本与其 UI pytest 参数。Python 后端及后端测试保持精确同字节：作者从 sealed2 的实际 JUnit 提取 owner35 + text13 =48节点；独审从其候选一实际 JUnit 提取同48节点，另核254个非UI Python/pyproject散列。`backend48-reuse-proof.json` 和独审最终 proof 保留边界；不把其他未跑的 Python 测试计为 PASS，不宣称最终82一次整集合重跑。

最终34页面/调度用例重跑：29个实际 IPC/进程内 HTTP +正常 Worker +离线JSDOM页面例，另5个仅本地源码的受控微任务例。5例包括 initial/refresh/recover/action-readback 外层错误与 initial-edit 实际 InputEvent insertText/historyUndo；其摘要刻意为 constant，不验 HTTP、Worker、真实摘要等待或系统原生 Undo。真实摘要等待与合法同序列状态变化由独立探针另验，不能混入页面 HTTP 数量。

| 最终范围 | 作者 | 独审 | 证据边界 |
| --- | --- | --- | --- |
| 后端48 | 48 PASS/0 FAIL/0 SKIP | 48 PASS/0 FAIL/0 SKIP | 完整实际旧JUnit的精确子集，254个非UI Python/pyproject与最终同字节；不认领最后JS修复后的整82一次运行 |
| 最终页面/调度34 | 34 PASS/0 FAIL/0 SKIP，291.50秒 | 34 PASS/0 FAIL/0 SKIP，291.22秒 | 29实际HTTP页面 + 5受控微任务分别统计；362源码最终前后无变动 |
| 独立附加API/Worker2 | — | 2 PASS/0 FAIL/0 SKIP，14.98秒 | 包括actual grant HTTP撤权同seq2 ACCEPTED→STALE、原key只metadata无payload及SQL不读owner payload；另一实际HTTP/JSDOM页面52检查/50手势/2开页38静态GET单列 |
| 独立受控37 | — | 37 PASS，Node exit0 | 真实ownerHash及实际app.js canonical；只控制摘要promise交付，含合法同序列状态和pending资格。不是37个HTTP或真实人工例 |

29页包实际1307项检查、1261次可见启用DOM手势、2条诊断汇总、59次开页 ×19资源=1121次实际静态HTTP GET，200/MIME/bytes/hash与冻结源码全部匹配。5个受控微任务单列30个断言，不混入1307；额外独立同seq页面另列，不能把重复基础流程累加成新的独立产品验收。作者最终验证见 `author-final-verification.json`、`sealed3-ui34.log/xml`；独审完整原字节报告见 [FINAL_REVIEW](independent/FINAL_REVIEW.json)、[原字节238档清单](independent/archive-file-manifest.json)与[全部测试历史](independent/test-history.json)。PENDING→EXPIRED 的信封来自实际API配合受控clock，不认领真实等待15分钟；ACCEPTED→STALE另有实际HTTP撤权与真实进程内HTTP页面。

作者MIME汇总探针第一次错误假设 application/javascript，但实际正确记录为 text/javascript; charset=utf-8，断言失败原错误保留 `author-metrics-first-error.log`；只纠正汇总器后，1121资源的实际MIME/bytes/hash均匹配，无产品或源码改动。

## 不提升的范围

所有人工逐项选择都是 SIMULATED。技术语义 UNKNOWN、正式发布开关 false 保持；新 GET 只在既有本人/项目检查后补范围元数据，未新增读取旧受保护 payload 的授权。浏览器只核 Strict 请求指纹及精确元数据；含浮点的完整 payload/seal 仍由后端权威验证。

PG、Windows、原生浏览器、旧源码升级、真实模型/付费 API、真实 owner 语义、完整 P-A/P-B、完整256条耐久/性能、最终82一次整集合、正式发布及部署均 NOT RUN。远端 CI 未验证，不对新精确SHA声称CI绿或没有runs。全局 Ruff10/mypy5为此前相同既有基线错误，改动 Python Ruff另验。旧四目录904文件对ed5 Gitblob均同字节，具体 `history-preservation.json`；本轮最终再次核对。

环境断开通知后默认 exec 实际成功并原健康进程正常完结，见 `environment-check.json`；没有凭 inProgress 认定恢复，也没有重试已知浏览器拒绝路径、换环境绕过或配置凭据。
