# CSV Goal修订离返恢复：独立最终审查

**有限通过本轮修复的工程门，未发现产品 must-fix。** 产品冻结 `776d76581c7f811f39af584283578d9b252a994b`；最终测试修正 `849a931f7dbb8926ca9cbe166c3cfba3527dbf0a` 仅修改 `tests/csv_goal_revision.cjs` 的采用批准oracle，126个产品源文件及schemas字节不变。共享仓库只读；两份快照均从对应Git SHA新建，未用旧bundle。

## 精确执行与去重

| 独立轮次 | pytest节点调用 | 实际结果 | pytest / JUnit秒数 |
|---|---:|---|---|
| 776组A | 16 | 15 PASS，1 SKIP | 475.89 / 475.894 |
| 776组B | 5 | 4 PASS，1 FAIL | 454.38 / 454.381 |
| 849仅采用离返 | 1 | 1 PASS | 102.43 / 102.433 |
| 849仅旧应用使用 | 1 | 1 PASS | 31.86 / 31.858 |

776完整21节点为 **19 PASS、1 FAIL、1 SKIP**，不改写为全绿。849仅两个target，没有全21新SHA重跑。合计23次pytestcase调用，其中1次SKIP没有执行业务；保留1次失败后，最终有效覆盖 **21个唯一用例PASS =776的19 +849的2**。不是23个唯一测试，也不把作者复跑再加为独立唯一数量。每轮各有既有Starlette/httpx弃用warning；本独审未运行mypy、全库或远端CI。

776失败确为测试oracle形状错误：adoption POST返回最小id/fingerprint提示，产品原有POST后GET以及恢复GET返回完整inspect批准payload。旧测试把完整显示与最小POST对象作deepEqual，必然失败；未发现产品丢弃证据。849仅将oracle改为导航前GET完整批准并绑定POST id/fingerprint；失败原log/XML/page都保留。

776旧application_use跳过来自快照cwd的 `node -e require.resolve('jsdom')` 探测：仅scripts子目录的node_modules链接不足以满足该gate。849补一个未跟踪的快照根node_modules链接到现有只读安装，实际probe RC0后仅补跑该旧case。没有网络安装、权限或tracked源码修改。初次collect-only还因选择性快照遗漏import所需bounded-agent gold而报错，尚未执行测试；从同SHA补齐该fixture目录后收集21成功，初collection.log仍保留。刚才进度消息中旧回归秒数曾写为29.89，准确原件为31.86，上表已纠正。

## 父级三个阻断点均已闭合

完整产品HTML/CSS/scripts在JSDOM执行，真实FastAPI TestClient/RPC走现有版本/实例API和NoModel Worker。preview已受理未发CHECK、version approval未commit、adoption approval未CAS三个精确停止点，离开再返回后均恢复完整server-frozen JSON，冻结amount→quantity两列有值且不可编辑，原勾选清除，下一动作先禁用；显式新勾选后才继续。不是仅断言按钮visible或entry存在。

除运行现有oracle，本审查独立读取原始请求序列并断言：776 preview/release以及849 adoption，从基线后第二次GET/context到下一显式POST之间均全为成功GET，包含原preview/key；版本阶段还读取CHECK、原version approval及当前live approval；采用阶段再读取Release和原adoption完整批准，GET payload与之前已接受完整GET一致且绑定POST提示id/fingerprint。此段0POST，下一POST必须真实存在并指向正确原key/CHECK或批准fingerprint/CAS路径。完整序列和源码SHA在strict-return-sequence-proof.json，未借用早期some(GET)满足新GET断言。

UNKNOWN恢复仍只走原键GET。独立lost-adoption原件实际得到一次原CAS POST200后故意丢失回执；原实例GET有精确approval_id、previous/target Release、revision+1、原data_version、principal/project/app/runtime和Release fingerprint，匹配原批准历史；没有第二次commit POST。独立硬校验找到4条匹配GET。新结果漂移分支显示原冻结/当前版本，Release与CAS禁用；只有显式原键CHECK取得NOT_ACCEPTED/TX_ROLLED_BACK证明后才允许新意图。没有通过丢弃unknown或另发key绕过。

相关8个API用例、9个页面用例和4个既有回归均有有效通过来源。10份页面原件（含旧失败和849替代）中，8份完整送达链实际保留旧Run30、同实例新Run5、Goal v2 frozen contract和新Run人工PENDING；navigation专测隔离，776错误oracle用例在CAS前停止，不冒称这两份已完成新Run。已保存CHECK角色目录过滤、错误身份/实例/版本、漂移/撤权、原历史和权限边界继续覆盖。

## 背景HTTP错误与输入完整性

页面原件保留25条GET `/api/projects/{pid}/protocol/contracts` HTTP400（RESOURCE_UNAVAILABLE / Evaluation asset unavailable），来自两快照没有包含旁路protocol evaluation assets `docs/evidence/protocol-store-loop-20261006/evaluation`。本轮未中途补该旁路输入或隐藏错误；不能声称所有HTTP成功，也不将此扩大成protocol验收。另有2条明确故障注入后的CHECK POST409，均携带NOT_ACCEPTED/ABSENT/TX_ROLLED_BACK证明，属于rejected/return-stale预期边界。全部路径、方法、状态、错误体在独立proof中逐项列出；三个正式离返恢复片段自身均全GET200。

两快照分别对636份tracked输入做前后SHA256比对完全相同：126 src、471 tests、7 schemas、32份同SHA import gold目录文件。776与849仅一份测试driver不同。来源为Git归档，source-before/source-after列明每个文件；额外gold与初次收集缺项明确记录，未冒称无附加fixture依赖。所有测试SQLite、actual-http、page-result、stderr、log和JUnit留在各自临时目录，原始失败和SKIP不覆盖。

## 范围和剩余缺口

这是合成SQLite/TestClient及一项真实loopback HTTP/JSDOM工程验证；不是原生浏览器、像素、PG、Windows、真实模型/语义/人工场景、远端CI或部署验收。NoModel拒绝任何模型调用。未新增凭据、费用、安全权限、安装、服务部署、Grant/executor或访问绕过。更早6ed三阶段反例，以及作者WIP wrapper比较和CAS观察15秒超时原件继续由原报告保留；后续通过不改写旧结果。本报告不代替root普通推送后的完整SHA、远端和工作树核验。
