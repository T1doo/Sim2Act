# 自然试验跨 Run 预算入口：最终有限独立审查

结论：**有限通过，无剩余已知 P1/P2 阻塞**，可在授权的普通开发分支交付。冻结源码 `8e2cce44597a0a5adf057d47271b85ab6d763ed6`；基线 `fae2a3d7de3978671ca9c1c1c19cb8012e731eeb`。生产仅 index.html/natural-goal.js 两文件变更，后台 .py、准入/预算算法、资格锚、权限、Principal/Grant、executor、sender及默认 LIVE 拒绝均未改。先前“专属门和跨 Run 总账都缺少”的概括过宽，本轮已依实际源码纠正；新功能只是现有 P-A 同意面板的显式只读查账入口，不是新增实际运行授权。

本审查亲自做的是只读源码/Git及闭合原文件解析、散列和合同计算；**没有亲跑产品/pytest/HTTP/Worker/模型、读取DB/SQL或联网**。设计、修前P2、修后复核及冻结记录均保留在本新目录；所有旧 sealed 目录未改。

## 实际资格与失败历史

- 第一轮 `85b65963ec91d723185164a4f6ee708fc8e19a27`：3节点执行，2 PASS、UI 1 FAIL，outer13.694769秒。两个既有拒绝节点1.913/1.725秒通过；UI7.269秒在 `trial-recover` disabled 停止，原件仅3检查标签、3动作、10 API、预算GET=0。未完成预算验证，原 FAIL 不改签。
- 修正仅 CJS 增加既有可见 `click("trial-refresh")`，与原 consent driver 首先读当前目标卡一致；原断言、守卫、时限和全部生产/Python字节不变。两个既有 PASS 经唯一未使用 CJS 变化桥保留，不重跑。
- 第二轮仅新 UI：JUnit **1 PASS/9.092秒**，outer12.261176秒；源为上述8e2冻结。故当前 **3唯一选定节点均具通过结果，合计4节点执行=3 PASS+1历史 FAIL**，不是一次完整批全绿。纯工具 needle/patch-context 错误不是pytest，也不加进产品分母。

首轮 manifest18项中15份非DB原件 bytes/SHA已独立核对；3个DB只核size并引用作者提供指纹，未打开内容。两轮原件均位于 `/workspace/natural-trial-budget-view-20261018`，没有复制DB或大原件树到本审查目录。

## 最终原件复算

`closed-evidence-audit.json`及可复算的纯文件脚本/原stdout、stderr记录PASS。审查核对第二轮697执行输入 before/after/current、133生产文件SHA，零漂移；生产字节与修后预审记录相同。两source的Git差异确为CJS一行。

最终原页面：**48检查标签（45实际页面流程标签+3合成validator负例标签），14动作，26 API GET+27实际资产=53页面HTTP，1次boot**；另8份已捕获 fixture HTTP，共61份已保存HTTP记录，不声称覆盖fixture捕获开始之前的请求。HTTP完整原文及其SHA、全部27资产的字节与当前源SHA已独立重算。4项 pure helper记录为原实际回执副本ACCEPTED和三项REJECTED，均明确 `SYNTHETIC_VALIDATOR_ONLY_NOT_HTTP`，不算新增pytest节点或真实HTTP故障。

真实页面预算GET恰为 `[409,200,200]`：批准但无账本时409清空旧私有scope/账目并保留原键UNKNOWN，先原键GET恢复，再选择主试验；双击只产生一个200；另一次完整实际200仅延迟投递，切换另一原键后，旧回调前后新scope完全一致且无额外请求；普通项目切换清空内容。页面全部GET，0 POST/下载。

独立重算原contract和nested approval指纹、原approval key及全部Scope，核账本与projection一致：单generate Run、一槽、wire100+输出预留1024=1124，partial usage prompt=5/completion=null/total=null，状态RECONCILING、halted=true、known total分量0。Source/Cold仅空阶段行，本轮不是三阶段实际业务运行。原预留成功、失败、未知均不退还，数学未预留容量不是发送许可。money保持 **UNKNOWN/actual_paid=null/currency=null/NOT_LIVE_VERIFIED/live_allowed=false**；paid_cap=0不等于已验证实际费用0。

fixture确为正常API材料/Goal、两个准备与LIVE_BLOCKED同意记录，以及一个生成Run仅 `store.claim`；通过现有真实 gate.admit配exact SyntheticOnlyFeeAuthority和原reserve/unknown settle建立合成账本。保存3个Permit均SYNTHETIC_ONLY/live_allowed=false；不创建有效LIVE token。provider trap未触发，provider记录为空，Worker/model/真实请求0，未使用sender。

作者pytest实际比较全部55表before==after，proof保存整体FP、55张表FP/行数和空changed列表。本审查核其相等和严格执行oracle，**未独立重算55表原行**，因为未保存全部rows且本轮禁止读DB。

原静态P2（错Run/假KNOWN0可与原ledger脱节）已补slot→stage/usage/status校验；修前发现未覆盖，修后字节桥及本轮明确合成validator拒绝保留。未见新增权限、后台写入或真实发送路径。

## 保留限制

本轮只验P-A查账。未新增P-B页面、完整3/2/2 Worker试验、实际READ撤权/跨账号或held项目、digest ABA场景；这些不能由普通项目清空或代码围栏冒充实际资格。Windows/native、PG、远端CI、真实模型、真实免费/强制不可收费机制、语义和正式发布未执行或提升。真实生产resolver/fee authority/sender仍未注册，LIVE继续拒绝；本审查不背书未来push/部署。目录在manifest生成后停止全部写入。
