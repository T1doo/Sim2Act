# R8最终冻结来源：独立受控UI LIMITED_PASS

2026-10-12，`/root/text_logic_review`。同原保存环境，HEAD `df5f422174c4eeea96e5dd16c141dc0a4b36b3e6`、分支`dev/text-compatible-continuation-20261012`，root唯一仓库作者，独审仅写本/tmp。

**本R8来源实际12项受控离线UI全PASS，0 FAIL/0 SKIP，Node exit0，stderr0bytes。R8_LIMITED_CONTROLLED_UI_PASS。** 12只为本组分母，不与此前两个12或其它作者/后端/实际页面结果叠加。

冻结`/tmp/text-continuation-r8-final-freeze.json` SHA256 `66d491e1bea7e7a6a50919e83b685780ca053ba1b3ef5d0482e8cbd4881255de`。401个source/tests前后逐文件SHA相同，0差异，规范map fp：

`3bb07485d301ea8b01bd4e2b408e71b4789650934ebf8b1734dafc66ff08a32f`

`pyproject.toml`单列前后SHA同为`49f68cb7901e719cd014141c69e5fa9ea562f51e9b9c40acd122ace6f2085d81`，HEAD/branch亦相同。freeze声明的target implementation为`c0cdc4e98de6a043bb43f1b1d5b27d4b57f525164922fb65cf70173f3b1d2a93`；这里不另证明它的后端执行/迁移行为。

实际index.html+app.css+HTML列出的18JS，共20原资产，12场景都加载且以真实SHA核401前后来源，原bytes在`loaded-assets/`。全部20资产也与前次14be来源受控报告相同。`text-logic.js` SHA：

`ae0e514fd0ab8b4cd8a4e8db45b0976fcca03221b25f6f3fa0a768d0297c4636`

| 实际资格 | 数量 | 结果 |
| --- | --- | --- |
| 成功预检POST迟到，期间identity/connection/project/workspace/edit改变 | 5 | PASS；共用tcSubmit门不再发旧iid/key后继GET，身份改B也不借新全局token读取旧请求；原intent对象保留、不画旧status/proof |
| 已接受POST后GET成功/409迟到，编辑A→B→A | 2 | PASS；不画/不装preflight，不清原pending，没有自动POST重试 |
| 冷原key GET返回另一key/旧所选源ReleaseFP | 2 | PASS；PREPARED被VERSION_CONFLICT拒绝，无preflight/receipt安装；旧ReleaseFP例重算真实有效approval SHA，仍须匹配当前所选metadata |
| 当前有效POST/GET409 | 2 | PASS；当前错误可见，原key/intent保留，仅一次POST |
| 当前正确真实SHA PREPARED控制 | 1 | PASS；只验证后装预检并清原pending，明确commit确认仍必需 |

每项完整proof含请求Authorization/body、全部检查及20资产SHA。实际全部脚本运行，未替换产品函数、registeredHash、setInterval或Date；脚本仅附诊断sourceURL注释，场景结束后正常window.close。fetch为本地Promise，metadata/identity为合成数据；不监听socket、不调用网络/TestClient、SQLite或Worker。编辑ABA为合成InputEvent，native Undo并未验。POST通过预检行使共用后继门，冷回执通过PREPARED行使key/源Release绑定；此组未执行COMMITTED/REVOKE/CANCEL后端效果。

R8修复针对实际损坏FAILED job可过预检、冷读取409的漏洞，新增真实旧Git Worker两fixture等8文件。401来源覆盖这些文件指纹，但本controlled12不证明原FAILED seal/frozenContract/release/Goal/CAS修复的业务结果；必须由另一后端/实际页面/R8组独立证明。root249、其它review58/4/10/6/R8均另外报，不充当本12也不借其PASS。技术semantic UNKNOWN，真实人类、真实/付费模型、native/CI/正式发布NOT_RUN。

所有产物在`/tmp/text-continuation-ui-independent-20261012/final-r8/`：新driver/runner、12原proof、complete Node stdout/stderr与exit、401+pyproject前后hash、20原资产bytes、summary及manifest。此前原候选12、freezeMismatch、transport原错误与14be报告原封保留；本新任务前后核其65个raw/报告/manifest SHA均相同，两个preservation JSON记录完整路径和SHA。前次14be有限报告不倒签为R8后端结果，旧红/平台错误不覆写。

本轮没有工具/平台拒绝，未写产品/src/tests/仓库/push、未配置凭据/权限/网络，未执行旧取消候选安装精确竞态或任何替代probe，该目标仍永久NOT_VERIFIED。所有本组进程已结束并通知父作者，不再扩测。没有阻断这12项前端受控资格的剩余失败。
