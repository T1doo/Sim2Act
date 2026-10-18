# 805afe60 独立有限审查与实际测试

结论：**PASS_BOUNDED**，限定静态审查无剩余明确阻断，**7 个唯一定向用例具备通过证据，分两批执行**。原批是6 PASS / 1夹具FAIL / 1 deselected，随后仅纠正真实stale-CAS夹具的节点1 PASS；不是原805测试模块的单批7项全绿。

生产冻结：`805afe60cdd94d6d4679e0da9c1f7fde752f67d2`。根为唯一仓库写入者；本独审未改根仓库、提交、推送或触发CI。[最终机器证明](final-proof.json)、[原批真实JUnit](junit.xml)、[纠正CAS真实JUnit](corrected-cas/junit.xml)。所有自启命令已结算。

## 输入与独立性

通过git cat-file逐文件读取冻结提交的blob，校验Git对象SHA和SHA256后放入独立snapshot。完整628个源/测试/schema/config/既有金标输入，前后零差异：[输入前](input-before.json)、[原批输入后](input-after-primary.json)、[最终输入后](input-after.json)。运行时包导入路径核为snapshot/src，既有Python 3.12.14/pytest9.0.2环境，无安装；[环境](environment.json)、[实际命令](command.json)。

首次启动仅collection ERROR，0测试执行：src/tests快照漏带传递导入所需的既有gold JSON。原始[日志](collection-error/pytest.log)/[JUnit](collection-error/junit.xml)/[命令](collection-error/command.json)保留。补取同冻结SHA的3份gold/source-a/source-b后运行原节点，未修改产品、原测试或oracle。

## 7个唯一合格覆盖

| 用例 | 真实行为与原件 |
| --- | --- |
| 首次提交拒绝 | wrong hash和stale dataVersion均409/DB不变；未具App授权B的cold POST403，50条SELECT观察确认正文屏障。[原件](pytest/test_material_preview_rejects_0/actual-material-early-rejections.json) |
| A撤权 | 撤销原App runtime精确resource.read Grant后，cold preview/check均403；38条SELECT正文屏障；原metadata cancel成功CANCELLED，无当次operation。[原件](pytest/test_revoked_A_B_cold_preview_0/actual-material-revoked-cold.json) |
| B撤权 | 同一精确App read授权撤回后，cold preview/check403、原metadata cancel成功且无求和操作；原件含SQL。[原件](pytest/test_revoked_A_B_cold_preview_1/actual-material-revoked-cold.json) |
| A内容漂移 | 真正B CHECK成功后测试夹具变更A content+hash，旧proof的新Release批准409/拒绝调用DB不变。[原件](pytest/test_material_hash_drift_after0/actual-material-hash-drift.json) |
| B内容漂移 | 真正B CHECK成功后变更B content+hash，旧proof批准409/DB不变。[原件](pytest/test_material_hash_drift_after1/actual-material-hash-drift.json) |
| canonical JSON双seal重签 | 同一fixture中将ctx.goal.version 2改2.0、material.revision 1改true；两seal、普通payload/preview哈希均重算。两次GET409且DB不变；逐次恢复原seal后均200/原FP/DB不变。[原件](pytest/test_material_canonical_json_r0/actual-independent-canonical-json.json)、[实际独立测试源](test_material_contract_independent.py) |
| 真实stale CAS | B测试前置授权和public derive先于新键A2 public preview/CHECK/采用，后续不再改Grant；B CHECK/Release/采用批准后，原A2真实新运行sum5/resultVersion2；旧批准CAS409、拒绝DB不变，业务实例仍revision2/data2/原A2 Release。[原件](corrected-cas/pytest/test_material_stale_cas_after_0/actual-independent-material-stale-cas.json)、[实际HTTP](corrected-cas/pytest/test_material_stale_cas_after_0/actual-http.json)、[独立测试源](test_material_cas_fixture_corrected.py)、[命令](corrected-cas/command.json) |

## 保留的原FAIL与修正资格

原805的stale-CAS夹具在A2采用后才新增B Grant并derive，A2 origin authority和current canonical authority不同。最后HTTP为M采用批准GET200，之后jobs.enqueue实际A intervening被既有eligibility拒绝：`Graph, authority or manual locks changed`；尚未到CAS，不能当CAS覆盖。[原日志/traceback](pytest.log)、[原HTTP](pytest/test_same_instance_material_ad0/actual-http.json)、[两个真实authFP与零intervening Run诊断](stale-cas-failure-diagnostic.json)。生产保护未放宽。

仅纠正测试前提顺序，保持原数据推进和409/DB不变断言；165.51秒1 PASS，不重跑原6 PASS。根已合入相同helper和case。最终[root函数bridge](root-function-bridge.json)确认helper源码逐字节相同；case仅引号/换行格式不同，完整AST相同（SHA256 `5466e6d59a4f773a0a47912b9175a7060f9d2421e32150e0d24269a68dd09da1`）；既有prepared/dump/proposal/preserve/reject/no_private_bodies原文与805相同。两函数的双方源码SHA与AST SHA均在bridge，不冒称case原文字节相同。根129个src文件也逐件对805零差。

## 最终静态审查

[静态证明](static-review.json)涵盖全部13个冻结差异，包括两JS与API契合。原v1 effective/calculate/eligibility/goal_spec/checked及column.effective_next AST对db2228全同。新严格M请求和namespace双封条复用；A/有效父材料/B先授权；有效图独立加入已授权B，保留canonical锚；原CHECK→独立oracle→精确批准→原iid CAS→Run/逐次owner策略接通。没有新增executor、表或产品Grant路径。

非作者只读复核：use.js仅M或已验证材料谱系按本Release的Reference读取冻结common preview，核iid/owner/project/runtime/parent/effectiveFP/resource/hash，显示B及原Goal来源，不取移动context。材料模式沿用原阶段与原键GET恢复；UNKNOWN禁退，未提交返回保留ledger。实际页面运行由根执行，本独审未重复或计入UI用例。

[完成fixture的只读SQL统计](actual-post-test-database-counts.json)覆盖8个fixture（含原失败）：23个Run，模型attempts=0、reservations=0；Worker显式使用NoModel（若request被调用立即AssertionError）。此统计不新增测试场景。

只含合成数据/Linux/SQLite/ASGI与NoModel。未执行真实模型、真实语义/用户场景、Windows、PostgreSQL、原生浏览器、远端CI或部署；根正例/UI不计入本独审执行数。旧满盘独审报告缺失未补回；a05可读证据补充的独立核验另见此前a05-readable-audit.json。
