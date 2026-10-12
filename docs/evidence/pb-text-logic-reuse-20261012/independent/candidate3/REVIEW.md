# 候选3独立审查：需要修复，不能签通过

独审 `/root/text_logic_review`，2026-10-12。产品基线 `e2b856bb453fc74452583fa10843148758e2d9b9`，分支 `dev/pb-text-logic-reuse-20261012` 的未提交候选3。冻结文件 SHA256：`651253961033fd7afd08b3a2d138470885a7ca85433658821b1346ffa404b99c`。本审查全部测试前后核对冻结文件中的378个 src/tests 文件：零缺失、零哈希差异；没有把不同候选测试相加成通过。

结果：新测试17 PASS / 6 FAIL；独立补充API数据污染9项中6 PASS / 3 FAIL；有限相关回归88 PASS / 1 SKIP。候选3尚未通过完整合同，不能以相关回归替代新链的失败。

| 测试轮 | 数量 | 退出码 | 时间 | 日志/逐项证据 |
| --- | --- | --- | --- | --- |
| 两个新作者测试文件独立重跑 | 23：17 PASS、6 FAIL | 1 | 70.90秒 | `new-tests.log`、`new-tests.xml`、`new-tests-result.json` |
| 独立API污染与授权/seal负例 | 9：6 PASS、3 FAIL | 1 | 26.11秒 | `test_independent_api.py`、`independent-api.log`、`independent-api.xml` |
| 有限相关回归 | 89：88 PASS、1 SKIP | 0 | 179.02秒 | `related.log`、`related.xml`、`related-result.json` |

每轮的完整命令见各 `*-command.json`，前后指纹见各 `*-before-freeze-check.json`/`*-after-freeze-check.json`。汇总见 `results-summary.json`。UI三种失败场景的实际请求、可见动作、资产哈希及完整错误均保留在 `ui-artifacts/`。每轮一个既有 Starlette/httpx deprecation warning，未安装或改依赖以消除警告。

## 真实缺陷

1. **独立授权单边污染被Python相等掩盖。** `text_logic_reuse.load` 用 `public(p) == expected`、`frozen == p` 检验canonical和双seal承诺。Python把`0`等同`False`、`False`等同`0`、`64`等同`64.0`。独立测试分别只改一条新`internal_approvals.payload`的`model_requests`、`formal_publication_enabled`、`recipe.max_lines`，并更新该行fingerprint；两个delivery_graph seals完全未动。三个GET均返回HTTP200/ACTIVE，应为VERSION_CONFLICT/409。这不是全量账本管理员重写，也没有改原来源。

   必要修复：原canonical、公私有payload、双seal snapshot、body和candidate等JSON完整性比较统一使用规范`fingerprint`，对期限及身份/Schema相关字段继续严格类型/闭集校验。修复后保留并重跑三个原始独立红例，不删失败日志。

2. **普通冷页面会打开旧来源应用。** 两个新文件里的三个UI场景`valid`、`authorization-lost`、`binding-lost`，均在原source撤权/删除后冷boot失败：`cold project logic and target preview do not open retired source lineage`。原因是全局`refreshApps`调用`refreshApplicationUse`；`_csv_instance_candidate`对literal返回None，use.js因此自动对源app做GET。后端409虽保留原门，但页面已尝试打开旧来源，违反合同。

3. **冷页面目录仍有旧候选私有SELECT。** 静态审查发现`api.apps`默认目录SELECT每个app的candidate用于推断hint，`conditional_apps.listing`也SELECT整项目app_drafts再用candidate.namespace过滤。即使仅禁止旧app GET，这两处仍不满足整段旧私有单元读取屏障。已有主链SQL屏障测试未覆盖全局冷boot这些目录。

   建议最小修复：UI使用新增`metadata_only=true`目录；`/api/apps`只取id/name/project/runtime及Grant tool元数据，以runtime是否具有data.aggregate_csv作为发现hint，随后显式打开仍严格完整检查。条件报告metadata目录依据独立task_extractions的family kind先识别ID，轻量列出，再由显式打开load；不得遍历原candidate或以JSON投影读原candidate判家族。默认API可保留既有兼容行为，但冷页面必须走无旧私有内容路径。修复后的正常可见JSDOM冷boot应置于与Worker相同的SQL单元屏障内。

## 作者测试预期问题

`test_cross_identity_budget_and_expiry`和两个容量参数用例对HTTP409的预期与平台当前BUDGET_EXHAUSTED映射HTTP400不符；请求得到预算拒绝，不是写入成功。它们在状态码assert处提前失败，不能据此宣称其后期限/无写入断言已通过。应按当前API合同核HTTP状态、精确error.code与全表无部分修改，修后整项重新跑。

## 已实际支持的有限结果

新主链TXT/MD两个参数用例实际通过：成功初始来源完整校验后签发→旧user/runtime材料撤权及资源删除→独立logic冷读取→新目标绑定→fresh Store/API/普通字面Worker→未见Gamma得正确新行引用、错误term保留失败历史，原私有单元SQL屏障在该API/Worker范围内未触发。它们还检查fresh runtime无token、唯一目标read Grant、typed版本及原对象保留；这不覆盖上述冷boot目录缺陷。

作者新用例中的target/body精确指纹负例、task marker删除/改写、authority seal缺失、runtime增加Grant或token、logic不可逆撤销、enqueue后logic/user/fresh-runtime撤权、绑定事务回滚及最终typed写中expiry回滚均实际通过。独立补充用例另证实授权wrong proof/wrong Release/无效consent/无效key拒绝且无写入，binding任一seal缺失后新app读取拒绝。

相关88项涵盖旧goal文本来源、旧registered文本成功/污染/marker门、有限CSV logic来源/目标负例、普通AppRun外事务计算与最终gateway、内部生命周期。不运行旧registered recovery UI、其late-latest-digest或任何已取消目标的替代probe。唯一SKIP为`test_internal_lifecycle_application_role_no_grant_expansion`，理由是需要显式隔离PostgreSQL；本轮禁止PG，因此保持SKIP/NOT_RUN，没有连接PG。

## 完整性及剩余边界

独审只写本次`/tmp/pb-text-logic-review-20261012`。测试设置显式去掉SIM2ACT_TEST_DATABASE_URL，使用各自/tmp隔离SQLite；模型执行仅已有MockTransport来源fixture及普通NoModel字面Worker，没有真实/付费模型、网络凭据或权限变更。没有产品/作者tests修复、push、部署、原生浏览器、Windows或旧源码升级动作。

所有独审pytest/Node/runner已经退出；冻结后的最后校验仍378文件全一致。已向root明确通知解除本审查的编辑等待，下一候选应独立冻结再验证。此报告形成期间只写/tmp，不继续读取或运行正在修改的候选产品。

尚未验证：修复后的完整正常可见UI、完整新合同、真实语义/owner、PG/应用角色、Windows/native、真实设备崩溃、全旧源码升级、正式发布/部署及新SHA远端CI。owner PENDING、semantic UNKNOWN、LIVE0、formal publication false保持。

用户已取消的精确候选安装竞态对照单独永久NOT_VERIFIED。本轮没有执行、实现、改名、换工具或变通重试，也不以冷Worker/权限检查通过关闭它。没有发生工具或平台明确拒绝；无审批绕过。
