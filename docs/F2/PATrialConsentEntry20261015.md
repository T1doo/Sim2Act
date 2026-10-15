# P-A 七槽准备与同意入口（2026-10-15）

结论：**仅准备与同意入口已验证**。本轮没有实际 P-A/P-B 执行、模型调用或正式发布；历史 Cold 仍 NOT_ACCEPTED。当前软件尚未通过原精确软件 target qualification，不能把这次交付当作运行准入。

基线 `619cc4bf5caf28841c3d8b9a6f0b9d22021f85d9`；服务器及初版页面提交 `178e0ddc85202e04914c6cdf72ba6bc45ea214d3`；旧拒绝预期修正提交 `22c3f8a65ca42cf9c2dd8c51ec15a6c6dcc95e5d`；最终冷页修复及实际测试冻结提交 `9a5f1e43772454b7ec933106b132afc539e1eb04`。开发分支 `dev/pa-trial-consent-entry-20261015`。最后一次改动仅前端与两个页面测试文件，服务器源码保持。

## 产品入口与合同

对照原 V5《平台产品设计》111–115 行：用户从目标与资料形成契约，不能要求其先编辑 JSON 或源码。原 natural_trial_api 只提供完整 contract/指纹 DTO；原前端无七槽精确同意入口。

现可在项目“目标卡与验收草案”内点击“读取当前目标卡”，选择两张不同、已保存的完整 GoalCard（分别只绑定一份当前已授权 TXT），再“准备精确范围”。服务端校验版本、项目/主体/runtime、两份不同材料及完整 Goal 快照，生成原 TrialContract、内部指纹和稳定阶段键。沿用原有限材料界限：每份 TXT 最多1024 UTF-8 bytes、20行；不符合则明确拒绝，准备过程不授予新权限。

原 TrialCaps 不变：Generate3+Source2+Cold2=7请求；每请求输出≤1024，总输出≤7168；wire及ASCII响应各≤32768 bytes；每Run预留≤64000、总预留≤192000；每Run≤300秒；lease30秒；RPM1；付费cap0。准备期限为服务器生成时刻+300秒，准备重放、批准与读取均不延长。此处不证明实际运行可在该期限内完成。quota主体标记unconfigured，未配置/未验证真实账户或免费资格。

页面完整展示两份TXT、全部Goal字段、材料和Goal版本、项目/主体/runtime、模型/端点/非流式、阶段范围/键、原预算及明确期限；用户勾选完整范围确认后，服务端复用原gate.approve持久化精确批准。内部 review_token由服务端生成、页面自动携带；用户不手写JSON、指纹、预算或LIVE字段。批准仍是同意，不是运行准入。

新接口位于 `/api/projects/{pid}/natural-trials/{key}`：POST preparation、consent、withdrawal；GET preparation、consent-status。旧工程接口保持。preparation保存独立成对记录，consent调用原批准/当前版本检查；没有新DDL或执行器。gate.revoke只提取共用metadata-only helper，原批准/撤回规则、admit及production_preflight未放宽。

## 恢复与授权边界

准备、批准、撤回丢回执或OUTCOME_UNKNOWN时，只GET原key；不自动重发或另建key。页面仅把project/key写入恢复链接fragment，不持久化token或私有资料；冷页重新连接后为链接中同项目合法原key建立无私有receipt的UNKNOWN占位，锁住准备/新建，必须先GET恢复；包含丢回执后reload。导航清空私有预览与勾选，将sending转UNKNOWN，允许先GET恢复；每次操作代数阻止旧POST覆盖较新的GET。准备后禁用目标选择框，须明确新建准备才能换范围。版本、材料、授权、软件或期限改变，批准重新验证后拒绝。

双方材料READ及SAVE授权在私有成对JSON之前；重复key存在性只查询request_key标量。材料READ撤回后，完整准备GET拒绝；consent-status只读取本人同意元数据，不展示旧TXT/Goal，withdrawal仍可明确停止。配对缺失、错误key/token、跨身份/项目、变更绑定、额外覆盖字段均不能错误批准。写后故障回滚全部准备元数据。

## 实际验证

最终冻结组合 **38 PASS /0 FAIL /0 ERROR /0 SKIP，RC0**，76.26325798034668秒，507源文件运行前后相同，HEAD与工作区当时不变。原始XML SHA256：`dfcd6cae8d113a4762f779d2bdea40fa977f68ea96584007104d9366447152bb`。

