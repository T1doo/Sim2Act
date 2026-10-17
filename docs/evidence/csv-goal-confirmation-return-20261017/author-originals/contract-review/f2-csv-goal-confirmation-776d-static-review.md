# CSV Goal 修订确认重入：冻结合同独审

冻结 `776d76581c7f811f39af584283578d9b252a994b`，分支 `dev/csv-goal-confirmation-return-20261017`，相对基线 `6edb626c4203def2a735006e860dcbca807315df`。**有限静审未发现剩余必须修复项；运行验收仍待root正式21项原件，不把此结论当21项已通过。** 本审只读Git/源码/测试与AST，未执行测试、HTTP、Worker或模型，未改仓库。

## 本次确切变动

5份文件：csv-goal-revision.js、use.js、页面driver、参数化Python测试及原功能说明。六份相关后端csv_goal_revisions/lifecycle/internal_api/db/worker/app_jobs与6ed逐字相同；原批准、当前权限、版本/Grant、独立CHECK、300秒期限、CAS和既有请求账本均未放松。Python测试中除页面参数化函数外，其余11个旧helper/test函数AST相同；原4页面case保留并增5case，共9页面参数。

新view的reviewReady初始false，必须GET当前context和原key接受链一致才能显示完整冻结内容并启用新确认。核principal/project/app/runtime、Release及fingerprint、instance revision/data_version，再校完整冻结context/preview；CHECK依原request hash/run，Release批准依原check/snapshot和当前generic approval，CAS依inspect_switch_approval的当前预检。完整Goal、材料/影响、列映射、CHECK、Release及采用批准共同展示；from/to由冻结旧列和新列恢复并禁改，ack全部重新清空。

## 当前归属、期限与迟到回调

here同时锁applicationUse对象/identity/project/generation、controller、DOM、连接/工作区代际，以及iid/Release/revision/data_version签名。每个恢复GET后校here，CHECK request hash await后再校here；签名变更时旧链不能令新view就绪。use.js现在await恢复renderer，返回后再用原current()拦跨工作区/选择代际的父级按钮更新。同signature常规轮询仍可复用当前controller，不以readGeneration永久废掉它。

Release和CAS新确认均要求finite未过期expires_at，显示/点击门都有约束。历史GET version-approval不能单独当当前批准；额外generic approval检查id、当前归属、完整snapshot、消费与expiry。已经有精确Release的consumed批准只作历史，不能再启用保存Release。CAS重新GET原adoption对应实际inspect_switch_approval，保持服务器原data/hash/grant/dependency/compatibility预检。

403/409清当前UI和确认，不删原接受/unknown handles；新view仍须GET重新鉴权，不会把缓存正文直接恢复。未知阶段继续使用原steps.body和key，request恢复分支仅GET；新确认门不阻断原key恢复，也无fallback POST或新key。accepted/unknown仍不能reset，只有原完整NOT_ACCEPTED/ABSENT/TX_ROLLED_BACK证明或原终止CHECK允许显式新intent。

## 两处WIP实质问题已修复

- Release从列表items取plain row，单条GET多envelope。冻结版逐项精确比较原row所有字段，另要求namespace INTERNAL_ENGINEERING_ONLY和formal_publication_enabled=false；snapshot/fingerprint/approval来源未被宽松比较替代。
- 丢失CAS响应后，已切到target的同signature pending controller曾被复用，并自动请求已采用状态不支持的/context。现在原CAS已获精确历史证明后先clearCsvGoalRevision，再readApplicationUse重建终态。确认必须匹配同approval_id、from/target、revision+1以及当前主体/项目/app/runtime/Release fingerprint/data_version；不能因另一个批准切到同target就把本unknown误认接受，也不重POST。

## 结果版本漂移的有限恢复

staleCheckReady与普通reviewReady分开。仅满足原instance data_version单调增加、其他context全同、已有preview且从未有CHECK step时，读取当前context与原preview成功后展示旧冻结内容和当前版本差异，清ack。仅用户明确确认后可按原body/key发送CHECK，由服务器current=True边界拒绝并出具原NOT_ACCEPTED证明；Release、CAS、换列、新key仍禁用。新intent须在证明后再次明确reset，不凭客户端漂移自行建立。Goal/权限/图/软件/批准过期等其他漂移不借此开门。

## 测试与尚待证据

页面driver保留实际API与NoModel Worker链，并增加return-preview、return-release、return-adoption、return-stale、lost-adoption。三个未发送确认返回要证明完整payload精确、旧ack清空、0自动POST，再继续实际CHECK/Release/CAS/新Run；stale要先精确旧key拒绝后才新key；丢CAS要求实际200被丢且由同approval历史GET-only恢复至accepted。原目录/旧结果/新Run PENDING声明继续保留。

外部页面watchdog150→240秒和lost-CAS hold观察45秒是测试诊断窗口，必须如实记录，不能称生产预算延长或吞失败；后端Run/lease/CAS代码未改。此时root正式全相关21项（8 API +9 page+4旧相关）运行中/待原件，本审没有独立运行结果。恢复GET checks在首次SUCCEEDED可能写CHECKED封存，0POST/0新Run不等于全库零DML。

不新增功能、模型/executor/Grant/部署；新功能继续暂停至必要回归与独审完成。Windows、PG、真实模型/语义、原生浏览器、远端CI及既往未知事项不由本静审补签。

机器证明 `/tmp/f2-csv-goal-confirmation-776d-static-proof.json` SHA256 `bc70753a1dc1c521df7d9d6143f8f1d1ee2612c3bff949821800edf73acecb24`，含5文件冻结hash、6后端不变hash、11旧函数AST比对、9页面case及有限结论。
