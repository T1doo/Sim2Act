# 条件/例外检查实际用户流程本地验收

基线6579beaeb66178261a6a52e2466dec037d068eb9，实施前plan d9fcdd8，产品ea802c85762abbff9fbee2e6e632ebe5f7e1f547。独立dev/bounded-semantic-suite-local；仅本地，未push/未新增CI。交付前远端dev/f1-foundation仍exact5a49ea6ad119cf2afae350d7cdb6aabfe877e68d。旧工作树/V5/AT02/历史Run不改。

## 新用户流程

已整合d464b832的应用页只读验收投影及原DOM断言：固定样本检查、当前/历史技术执行、绑定结果版本核对、语义NOT_RUN/用户PENDING分开显示。应用FAILED不能借历史成功；新运行未确认或回读失败清旧验收；冷会话只读历史，不自动确认。

同一应用工作区增加显式授权规则资料选择。只列当前项目已授权TXT/MD metadata，不自动读内容；打开经当前user/runtime授权交集、可信实际hash重算、固定公开虚构A-S v1合同后，展示resourceID/hash内容版本/合同版本及R1–R3原文行。填写假设事实和人工报告，报告不自动生成、不读gold；引用由显式打开的授权原文提供。核对逐条显示条件满足/不满足/未知/不适用、原因及原文定位，并显示结构报告PASS/FAIL。R1满足仅期限窗口，明确未核查实际已提交；逾期政策UNKNOWN。

条件报告与CSV技术验收独立，未挂到Run签收/候选source_proof/owner自动确认；结构PASS可同时业务BLOCK/UNKNOWN。有限人工规则不是开放语言理解；自由说明NOT_CHECKED/真实事实未核查、semanticUNKNOWN/ownerPENDING/正式发布关闭。无任意代码、无真实模型/新真实身份凭据/准备器激活，无新增表或API建表，检查只读。

编辑事实清证据；授权metadata未变化的正常2.5秒poll保留输入/报告；版本变化、source缺席/格式变化、授权列表失败清来源和证据。显式重新核对再次授权和可信读取（POST仅只读检查）；冷会话不存/复活旧PASS。资料hash仍未变化但实际bytes篡改在下一次显式可信读取拒绝；旧报告只是上次核对，不承诺后台读取所有内容持续完整性验收。

## 验证证据

源码SHA见[source-sha256.json](source-sha256.json)。独立报告对应全部产品/测试source一致，计划为实施前版本。

- 主执行器最终HTTP/DOM专项3PASS/1warning/16.33秒；条件流程21断言（保真实2500ms poll）、应用使用29断言；含全表无写/原Grant与Principal完整指纹不变、正常worker3AppRun/2结果、FAILED历史分离。
- 独立41手写HTTP检查PASS，全表无写、外部socket硬禁；26实际loopback HTTP/JSDOM断言PASS/6.13秒，另原应用使用真实HTTP回归PASS（联合2PASS/10.14秒）。editedfacts迟响应、项目A→B→A、同身份重连ABA、授权列表失败、实际双授权撤销/过期、source篡改、未知、冷会话均覆盖。[独立报告](independent/final-review.json) SHA80872ec12a651ac37faa062e1dfaa9e6c56b74087f4ac88eaae6a10c281b0201。
- Ruff/mypy36/Node检查/diff PASS，最终source冻结SHA校验PASS。
- 完整适用SQLite/PG最终结果在下方追加；早期主动中止日志不能作为完整验收。

## 失败及未测边界

首轮DOM wait误等空runs，而真实空列表是run-history-status消息；其后test-only source变更POST空body被原strict_json中间件400拒绝，原貌保留后改fixture发送{}（不改安全策略）。独立真实复现初实现每次refresh清表导致2.5秒自动poll丢输入/证据，现改授权metadata reconciliation；原defect source/脚本/日志和修后正常poll验证保留。独立PASS的poll-defect表示成功复现缺口，不是旧产品通过。

两次尚未冻结的SQLite/PG全量为修R1措辞和poll缺口主动INT，保留中止/pytest teardown异常，不伪称全绿。第二PG中止有1个本轮test schema残留、0role；明确核名后只DROP该schema并保存日志再开最终回归，不能称中止时无残留。

已安装Linux Chromium在chromiumSandbox=true启动探测因SUID sandbox helper配置错误BLOCKED；不修改helper/系统策略或使用no-sandbox。只是启动探测，未执行完整renderer保护audit。原生Edge/像素/Win11 NOT_RUN；不借20bb历史CI签本源码。下一次授权原生最小步骤见[Edge方案](../../F2/ConditionalChecksNativeEdgePlan.md)。

[新增价值与下一核心缺口](../../F2/ConditionalChecksUserValue.md)：用现有页面完成来源规则报告核对与失效处理，下一步仍需把目标/可核验Run/候选契约绑定及受限工具/语言DAG规划，新真实执行必须另完整批准。完整P-A/P-B/语义/owner/F1/AT02未提升。

## 最终完整回归（冻结ea802c8源码）

SQLite966项：927PASS/39SKIP/0FAIL/0ERROR，393.55秒，3warnings。每项skip与warning保留于完整日志；PG专用角色/事务锁/独立进程和3项Windows/受保护Chromium限制不能算PASS。

PostgreSQL配置966项：962PASS/4SKIP/0FAIL/0ERROR，917.71秒，2warnings；其中明确SQLite-only子进程UI2项、Windows原生PowerShell1项、受保护Chromium恢复UI1项跳过。此配置仍含既有显式SQLite-only fixture，不能说每项都用PG物理连接。新增source GET/条件HTTP/DOM、最小应用角色SELECT-only均实际PASS；独立PG未跑不借主执行器提升。

主执行器最终ownedPG残test_% schema0/role0，然后只移除sim2act-conditional-ui-pg，docker列表验证无该容器。HTTP fixture server线程均正常finally停止，受保护启动探测关闭/清理临时profile；没有额外持久后台服务。源码冻结校验与独立review产品/测试SHA再次匹配。终态仅docs追加，不变ea802c8产品；未push/未新CI/真实模型0/无新真实身份凭据/准备器未激活。
