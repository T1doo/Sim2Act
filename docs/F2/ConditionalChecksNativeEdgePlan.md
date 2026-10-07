# 下一次受保护原生 Edge 最小验收方案（本轮不执行/不接CI）

当前 Linux 安装 Chromium 以chromiumSandbox=true尝试启动，因SUID sandbox helper配置错误BLOCKED；不chmod/helper修复、不使用no-sandbox、不替换身份或安全策略。探测只是启动，不算renderer保护完整验收或像素通过。实际HTTP/JSDOM不是原生Edge。本方案未修改WindowsServerCI工作流、150秒helper/15分钟job或原9文件槽。

## 运行前约束

另获原生验收授权后，在既有Windows隔离fixture及原protected Edge harness中增加最小phase。复用原PS launcher、签名/进程renderer保护audit、同origin路由限制与150秒总时限；module不得另launch、加安全例外或启用LIVE。资料为repo固定公开虚构a-source/policy.txt，事先显式创建测试资源与双主体授权；提供project/other/resource/unsupported现有fixtureID及合成token。使用已有应用使用实例/worker，无真实身份/模型/外发。控制资料变更/撤权用fixture本地动作，不为产品API添加test-only路径。

## 最小同一真实页面序列

1. 登录并选应用工作区。见d464整合的样本工具检查/当前运行技术状态/语义NOT_RUN/用户PENDING；未选运行不自动接受历史。未点资料打开前只可取授权metadata，无资料content GET。
2. 显式打开A-S已授权资料，显示resourceID、完整SHA256内容版本、合同v1/fingerprint及R1–R3原文行。打开非注册文本应VERSION_CONFLICT且清空来源/结果。
3. 人工填写假设：trip true/680/receipt true/approved false/days2，手填TRUE/TRUE/FALSE、BLOCK、obtain_prior_approval、10/UNKNOWN/noRestart及非金标准说明。见结构核对PASS、R2不满足原因、R1仅期限窗口未证实际提交。至少等待一次真实2.5秒poll，输入和报告保持。
4. 改金额500但不改人工报告：编辑立即清证据，新核对FAIL/R2不适用。未知事实+UNKNOWN各规则/决策+clarify_facts报告得结构PASS但业务UNKNOWN，不自动填正确报告或用户确认。
5. fixture连贯改内容+hash，显式重新核对409或背景metadata先失效；不能出现旧PASS。restore后正常核对再撤当前user/runtime任一grant，应403 GRANT_REVOKED或背景先清；引用内容/旧证据必须消失。hash没随内容更新亦VERIFICATION_FAILED，不漏旧原文。
6. 拦截并保持实际200检查响应，期间编辑事实、项目A→B→A、同身份重连；释放后不得复活旧证据。技术请求断开仅显示核对未完成，不表示条件不满足；恢复必须显式打开/核对。
7. 原应用提交错误列由正常worker得到FAILED；技术执行FAILED/无结果PASS，历史成功不借作本次；条件报告与CSV技术验收独立。冷重载重新登录不发POST、不恢复报告PASS，显式选历史仍只读/PENDING；重新输入规则报告才能取得新证据。
8. 最后完整Grant/Principal指纹不变（fixture故意撤销单独记账）；AppRun仅预期提交产生，条件检查全部表零写，真实模型0。owned服务/PG清理，原renderer保护audit仍必须PASS。检查页面错误与1280/390宽按钮、字段、引用横向溢出；截图须另独立原图审，不以DOM代替。

## 交付与判定

共用HTTP/DOM oracle为tests/conditional_checks_ui.cjs与tests/application_use.cjs（当前21+29逐项检查），故障注入仅transport/fixture。移植到现有protected native caller时保持原业务断言；功能原生结果、保护audit、截图producer与独立像素审查分别记录，未运行项NOT_RUN。预计最小phase必须先实测150秒总预算，不通过不加长时限。不得把本轮HTTP/DOM绿灯或20bb历史Edge CI签到新源码。
