# P-A 窄 P2：编辑再撤销后的迟到交接保护

2026-10-11；开发分支 `dev/pa-text-goal-20261011`，接续基线 `7e86ec78201e7d0fcce5b43d6157c318f9ba8296`。根代理是唯一产品源码写入者；既有 `pa_independent_review` 独立只读复核。原授权范围、[P-A 合同](../../F2/PATextGoalPlan.md)、[剩余验收清单](../../F2/DeliveryRemainingChecklist.md)和父复审的具体 P2 为依据。

## 修改与边界

旧交接只比较草稿最终值。同卡 A→B→A 编辑撤销后，迟到确认或原 key 读取可能重新通过检查，切到 apps 并接管焦点。`goal-application.js` 对七个持久目标字段和材料选择器的 `input`/`change` 累加页面存续期间不重置的编辑代次。确认、原 key 恢复均冻结该代次，在现有各异步交接检查中复核；值复原也不能恢复旧交接。原完整值、身份/项目/目标、工作区/应用代次检查仍保留。显式新一次只读恢复可建立新交接，无编辑确认照常打开精确应用。

相邻自然目标回归发现 index 引用的 `/goal-application.js` 既有 API 固定静态路由遗漏，实际返回404。`api.py` 只补该固定 `FileResponse` 路由。此前 P-A 驱动本地嵌入脚本，所以原页面结果不证明 HTTP 脚本交付。当前驱动每次开页通过进程内实际 HTTP 读取 HTML、CSS、全部16脚本，并按 boot 保存状态、Content-Type、字节数和 SHA256；本地路径只用于 Python 的独立源码 hash 比对，不能代替页面加载。

没有修改目标生成/预算、候选来源、worker、权限、执行器、应用内容或语义接受。生产生成仍 disabled、LIVE allowance=0；所有合成 provider 通过 test-only MockTransport，真实/付费模型请求0。UNKNOWN 语义不提升，目标接受仍 NOT_RUN。

## 失败历史与证明范围

原两个 P-A 证据目录共270文件保持相对基线原字节，见 [旧证据清单](old-evidence-integrity.json)。下列各轮是同一批节点重复执行，不能相加认领唯一测试数量。

| 轮次 | 实际结果 | 解释与原始证据 |
| --- | --- | --- |
| 首次红轮启动 | 未执行测试 | shell 输出目录尚不存在；exit1，见 [setup-failure.json](setup-failure.json) |
| 原 `7e86ec7` 编辑撤销红轮 | 2 FAIL，13 deselected | 同卡 textarea insertText/historyUndo，确认 POST 与原 key GET 各复现焦点接管；[red.xml](red.xml)、[red.log](red.log)、[red-source.json](red-source.json) |
| 编辑代次定向修复 | 2 PASS，13 deselected | [green-aba.xml](green-aba.xml)、[green-aba-ui](green-aba-ui/)；这轮脚本仍从本地源码嵌入 |
| 首次相关完整回归 | 68 PASS / 5 FAIL / 0 SKIP | 15 P-A、53后端通过；自然目标5例均遇缺失脚本路由导致 JSDOM SyntaxError；[final.xml](final.xml)、[natural-red](natural-red/)、[script-routes-red.json](script-routes-red.json)。原 [page-proofs.json](page-proofs.json) 572检查/494动作只证明 API 链及本地脚本 |
| 改为真实 HTTP 脚本加载的红轮 | 1 FAIL，14 deselected | 尚未补路由，直接在 `/goal-application.js` 404 失败；[red-http.xml](red-http.xml)、[red-http-ui](red-http-ui/) |
| 路由修复后首候选作者轮 | 11 FAIL，余62计划节点 NOT_RUN | 删除本地脚本路径配置时也误删 Python 最后 hash 比对仍需的 `web` 变量，出现 F821/NameError；精确识别作者唯一 pytest 后 SIGINT，exit2；[sealed.xml](sealed.xml)、[sealed-fixture-cancellation.json](sealed-fixture-cancellation.json)、[sealed-checks.json](sealed-checks.json)。保留首候选 manifest；恢复局部比对变量后另轮验证 |
| 编辑代次独立第一轮 | 68 pytest PASS，另26受控探针 PASS | [独审原报告](independent-edit-only/final-review.json)、[红轮分类](independent-edit-only/red-history.json)。API/Worker实际；该轮脚本为本地嵌入，26受控响应探针不称 HTTP/worker 证明 |
| 路由修复后首候选独审轮 | P-A 15 FAIL；后端53 PASS、自然兼容5 PASS | 同一 Python `web` NameError；底层15 Node JSON PASS不折算 pytest PASS。取消请求到达时独审 pytest 已自然结束，未发送 SIGINT；[独立首候选历史](independent-http-final/candidate-fixture-failure-history.json)和完整日志/XML原字节归档 |

