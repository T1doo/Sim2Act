# Report 晚回执修复候选证据

冻结源码和测试：`51487fd4787eae66f09f8ff2b01492d8f9c13503`。
独立分支 `dev/report-presentation-late-receipt-fix-20261008`，祖先为原候选
`64576576bdbd0b811ecb875cd46ccbf302b5f686`；原候选保留，未进入 main/dev。

平台复审的 P2 `/checks` ABA 由实际 HTTP 负对照复现：服务器先接受检查，
扣住响应，关闭并重开同一应用，等待新历史完成，再释放旧响应。旧静态源码
`ffda5b00a9a1469b454728adb5a0005016cd0a55` 在 SQLite/PG 均失败于当前
页面没有新的 report-presentations GET；当时文本仅 ALLOW，两个按钮 disabled。
见两个 `*-old-final/failure.json`，不是模拟后端回执或只检查源码文字。

最小修复只改变现有 `report-manifest.js`：在原 DOM 被替换后，当前同身份/
项目/应用/fingerprint 的页面重新读取原授权 history 和展示账本。旧闭包
不绘制结果、不自动继续 POST；跨应用/身份不读取旧应用历史。API 读取失败
清空受保护内容，并用自身清空标记防止吞掉当前失败提示或污染后来的导航。
HTTP 200 内容校验失败的清空分支仍没有该新提示标记，不声称覆盖其反馈。
后端 Python、canonical 合同、权限及历史保持原实现。

## 最终验证

最终完整范围为新增 14 个实际 HTTP/产品 JS/jsdom 案例，加原两个 UI 回归，
每个后端共 16 个 pytest。终态和时长见 `test-summary.json`；每例七个实际
加载脚本 SHA256 核对冻结源码，见 `loaded-source-verification.json`。
没有使用旧 1591/2051 或原候选114结果证明本轮改动。

新增 matrix 是 definition/check × 同应用 ABA、另一应用、真实 connect
身份切换、撤权、回读失败与显式重试、已接受回执丢失、同上下文刷新替换 DOM。
检查无自动续写、无旧内容混入、原 decision 与新 explanation 共存、安全
textContent、非 delivery_graph 表保持（撤权例仅排除自身 grants 修改）。
原两个驱动/断言及 Windows 900 / Edge 240 / Node 150 不变；Mypy 53 源文件、
Ruff、新旧 JS 语法及 diff 检查通过。本轮不运行原生 Windows/Edge、后台轮询
或全量。JS 按既有 6 秒等待运行，Python subprocess 90 秒保持。

## 失败与独立审查

`exploratory/` 保留失败与中断日志：最初身份切换夹具错误地等待刻意 held 的
旧请求，现只等待身份切换自己的请求完成；撤权端点最初空 body 被原安全
中间件 strict_json 拒绝为400，补认证头不足以解决，最后补合法 `{}`。
这两项只改新增夹具，没有改原产品规则、原断言或等待上限。

多个自有探索矩阵并发时出现新的6秒等待超时，包括 refresh 检查、初始
definition 发送和初始定义准备。已停止被取代的测试，最终 SQLite 与 PG
分别完成；**这些超时原因仍 OPEN**，后续通过不能解释或关闭它们。
主动 SIGINT 的进程和所属路径见 `owned-exploratory-interrupts.json`。
旧 PG resources-history Future10秒和旧 DOM lost-check6秒也继续 OPEN。

独立只读审查精确51487fd为 **LIMITED PASS**：当前选择重新读取授权历史、
无旧结果搬运/续写/外来访问、自身 API 失败反馈成立；新增 test-only JSON
修改不阻断候选普通推送供平台复审。审查者没有执行测试或操作临时资源，
不建议据此合并 dev。完整矩阵的执行证据由本任务另行保存。

## 边界与复现

整体 NOT_ACCEPTED、实际材料 PENDING、PROJECT PENDING/BLOCKED_PARTIAL、
语义 UNKNOWN、人工 PENDING、正式发布关闭、LIVE=0。只是合成工程展示病例，
不是真实任务 gold、通用 P-B、canonical 实际 VIEW 补丁或人工签收。
未触发模型或业务写权限，未合并 dev/main、部署、强推或新 CI。

复现步骤见 [修复说明](../../ReportPresentationLateReceiptFix.md)。
所有临时测试资源自有隔离，清理核查见 `cleanup-audit.json`。
原分支、main/dev 远端引用和推送前祖先核验另见 `git-audit.json`。
