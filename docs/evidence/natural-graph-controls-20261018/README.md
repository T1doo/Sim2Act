# 自然应用交付图与节点编辑保护

真实价值：此前自然应用打开内部面板后提前返回，用户看不到交付图，也无法按局部修改提示派生图；节点编辑保护的前端筛选也漏掉后端已支持的自然家族。本轮仅修改 `app.js` 和 `manual-locks.js` 接通既有控制器，不增加API/executor/Grant，不改main/部署/费用或凭据权限。

普通分支 `dev/natural-graph-controls-20261018`，基线 `4a5fa568d2aefcbe59ef2f14c5a58414073bbe0b`，实际通过源码 **`d9e19b2829221909b49fd075b721d4e831d711a4`**。root唯一仓库写入者，独审与驱动草稿均只用全新外部目录；开工clean、远端一致、约23GB空闲。

最终1唯一pytest/1PASS，JUnit87.861s、外层91.792s。44检查/26操作不是额外用例。完整实际index、CSS与25脚本共27资产逐字核当前源；54实际API，7POST。普通三次Mock生成P-A、原Release和空实例是fixture；图不存在由UI原GET409验证，然后从目录显式derive201，明确锁定、重派生、真实LOCK_CONFLICT400，明确解锁、重派生、预览201，普通workspace往返后图GET仍有效。双击派生/锁定各只1POST；未确认不写锁，不自动CHECK/创建Release或业务Run。

原Release/空实例和另外50张表按完整before/after行断言保持；5张图/锁元数据表按精确11journal（含请求/双seal/FP）、3anchor、唯一state、来源版本及最终rev2解锁核对。全55表断言由本次pytest实际执行；只保存表指纹与结果，未复制巨大全表快照，独审不冒称另行重算50表原行。

共2次attempt：首轮d1b源1FAIL（JUnit47.683s/outer50.715s），实际400/code/rejection正确但测试误要求UI字面错误码；原显示文本NOT_RETAINED、渲染原因按代码推断。只改一处测试predicate匹配完整服务端具体原因，生产不变，第二轮完整PASS。每轮693输入（含全部133生产文件）前后0漂移；proof额外直接hash的131文件仅为py/js/html/css，其余2生产格式在全输入映射内。共6Mock，均为fixture生成；页面模型/业务Worker/真实模型0。首轮原件完整保全，未冒称全程绿。

[最终执行](author/execution.json) · [JUnit](author/junit.xml) · [pytest原输出](author/pytest.stdout) · [页面原请求响应](passed/results.json) · [真实断言证明](passed/proof.json) · [首轮FAIL](failed/results.json) · [首轮JUnit](failed/junit.xml) · [有限独审](independent/final-independent-review.md) · [交付原字节清单](selected-artifacts.json)。

本目录仅保留本轮必要原始日志、JSON、输入哈希和审查报告；不追加旧归档，不创建大bundle或数据库副本。各fixture.db和重复HTTP流原件继续保全在 `/workspace/natural-graph-controls-20261018/`，首轮14原件清单同时保留。完整当前代码在上述冻结Git提交。

实际页面仅P-A；P-B同namespace后端支持和共同接线属静态依据，未冒称本轮PB现场通过。first-use临时围栏释放经源码审查，本例实际验证的是目录打开和普通workspace往返；未重跑Goal创建向导或之前完整业务链。JSDOM/SQLite/合成账号/Mock，不是原生浏览器、Windows、PG、真实模型/语义或远端CI资格。未部署；旧满盘独审缺件、exit139未知和旧取消门均不补签。
