# CSV事前合同确认：工作区返回与原确认恢复修复

本修复从已推送的 `ae4e3558a1606bf2846354fd06d24373d4ecee9d` 创建普通分支 `dev/csv-report-confirm-workspace-20261017`。最终产品/测试源为 `aed84dfc36eb6e810760331bd72b5f9853b981d5`；此后的提交只写本说明与新证据。本轮没有开始后续产品功能。

追加独审发现：WAITING_APPROVAL确认控件闭包绑定旧workspaceSelectionGeneration，但Resources→Projects只重建run-outcome，不重建独立csv-report-contract。返回后复选框和确认/UNKNOWN恢复按钮仍可见，旧stillCurrent永远false，点击没有请求。账号或项目往返后，原页面会在显式重开Run时继承旧勾选。这是实际确认入口缺陷；原ae4证据未覆盖这些操作，不用其已有绿例声称这里曾通过。

## 真实红例与来源

- 作者基线 `54567147fd8220eae05fe708196df099f00654df` 只增加测试，所有src字节等于ae4；4FAIL/0ERROR，JUnit20.707s。真实页面可见导航复现未确认返回、实际确认POST已接受且响应被控制延迟时返回、项目和账号往返。
- 作者 `2c530db7c25836f5851de057771450ff632c379d` 仍只改测试，另行单跑新增UNKNOWN红例，1FAIL/0ERROR，JUnit9.848s。实际确认响应已被接受后控制丢弃，原UNKNOWN恢复按钮返回后点击0POST。
- 独审从2c530只读导出Git版本，独立运行相同五项：5FAIL/0ERROR/0SKIP，JUnit25.814s。五红是产品断言失败；pending/UNKNOWN的真实确认已200接受、数据库QUEUED，其余WAITING_APPROVAL，全部0Worker执行/0Operation/0模型。不得把pending/UNKNOWN写成“没有受理”。
- 独审首次545导出未包含collection链所需的版本化 `docs/evidence/bounded-agent-offline-20261006/independent-gold.json`，RC4/JUnit1.136s、0产品场景。该收集错误单独原样保留，不计产品红；新2c530导出补入同Git中唯一必要fixture，未用旧bundle，也未修改源或测试。

## 最小产品修改

相对2c530，src/tests严格只差 `web/app.js` 与 `web/ordinary-csv.js`；红绿用例及全部后端字节相同。

1. 确认面板独立保存当前view，绑定账号连接、项目代次、Run选择、工作区代次和view对象。工作区返回创建新view与DOM；旧view、脱离DOM控件和旧异步回调继续失效。账号/项目/Run清理时同步清除该view；普通成果视图仍按原逻辑独立重建。
2. 未发送的ready确认在新范围恢复为未勾选。每次新勾选先GET原Run，核对id、WAITING_APPROVAL、原Run版本、未确认状态、contract fingerprint及完整snapshot，await后再次校验view和勾选代次。只有仍一致才允许用户另点原确认POST；服务端原完整合同与权限检查继续生效。
3. 已发送与UNKNOWN的原body/key及请求状态保留；返回只重建未勾选控件，不自动GET或POST。提供明确“重新读取原Run完整合同（只读）”按钮。pending可显式读回实际已接受Run；UNKNOWN恢复仍仅用原body/key，不建立第二Run或第二成果。旧确认回调不能覆盖新视图。
4. 面板使用`run_version`显示Run版本，避免被展开spec.version覆盖。未新增API、executor、Grant策略或后台执行能力。

## 冻结绿例与精确范围

作者在aed84：8个新合同页面参数一次8PASS/45.115s，另行原普通成果workspace-return直接回归1PASS/7.906s。各批571个tracked源/测试before/after与Git逐字一致。未修改源码或测试后重跑“为了凑一整轮”。

独审在同aed84：9PASS/0FAIL/0ERROR/0SKIP，JUnit60.114s；572份tracked输入（571源/测试+pyproject）before/after与Git一致。最终选择是旧3页面直接回归+5新导航+旧普通成果返回1例，共9唯一节点；红绿重复不增加唯一数。

双方相同范围：149个页面断言、409条实际ASGI页面API请求（389GET/20POST，含原key恢复）、198份served HTML/CSS/JS资产逐hash核验。新8页面各一个冷NoModel Worker、同Run三VERIFIED工具、实际保存完整MD，模型请求0。旧普通成果回归一个冷Scripted Worker、4次合成Mock请求，仍PARTIAL/NOT_RUN。全轮真实模型0；不能把这一例也称NoModel。9份实际Blob捕获原件：新8份各730字节、旧1份109字节，逐字匹配各自保存内容/hash。

五个新场景分别验证：未确认返回后新勾选的完整合同GET、pending返回后显式GET且迟到旧响应不覆盖、UNKNOWN返回后原key精确恢复、项目往返、账号连接往返。返回本身均不自动发送。旧控件的0请求防线包含对已脱离DOM的handler直接调用；这是围栏检查，不冒称用户可物理点击脱离DOM控件。丢失/延迟回执为实际ASGI接受后控制页面交付，非真实网络中断。

## 既有验收证据关系

旧完整28例实际执行源仍是 `599052cbadae21b4a7ba8738fb889ea970c11e84`。此前 `402f3eb5f80be73ddc57d4bb6123fdd6157726e0` 只复验3页面，当时其余25例保留599来源。本轮aed84另行实际重跑其中的普通成果workspace-return 1例；其余24例未在本轮重跑，不改签原599记录。不称“最终28全过”或“31唯一”。旧ae4的全部文件及证据原样保留。后端合同、独立数值checker、权限、Worker/工具账本及原固定checker均与ae4逐字相同。

`originals-manifest.json`给出每份新执行原件的原始路径、归档路径、字节及SHA-256；SQLite和较大文件以mtime0确定性gzip保存，解压与原件一致。`checksums.sha256`覆盖归档。独审只读导出的snapshot源码是可从Git恢复的输入，其逐字hash/provenance保留；不把数百复制源码或执行产生的pyc当额外原始执行输出计数。独立初始收集错误、五红与最终绿分别归档，不覆盖失败。raw机器输出保留原空格与换行，属性例外只限raw证据。

仅验证Linux/Python3.12/SQLite test_only、实际FastAPI ASGI、完整服务页面/Node JSDOM/Blob。未运行原生浏览器、Windows、PostgreSQL、真实模型、真实语义/人工签收、远端CI、部署或旧恢复矩阵。新CSV合同仍只限定结构化目标PASS，通用语义NOT_RUN、owner PENDING、发布关闭。未访问旧满盘环境，旧末轮独审报告缺口未补回。

## 后续只读候选，尚未实现

原方案F2-T01与验收章节要求事前标准与语义人工量表分开。当前普通RunInput只收Goal/材料/key，普通自然语言GoalSpec.constraints默认空；已有owner-review入口绑定internal instance（或其natural Run）。下一项高价值候选是普通Goal事前人工标准及同一Run逐项签收，复用现有声明账本的保护，保留自动语义NOT_RUN、区分人工声明与机器通过。不能直接把普通Run传入internal-instance owner API，也不能推导新权限。本轮只核实这个缺口，未写实现。

来源归属补正：首次归档把原25例笼统写成“本轮也未复跑”，与本轮明确执行的普通成果workspace-return 1例冲突。现已补正为“其中1例在aed84重跑，剩余24例未重跑”；原作者scope JSON的旧字段保留为原记录，并由raw/author/scope-attribution-correction.json明确撤回。测试命令、XML、结果与独审9例范围始终不变，原267份原件也未改动，仅增加此补正原件。
