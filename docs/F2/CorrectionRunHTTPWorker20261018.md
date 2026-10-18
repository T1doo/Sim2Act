# 修正回执入口的实际 HTTP/Worker 验证（2026-10-18）

产品基线 `89c3663089bd94385ff461c30be4c82d97fb68b2`。本片不改产品代码、权限、一次修正合同、预算、租约或时限。仅补已有页面测试的进度阶段、原件保存、异步就绪判断及已成功 Run 的明确冷页恢复分支。

## 实际结果：保留 fresh FAIL，续验单列 PASS

唯一 fresh `test_visible_rejection_correction_and_independent_owner[pa-normal]` **FAIL**，pytest285.58秒/外289.175秒，输入零漂移。正常合成 fixture 实际生成候选、保存原结果及人工拒绝；页面预览并明确确认修正，POST202、原key GET200；新按钮实际打开精确 child 的 **QUEUED** 进度，尚无成功成果可验收（8项页面检查通过）。该 child 随后由普通 Worker **一次 claim 成功 SUCCEEDED**，MockTransport1次，未改时钟、预算或 claim 上限。

失败断言紧接手动刷新检查 owner 选择，未等待与后台轮询交错的有效读取结束。原始 HTTP 随后确有该 child SUCCEEDED 与同 child owner200/sequence0/PENDING；这证明后端完成，不证明失败断言时 DOM 已就绪。首轮不改签 PASS，不声称首轮后置历史/递归断言已执行。

保全首轮失败 DB 的精确快照后，**在原库、原实例、同一已成功 Run** 冷页续验：原key GET恢复 → 新按钮 → 同 Run成功成果/PENDING → 空白逐项选择 → 模拟人工 PREPARE/DECIDE。该独立续验 **PASS /117.269秒/31检查/52有效交互/55前端请求**，没有 Worker、模型发送或 correction POST，没有 clone/重建/复活该 Run。

原父 Run：`run_18e315c4454c4956a75c4b7c97c403b5`；同一 child：`run_0835ae48c5d246ab9aadcd5895de8788`。续验原始页面沿用的分类常量误称 NEW_WORKER，保留原件并在 `classification-correction.json` 更正；`execution.json` 准确记录零Worker，未借首轮 Worker 为续验冒领新执行。

## 历史、合同及控制语义

续验作者实际比较首轮 HTTP 父 Run 的11个字段（ID/AppRun/Release/status/version/result/result_version/effects/events/steps/markdown）与续验 fresh GET，全部相同。续验前后完整数据库比较仅追加2条 `natural_owner_records` 与2条 seal；runs、AppRun、typed及原人工记录/封印原行均保留，typed集合不变。child作为再次修正父节点返回409 `Corrections-of-corrections`，全表无额外写入。这不能补回首轮未落盘的内存 before snapshot，也不是全库跨首轮的逐行不变证明。

原件归档 `natural-spec-correction-20261013.tar.gz` 的正式最终JUnit已包含撤权、排队后撤销、迟到模型回包与取消，故不重跑该矩阵。旧输入/方法与当前已有差异；它们仅为**历史控制语义证据与本次静审依据**，不提升成当前所有后端/新入口资格。原XML节点与差异桥见本次有限独审。

静审还发现独立剩余缺口：受理后、打开新 Run 前若来源撤权，新入口的完整实例读取失败并清选择，无法达到已有 `control-status` 的 owner 停止分支；当前没有另一个同 child 的可见停止入口。没有恢复旧私有 instance 来绕权限，也未在本片混入新的控制 UI；该有界接线需求单独保留，不能声称“撤权后页面取消闭环”已通过。

## 验证边界与原件

[原件索引](../evidence/correction-run-http-worker-20261018/README.md)。两次执行均真实 TestClient HTTP、实际完整服务页/JSDOM，无 renderer stub；首轮实际普通 Worker，模型与人工判断均合成。PG、Windows、原生浏览器、远端CI、真实模型/场景/语义/真人验收均未执行。

测试修复保留原成功断言，仅在刷新后等待精确同Run/PENDING就绪。续验后又加严就绪条件（详情SUCCEEDED、合同同Run/v2、prepare可用）并按恢复分支修正分类；这两项收尾只作语法/静态检查，没有再重跑修正整链。

首轮保全 DB 快照SHA256 `ef4e53a96807567da12b7a00c8eecab68a21f8bebd61d1d5fc40191af52e5704`；原库续验后 `fe1d87474e14b93a34a67ab592d3644bab74416f5d20da0d6558f5ee46bc5d7b`。DB快照仅在当前实例保留，提交仅复制有封存清单的非DB原件，不隐含旧满盘实例恢复。

未探测/推送此前认证拒绝的远端，未改main、部署、凭据或持久安全配置。真实source producer/生产controller注册及官方账户额度、强制零新增费用接入依据仍缺，继续禁止真实调用。