其中新增入口：14个实际认证HTTP检查，12个完整交付页面/JSDOM场景、244个检查。页面通过TestClient IPC读取全部21个实际HTML/CSS/JS资产并核哈希，原始60份trial HTTP交互保留。覆盖正常批准/撤回、重复、准备/批准/撤回丢回执、冷页原key、先GET恢复后释放迟到POST、Goal变更、READ撤权、过期，以及真实API400 OUTCOME_UNKNOWN（受控残缺原key配对）。人工浏览器像素/原生浏览器未跑。

新增入口共26项。HTTP主流程和全部12个页面场景实际查询Run、Attempt及非同意预算记录并比较不变；撤权后停止用例核对终态无Run/Attempt。3个重复prepare撤权/残缺配对专测核对拒绝及无私有body读取，不把它们另计为完整业务前后比较。页面不提交Run、阶段批准或admission。测试另将HTTPTransport/AsyncHTTPTransport外发钩子设为失败，均未触发。**新入口的准备/同意/恢复新增Run、槽、模型外发=0**。其余12项是8个旧HTTP接口与4个旧gate回归；其中两个旧admission夹具显式创建并claim测试Run，仅用来验证准入拒绝，不是新入口副作用或实际执行。

Ruff对六个涉及Python文件PASS，JS语法检查PASS。mypy实际检查三个产品模块，最终只有未修改tools.py210/264两项既有类型错误，RC1；首次新增consent Literal类型错误已修复，原始log保留，不称mypy全绿。

## 保留的失败与独审修复

所有开发轮次XML、stdout/stderr、HTTP、页面proof和SQLite夹具均保留；不把多次PASS累计成独立验收次数。首轮7P3F是400/409测试错误码预期；第二轮10P10F含9个新driver旧资产数量魔数错误和1个真实导航恢复缺口；之后10UI PASS。权限顺序修改时错误引用复合表不存在id导致14FAIL，改用request_key后14PASS。随后11UI PASS、悬挂导航专项1PASS/10deselected。

独审与封存前自查推动修复四项真实问题：重复prepare提前整行读取私有body；HTTP400 OUTCOME_UNKNOWN误归确定拒绝；sending导航后无法先GET恢复及迟到响应覆盖风险；冷页fragment已知原key却未锁新准备。原始审查发现保留，修复及实际证据另记，不改写旧结论。

冷页最终补测先实际得到1FAIL/10deselected，再修复无私有receipt的UNKNOWN占位；普通冷页与丢回执后reload两项实际2PASS/10deselected。22c3修复前组合37PASS的完整证据仍留在final-corrected，不作为最新签收。一次修复前审查器在源码epoch切换时记录CHECK_FAILURE（并有其自身旧AST索引假设），原文件保留；不冒充产品失败或最终独审通过，最终重新核定固定9a5f源码。

首个冻结组合178e为 **35PASS/2FAIL，RC1**，原始XML SHA256 `e26982bc971f9124471298fd035f9624ec0ab5f123118e0ec35966ad1983691d`。两个旧admission测试要求400 LIVE_BLOCKED，但新产品源先在 `_qualified()` 精确软件门返回409 VERSION_CONFLICT、消息 `Current software differs from the exact reviewed literal target`。后续仅将该**精确拒绝三元组**纳入旧测试，保留400 LIVE_BLOCKED、所有fee/free/live_allowed额外字段422和账目不变断言。没有更新/repin任何资格target/anchor，没有更换工具或绕过拒绝。

因此最终回归证明明确拒绝及无副作用；本轮新软件没有执行到后续LIVE_BLOCKED分支，不能称该分支已验证，也不能称新软件已qualified或生产兼容。

## 范围与剩余缺口

仅签收准备和同意入口。实际模型生成、实际Source/Cold、完整P-A/P-B、历史正常Cold原错误、生产精确软件资格审查及真实账户/费用资格仍未完成；不新增诊断或盲跑历史Cold。PG、Windows、原生浏览器、人工语义、真实模型/付费API、旧库升级、远端CI均NOT_RUN。本轮没有配置凭据、扩大网络/安全权限、部署、强推或更改main/core分支。

完整原始证据和失败历史位于 `docs/evidence/pa-trial-consent-entry-20261015/preparation-consent-evidence.tar.xz`，MANIFEST逐文件及符号链接校验；public提供最终原XML/结果、原始trial HTTP和UI proof摘录。独审记录随包封存；推送后复核在仓库外记录，避免封存后改写。
