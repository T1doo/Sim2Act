# P2新Goal摘要错误门：独立LIMITED_PASS

2026-10-12，独审`/root/text_logic_review`。仓库`/workspace/Sim2Act`，基线`a747a7aafe7a537858f75bbfa129addd8696d0a6`，分支`dev/own-goal-read-errors-20261012`；root唯一产品作者，独审只写本/tmp。接受范围仅新Goal面板读取/恢复/保存读回的迟到错误门，不扩大功能或F2-T08兼容接续。

结论：**P2 LIMITED_PASS**。独立复现精确旧JS红例，当前定向及四个正常页面全部通过。各组分母单列，不把修前失败、修后通过或其它阶段重复累加。

| 独立执行组 | 实际分母/结果 | exit | pytest用时 |
| --- | --- | --- | --- |
| 精确a747旧JS，新11定向对照 | 11项：4 PASS / 7 FAIL / 0 SKIP | 1 | 9.90秒 |
| 当前JS，同11定向 | 11项：11 PASS / 0 FAIL / 0 SKIP | 0 | 9.76秒 |
| 当前JS，原4正常新Goal真实HTTP/Worker页面 | 4项：4 PASS / 0 FAIL / 0 SKIP | 0 | 64.28秒 |
| 有限附加当前save读回GET失败保留原pending | 1项：1 PASS / 0 FAIL / 0 SKIP | 0 | 0.62秒 |

旧a747阶段作者34、独审43及152项147P/5S原分母保留，不重新计入本P2；父作者本P2其它14原owner页面/5 controlled回归结果也不混入上述独立组。所有独审pytest/Node/Worker进程已结束，已明确通知父作者解除独审freeze等待；不再启动其它测试。

## 精确源与完整性

本/tmp`a747-owner-review.js`由`git show a747a7aafe7a537858f75bbfa129addd8696d0a6:src/sim2act/web/owner-review.js`取得原bytes，SHA256：

`daa6530ba21f4153442cfeaeaac89fd3816967dcc25a398de32592082ea7ac56`

当前`owner-review.js` SHA256：

`c65466c9ad9be536d6b6f47711e41568a56886c5d798f1386950f339cb49d5a3`

冻结`docs/evidence/own-goal-read-errors-20261012/freeze.json` SHA256 `456b9b3db23caa0986cd8129cfc746e220632b8f37bf63296c5029ed2629a622`，379个Git deliverable src/tests，5个ignored egg-info另列排除；规范map fp `8ec8228f078bf5137f0f8f3ffe57579458ccc10467ef54c3d3cfe249f5a247f2`。四组各before/after共8次核379逐文件SHA、路径集合及freeze SHA，全部一致，0差异/0额外/0缺失。

修前与修后每个controlled scenario proof都核真实原JS SHA，未替换产品函数。controlled使用本地原脚本JSDOM、真实规范SHA256与stub Promise排程，不调用HTTP、SQLite、Worker或native Undo；runner的通用数据库配置标签表示隔离默认值，在这些组不代表实际建库。正常4页另用真实TestClient HTTP、隔离SQLite、冷NoModel Worker与IPC可见JSDOM，严格区分两类证据。

## 真实旧红与当前修复

精确a747实际7 FAIL：old-failure-after-new-success、initial-failure-after-edit-aba、initial-catch-edit-aba、initial-catch-new-read、refresh-catch-new-read、recover-catch-new-read、save-readback-catch-new-read。旧脚本覆盖了新CURRENT文字，或在编辑/较新GET后错误落入旧catch；save读回409还清空state及原pending。原11每项proof、stdout/stderr、Node exit和完整log/XML全部保留，不改写旧FAIL。

当前同11全PASS：inner失败只有原read/edit/workspace fence仍有效时rethrow；initial、refresh、recover和save读回outer再校同步捕获的reading代次及原fence，覆盖inner到outer之间的新read/编辑。原有成功门继续阻止旧成功结果与编辑ABA后的成功安装；真正当前initial/refresh失败仍显示错误，并未吞掉全部异常。

save读回显式区分POST与GET阶段：readGeneration=null才允许当前POST确定4xx清原state/pending；GET失败不能据此否认保存效果。失效readBack返回false不进入owner continuation；有效读回同时核代次再刷新owner。附加1项真实当前GET409证明仍显示当前错误、v.state与原key/body pending保留，请求序列仅GET→POST→原key GET，没有自动第二次POST。

## 四个完整正常页面

| 场景 | 完整proof/Node | 冷Worker | 检查/可见动作 | HTTP资产 | SQL语句/旧private求值 |
| --- | --- | --- | --- | --- | --- |
| accept | PASS/error null/exit0 | 2 SUCCEEDED | 40/84 | 20，含CSS1 | 17352/0 |
| reject | PASS/error null/exit0 | 2 SUCCEEDED | 40/84 | 20，含CSS1 | 16661/0 |
| goal-lost | PASS/error null/exit0 | 2 SUCCEEDED | 42/86 | 20，含CSS1 | 16661/0 |
| decision-lost | PASS/error null/exit0 | 2 SUCCEEDED | 41/85 | 20，含CSS1 | 17338/0 |

每页1普通冷boot，从旧source撤权/删除后开始自有Goal编辑/保存、精确Goal绑定新Worker、逐项SIMULATED决定、版本修订STALE与原key不复活、保留旧技术Run读取、新Worker及新决定；两丢回复场景仅原key GET恢复。真实HTTP index/CSS/18JS的全部hash再次核源0差异，全部动作visible/enabled；每页Node stderr0bytes。实际source私有数据及source/初始target两张native GoalCard snapshot屏障全段protected_private_evaluations=[]。只读fixture确认每页本新instance恰好2个AppRun SUCCEEDED、结果版本v1/v2；不借Worker.once布尔值宣称成功。没有停止poll或替换正常interval。

## 产物与局限

所有原产物位于`/tmp/own-goal-read-error-review-20261012/final/`：四组分别`before-exact-a747`、`after-controlled`、`normal-new-goal-pages`、`current-readback-extra`的log/XML/command/result/前后hash JSON，各自`*-artifacts/`内scenario proof/log/exit；正常页另完整SQLtrace/资产/request/action/Node stderr，独立附加driver/test文件及旧JSbytes保留。`results-summary.json`保存各组分母、逐scenario校验、四页精确Run IDs和源hash；manifest单列产物SHA。

本P2没有其它阻断实现缺口，不外推为真实用户语义签收或正式发布。controlled合成historyUndo事件只验证编辑ABA逻辑，native Undo/浏览器并未执行。人工决定均SIMULATED，semantic UNKNOWN、formal publication false、LIVE0。F2-T08兼容接续由父作者下一阶段独立设计/实现，本阶段未验；本轮不修改旧软件迁移状态。

没有写产品/src/tests/仓库或push；没有socket/native/真实付费模型/凭据/CI Forbidden/main/core/force/部署，没有工具或平台拒绝。此前取消的候选安装精确竞态仍永久NOT_VERIFIED，未执行/实现/替代；本新Goal摘要错误门只在本次明确授权范围内，所有既往红轮和UNKNOWN历史保持。
