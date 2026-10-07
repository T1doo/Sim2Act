# 普通任务提交回执恢复：本地交付

普通任务提交后若连接断开或代理返回502，页面冻结原目标、材料与提交键，明确显示“尚未确认”，用户点击恢复仍使用同一个请求。服务端既有持久幂等与当前权限负责核验；之前已经接受的任务不会重复创建。收到任务ID后读取失败，只提供GET恢复。已接受不代表执行成功或目标验收。

本地分支dev/task-submit-recovery-local，基线d3d4fa58fda9e339d6842b7d13aee5f9a5022d37，无activation68443祖先。实现仅现有app.js/index.html；未新增API、表、DDL、权限、后台自动重试或模型调用。页面内按身份/项目隔离，迟到回执不能抢走当前项目或用户重选历史；输入/key不写localStorage/sessionStorage。刷新页面会丢失内存快照，已提示先查任务历史，本切片不声称跨页持久恢复。

## 实际验证

[DOM结果](dom-results.json)：真实loopback API/显式test-only SQLite，实际服务端接受后丢回执或502，24项PASS；6个刻意新意图恰好6个持久Run，恢复返回原ID。双击、冻结输入、未决后403不能解锁另建、跨项目迟到成功/失败、历史重选、初次422可修正、已接受读取失败不再POST、浏览器存储为空及可访问状态反馈均覆盖。正常Mock worker执行恢复的Run，2个MOCK Attempt、1个VERIFIED resource.read、实际PARTIAL结果；不伪造SUCCEEDED或语义验收。Grant/principal数量保持不变。

最终联合专项1PASS/1识别的沙箱阻塞SKIP/1既有warning（2.79秒）；先前v6 DOM独跑1PASS/1浏览器DESELECT（2.19秒）；foundation/registered-generation/protocol/agent相关回归47PASS/1浏览器DESELECT/1warning（36.92秒）。Ruff新Python测试、两个Node语法、git diff检查PASS。本切片PG/Windows/Win11未测，不能借旧CI签收新代码。

[实际受保护Chromium启动](browser-startup.json)：chromiumSandbox=true，沿用既有helper移除弱SDK参数，无no-sandbox/disable-setuid-sandbox/禁TLS或系统权限更改。实际浏览器因SUID helper未由root拥有而SIGABRT；最新联合跑1PASS/1SKIP，之前浏览器独跑1SKIP/1DOM DESELECT。只有上述明确SUID错误允许SKIP，其他启动异常保持FAIL。未加载页面、无PNG、像素审查NOT_RUN。保留BLOCKED，不将DOM称原生浏览器成功。

[测试历史](test-history.json)保留初次driver模板正则转义失败、异步读取断言过早及完成消息未闭合的失败；已分别修复driver、等待实际回读和产品完成消息。最终v6覆盖24项、6Run；v5旧23项/5Run不替代最终。日志用JSON字符串原样保存，不归一化oracle材料。

本切片真实模型请求0，不push、不触发CI、不带未发布activation。单独获批真实实验与空白投影修复在其他工作副本保存，互不改写本产品测试口径。完整P-B/F1/AT02/正式发布尚未签收。

下一项有界产品工作：任务历史显示目标摘要、接受时间与MOCK/LIVE模式，帮助刷新后定位同一持久任务；沿用现有授权Run读取接口，继续保持PARTIAL/UNKNOWN与验收状态分离。
