# 自然应用交付图与人工锁入口：有限最终独审

结论：本轮限定范围通过，未发现阻止普通开发分支交付的 P1/P2。修复的是用户真实可用入口：保存的自然 P-A/P-B 应用原先在 showApp 提前 return，无法派生局部修改所需的图，人工锁控件也被隐藏。现在复用既有图/锁控制器接通。**实际资格只新增 PA 一条页面 case；公共自然 namespace 的 PB 适用性经源码审查，不声称本轮新跑 PB。**

执行源 `d9e19b2829221909b49fd075b721d4e831d711a4`；基线 `4a5fa568d2aefcbe59ef2f14c5a58414073bbe0b`。独立 Git diff 确认生产仅 `src/sim2act/web/app.js` 和 `src/sim2act/web/manual-locks.js` 两文件：await openInternal 后重新核 generation/pid/identity/selectionCurrent，再为严格自然 namespace 打开图；不保留开页临时 callback，使正常 workspace handoff 后图可继续用。manualOpen 增加同 namespace，原 CSV/Report 条件保留。没有修改后端、ActionSpec executor、API、Principal、Grant、权限或产品 Run300/lease30。

原规格依据为 V5 产品 §9.3（`docs/sources/V5/平台产品设计.md:429`）与 F2-T07/AT13（`docs/sources/V5/分阶段开发计划.md:99`、`:343`）。后端 load_family/自然 origin/当前授权、图与锁 CAS、LOCK_CONFLICT 原门保留；CSV列/DAG专控仍有独立family guard。此前完整逻辑页面 fixture 预派生图不能证明这个新入口存在；本轮正面验证 fresh 无图时可以从页面开始，不重跑已经通过的 CHECK/新Release/THIRD/cold 长链。

## 实际结果与独立复算

作者原件根 `/workspace/natural-graph-controls-20261018`；成功 case 为 `actual-tmp/test_fresh_natural_app_derives0/`。`execution.json` 为 exit0、91.792321818秒；`junit.xml` 一例 `test_fresh_natural_app_derives_and_controls_edit_locks_from_page` PASS、87.861秒。44是页面checks，不是pytest数量。一次成功执行包含26个页面actions、54 API、27静态assets、1boot，共81页面HTTP。

本审查没有亲跑产品、pytest/collect、HTTP、Worker、模型、SQL或网络，没有读取最终 fixture.db。通过本目录 `final-artifact-audit.py` 对闭合文件/Git独立复算（原stdout、空stderr及JSON保留）：

- 693项执行输入 before/after完全相等，逐项对当前文件吻合；tracked生产133份全部对冻结Git blob一致。proof直接过滤 `.py/.js/.html/.css` 的生产131份与tracked133是两个分母，未混称。另2份为 `src/sim2act/text_software_anchors.json`、`src/sim2act/text_software_qualification.json`，同样纳入tracked133与693零漂移。
- `results.json` 的54 API与`http-responses.jsonl`的54条完整行逐项集合吻合；实际request body JSON/原文SHA、response完整UTF8文本/JSON/SHA复算通过。27assets的长度/SHA与冻结源码吻合；三份实际graph的canonical graph hash、app/project/候选绑定、stable IDs与锁false→true→false通过。
- 普通目录明确选择保存的自然PA及空实例；打开零POST。正常图GET409证实没有fixture预派生图。七次POST严格为 derive201、lock201、derive201、preview400、unlock201、derive201、preview201；双击没有重复POST。锁前后独立确认、当前node/CAS和原key receipt GET一致，锁revision1→2，解锁后false。400回执的LOCK_CONFLICT、NOT_ACCEPTED/ABSENT/TX_ROLLED_BACK、原key与独立request fingerprint已核；成功preview完整fingerprint与原instance/最终graph绑定已核，仍PENDING/UNKNOWN。
- 工作区正常projects→apps返回后实际GET图成功，未再POST；旧draft、Release和空实例重新读取相等。CSV列/DAG控件隐藏，拒绝preview不能CHECK或创建版本；成功preview也须独立确认才能CHECK。本轮没有提交CHECK、业务Run、版本审批/commit、下载或故障注入。
- 成功fixture仅3次正常parallel自然生成Mock；页面模型、业务/CHECK Worker均0，真实模型0。两次attempt累计6次Mock。没有把模型未运行当真实语义验收。

## 表与journal证据的精确限制

冻结Python实际成功执行了55表snapshot比较：50张protected表逐行相等；5张graph metadata表的旧行保持，`exact_graph_metadata`把新记账收紧为11条精确(kind,scope,key) journal、原request/response/双seal与fingerprint、3个anchor revision1/2/3、唯一state/末anchor、精确sourceVersion及最终unlock锁。锁冲突请求key不得留下journal；旧Release/实例/AppRun/typed/Attempt/Grant/Principal等不变。最初广泛metadata白名单的P2证据缺口已在资格前同case收窄，原审查意见留在本目录，不改签历史。

这里没有保存巨大before/after全表快照或11条存储journal原行，proof仅保留前后fingerprint、50 protected/5 changed列表及PASS。**独立审查已读严格执行oracle、核冻结字节/JUnit PASS，并从实际七次HTTP重建11个expected journal header；没有独立重算50表原行、11个stored journal fingerprint、实际anchor/state/sourceVersion行。** 因此表结论是“成功pytest实际断言通过”，不是独审重新查询数据库或复算完整表原件。原DB仍由作者外部保全，不因减少交付包而虚称这些大快照存在。

## 首轮失败与交付边界

本阶段一条唯一pytest、2attempt：当前1PASS，首轮`d1b07e4581a2681bb10ca27104036512c3a7d7ed`为1FAIL/exit1，外50.714888247秒，完成23checks及4POST，到实际400 LOCK_CONFLICT。首轮14原件、4,880,461bytes在failed-1保持，已独立逐字SHA核验。未到unlock、成功preview、workspace尾段及Python终态metadata helper。原UIstatus文字没有单独留存，错误文案原因只根据api和naturalLogicWrite catch使用detail的代码推断，不能将推断说成恢复了首轮页面状态。

d1b→d9唯一变更是CJS显示文案predicate从包含字面LOCK_CONFLICT改为包含该实际响应error.message及换行；独立Git字节替换核验通过，HTTP400/code/path/请求key及所有后续oracle不变，133生产逐字不变。它纠正了测试文案预期，不是为了通过而降低服务端拒绝或版本/权限要求。该失败不会被当前PASS覆盖；完整记录见`first-failure-and-oracle-correction-review.json`。

源码与实际资格到d9为止。本报告不预先背书之后的交付文档、归档或远端push；没有自行fetch或访问远端。普通用户入口修复可交付不代表R0/全部AT13/14/15、PB本轮actual、双账号隔离、实时调度、真实模型/真人语义、原生浏览器/Windows/PG、远端CI或部署通过。旧永久取消安装窗口、exit139原因未知、旧满盘证据缺件均未重试或补签。

只进行了本轮必要静态/文件核验，没有新增产品测试或旧矩阵。原件以已有HTTP完整文本、日志、hash和本报告支持，不新增DB副本、整树或大bundle。本目录生成`sealed-manifest.json`后停止全部写入；所有此前sealed目录保持未写。
