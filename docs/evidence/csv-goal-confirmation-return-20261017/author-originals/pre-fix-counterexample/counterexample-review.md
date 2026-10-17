# 6ed CSV Goal 修订三阶段离返缺口独审

**缺陷已独立复现，应阻止该 UI 切片准入。** 基线 `6edb626c4203def2a735006e860dcbca807315df`。共享仓库只读；在独立 `/tmp` git source snapshot 中，仅修改测试driver添加三个导航观察点和 Node 模块路径，不改产品源码。沿用原 `test_visible_same_goal_revision_check_release_adopt_and_new_run[deliver]`、真实 FastAPI TestClient/RPC端点、既有 NoModel Worker、完整产品HTML/CSS/JS及JSDOM动作。不是原生浏览器、真实像素、PG或模型验收。

## 准确反例

原视图每阶段都已有非空服务器回执证据。点击“资源”，再点击“应用”，既有 resumeCsvGoalRevision/readApplicationUse 重建同实例控制器：

| 停止点 | 实际接受状态 | 返回后真实 DOM | 仍可操作 |
|---|---|---|---|
| preview已受理、CHECK未发 | previews POST201/原key | proof为空；from/to options均0、value为空 | checkAck未勾选但可勾；勾选即启用CHECK按钮 |
| version approval已受理、Release未commit | version-approvals POST201/同原key | proof为空；from/to仍0选项 | releaseAck可勾；勾选即启用Release commit |
| adoption approval已受理、CAS未发 | adoption-approvals POST201/同原key | proof为空；from/to仍0选项 | adoptAck可勾；勾选即启用CAS按钮 |

每个导航/确认框观察点均证明0新增POST。前两阶段原流程随后实际执行CHECK202与Release commit200，尽管刚返回的页面没有相应可核对证据；第三阶段观察到CAS按钮可启用后，原测试的“CAS adoption proof names original instance and awaits consent”断言失败，故未发送最终CAS。

## 原因与现有覆盖缺口

`renderCsvGoalRevision` 通过原 owner key保留 entry.preview/approval/adoption，但新建 proof/from/to 后只调用controls，没有恢复内容和列选项。controls依据缓存阶段对象与checkbox控制后续按钮，因此业务状态保留而用户核对内容丢失。现有deliver只在CHECK PASS后的离返断言版本按钮visible；未核对proof/冻结列。version/adoption批准和最终commit之间没有离返断言。保留原意图是必要的，但不能使空页面继续确认。

## 必要修复/回归断言

1. 在上述三个准确停止点分别离返，按实际API阶段回执作oracle：新proof非空且JSON深等当前阶段已接受payload（preview/version approval/adoption approval）。不可仅断言按钮visible或entry存在，也不可显示其它旧阶段JSON代替当前批准。
2. 两列select应重新有选中项，其值严格等已冻结preview请求baseline_column/column，提交后不可修改；不要用ctx前两列的默认值代替。最好让测试映射不是默认第一→第二列，以免错误回填漏检。
3. 三个确认框离返后均重新未勾选，后续CHECK/commit/CAS按钮先禁用。只有完整且当前可核对证据已恢复，再明确勾选才可启用；若无法安全恢复则保持禁用并给原键只读恢复入口。
4. 导航本身0POST/0新键；已受理请求的body、key、Goal指纹、Release/实例绑定保持。UNKNOWN/accepted-read-error只能按原key GET恢复，不得再次POST或自动推进下一步。恢复成功同样展示正确阶段proof与冻结映射，并重新要求确认。
5. 其它身份/项目/实例的迟到回执不得重填本页；原有导航代数和pending锁继续保持。不要通过清空entry/另发key回避此缺口。

## 实际结果与原件

独立一次执行为 **1 FAIL，RC1，76.55秒**（JUnit 76.543秒），1条既有Starlette/httpx warning。9条COUNTEREXAMPLE断言和3条导航0POST断言全部成立；最终失败是上述原UI证据可见性断言。它是缺陷复现结果，不得写成1PASS或完整功能验收成功。无需为了“凑绿”重跑。

原件在本目录 pytest.log、junit.xml、snapshot-proof.json、data/test_visible_same_goal_revisio0/{page-result.json,node.stderr,actual-http.json}；产品/改动后driver在snapshot中可检查。全部测试数据合成；最终CAS、PG、真实浏览器、模型均未执行。root修复后仍需固定SHA的独立完整审查，本报告不提前接受新实现。