独审第一轮24个 ABA 探针覆盖七字段和材料选择器 × 确认 POST / 原 key 确认 GET / 应用 GET 三种迟到点，另2无编辑对照。第一次旧码2PASS/24FAIL中3个材料选择夹具缺选项失败已留档；修正独审夹具后同旧码仍2PASS/24产品FAIL，再对修复码26PASS。没有用夹具失败冒充产品红轮。

JSDOM textarea 用 `setRangeText` 改值，再派发实际 DOM `InputEvent` 的 insertText/historyUndo 顺序。原值及工作区/应用/目标选择代次均验证不变，迟到响应不能接管焦点/导航，随后显式原 key GET 可正常交接。这里是 JSDOM 派发事件，不是原生操作系统/浏览器撤销栈证明。动作仅统计 `user_actions.event == "native DOM dispatch"`；两个编辑序列摘要是诊断记录，不额外算动作。

## 最终验证

最终源码冻结 [final-source-manifest.json](final-source-manifest.json) 包含358个跟踪文件（src81、tests276、pyproject1）。先前编辑代次 manifest 和含 F821 的首候选 manifest 均保留。最终变更源码 SHA256：

| 文件 | SHA256 |
| --- | --- |
| `src/sim2act/web/goal-application.js` | `3468e7fefad83b7257cbb8e83b8fc99e7d3d1dcb53a3ce8a40fdfead0152b481` |
| `src/sim2act/api.py` | `abc436e498dc3261c9232e5c942c8b2e612029bf92aab99defcc59d204888a4c` |
| `tests/goal_text_ui.cjs` | `a148c53890281f5a0ea40289a5e408872f040825cb0fe7eda54d6c4611a91da1` |
| `tests/test_goal_text_ui.py` | `ff6da760df409e7cb71b7193b4210df70f2914bce26ee20cc96015c16c0cad44` |

作者正式终轮 **73 PASS / 0 FAIL / 0 ERROR / 0 SKIP / 0 deselected**，188.25s，见 [verified.xml](verified.xml)、[verified.log](verified.log)、[各轮实际历史](test-history.json)、[作者终轮完整性](author-final-integrity.json)。73节点为15 P-A页面、13目标应用、14原始响应、26对抗后端、5相邻自然目标兼容场景。独审独立新前缀正式终轮同一73节点 **73 PASS / 0 FAIL / 0 ERROR / 0 SKIP**，183.16s；另26受控迟到探针及18项 HTTP资源独立探针通过。两次73是重复执行，不相加为146个唯一节点；26探针另计，受控响应不冒称真实 HTTP/Worker运行。

[作者最终页面审计](verified-page-proofs.json)逐份核对15场景 **572内部检查、494可见且可操作 DOM动作、2诊断摘要、30 boot × 18资源 = 540实际 HTTP GET**。每个 boot 加载HTML/CSS/16脚本；全部200、正确ctype、UTF-8字节数及源码SHA，每场景恰好一次生成POST和一次确认POST。旧 `page-proofs.json`及旧独审报告的本地脚本范围不改变。五个 [自然目标兼容回执](natural-verified/)共73内部检查，走实际 loopback HTTP，但其直接处理器测试不能认领 P-A 可见操作链。pytest临时 `*current` symlink 曾使证据复制助手重复遍历同案例，复制错误及去重/原字节验证见 [collection-initial-failure.json](collection-initial-failure.json)，不计作产品测试失败。

[最终独审报告](independent-http-final/FINAL_REVIEW.json)、[原字节归档清单](independent-http-final/archive-file-manifest.json)及 [归档比对](independent-http-archive-integrity.json)覆盖130原始文件另加manifest，首候选失败与最终通过均保留。独立 [18资产 HTTP 探针](independent-http-final/sealed2/http-assets.json)核200/ctype/bytes/hash及未登记脚本404。四份最终文档的只读审查另见 [doc-review.json](doc-review.json)，不改封版130文件或原manifest。有限范围未解决产品缺陷0、当前执行阻塞0。作者358项源码、旧270文件复核0变化；独审19项before/after对自身及最终358冻结清单均0差异。

[最终静态比对](verified-static-comparison.json)：全树 Ruff10、mypy5，与 `7e86ec7` 既有诊断逐条完全相同；不是全树静态绿。新增候选 F821 已纠正；[改动检查](verified-checks.json)及 [冻结前检查](final-source-precheck.json)通过。原始失败日志/XML原字节保留，日志尾空格可能触发完整 evidence 的 whitespace 检查，源码、测试、文档单独核查。

## 未运行与下一门

PG/角色、Windows、原生浏览器/视觉/系统撤销、真实模型/付费 API、旧源码完整升级、完整 P-A/P-B、语义与 owner 接受、远端 CI、部署均 NOT_RUN。本修复不改变这些门。下一 owner 精确应用版本及新输入证据验收只在父复审签收本 P2 后接续；真正语义 owner 由用户承担。正常分支推送仅证明远端 SHA，不表示 CI 通过。
