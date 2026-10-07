# 持久任务历史定位与身份隔离

承接442e90b0回执恢复，当前独立UI分支dev/task-history-ui-local从d3d4fa5派生，无activation68443祖先。旧WIP657ea4f、442e90b0和本轮历史提交均仅本地。API只扩展现有授权Run列表的goal_summary/mode，不新增端点、表、DDL、Grant或模型请求。

用户刷新后重连，按目标摘要、接受时间、冻结提交模式找到原Run，点击只读打开既有状态。目标摘要最多160字符加省略号、空白收敛，textContent显示；列表不外发合同、请求键、资源正文、成果或凭据。created_at是持久接受时间，本地时间展示；mode为普通任务冻结提交模式，不证明实际模型调用/技术成功/目标验收。缺失或未知mode，以及协议任务普通合同中的MOCK占位，一律UNKNOWN。现有own_project与principal双过滤保持。

刷新以身份/项目/请求代次隔离，项目导航即时清旧历史；当前列表读取失败清旧列表，显式刷新仅GET。连接身份时先清任务、成果、材料/应用/目标/协议视图及在途选择；失败连接仍保持清空，A→B→A不恢复旧回读。connect独立代次使旧连接成功/拒绝均不能覆盖当前身份。

## 验证与失败保留

实际API4项、实际loopback HTTP/JSDOM组合39项覆盖442e90b0及新历史流程：7个刻意新意图恰好7个持久Run（原恢复6，第7用于同项目较新快照），2MOCK Attempt、1VERIFIED read、原Run PARTIAL。恢复/新页面定位/身份更换/读失败全部不新增POST；Grant/principal数量保持。专项5PASS/1识别的SUID沙箱阻塞SKIP/1warning（4.05秒）；相关foundation/registered generation/protocol/agent与新专项52PASS/2浏览器DESELECT/1warning（41.54秒）。Ruff、mypy34源文件、Node语法、diff检查PASS。API测试一项只保存LIVE mode元数据，不执行模型。

独立审查发现两个真实身份边界缺口：失败连接留下旧成果、旧连接迟到拒绝覆盖新反馈，已复现并修后闭合。稳定源码独立5PASS/1浏览器DESELECT（3.23秒）。[修前/修后反例](independent-review/README.md)及原脚本/JSON均保留；中间两次helper注入语法失败不藏为成功。

[测试历史](test-history.json)保留初次Limits夹具缺少必填字段（终端首轮1FAIL3PASS，已改显式固定限额）、v1 driver错误等待held Promise导致无results、v4/v5注入正则转义错误。v2/v3成功仍为中间较少覆盖；最终v6的39项与7Run才是当前证据。上述夹具错误没有真实请求或状态伪造。

[受保护Chromium实际启动](browser-startup.json)仍因现有SUID helper所有者而BLOCKED；无no-sandbox/权限修补/安全降级，无页面加载、PNG或像素验收。PG/Windows/Win11本切片NOT_RUN，不借旧CI给新代码背书。不push、不CI、不重试失败真实实验、不复用其余13请求；完整P-B/F1/AT02/正式发布不提升。

[下一轮既有Windows Edge验收方案](../../F2/TaskHistoryWindowsAcceptance.md)明列工程与像素门，当前尚未实施/运行。下一产品切片：普通任务成果画布用现有Attempt/Operation回执呈现简明步骤和等待原因，使PARTIAL/FAILED/UNKNOWN及目标未验收可直接理解；只读展示，不自动恢复执行。
