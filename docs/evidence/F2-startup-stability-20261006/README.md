# E20：有界启动稳定性诊断（2026-10-06）

交付源码仍为 `aaf07f49b3d32eeb360d8cd60a52a4fad22959fd`；本轮仅文档/观察诊断证据，无生产源、原 AT05、测试断言或等待时长变化，无新 feature。正确工作副本 `/workspace/Sim2Act-pb`，既有 `dev/f1-foundation`，原 `/workspace/Sim2Act` work 树不动。正式发布/部署 false，模型请求 0，无外发/导出/安全策略更改。

## 首次失败与分类

[E19 首次失败 JUnit](../F2-internal-entry-20261006/linux-pg-first-failure.xml)及[原始可查事实](first-failure-review.json)保留：AT05 首次 start 在 1.269 秒内报 `API/worker exited; inspect local logs`，当时两日志 0 bytes，cgroup oom/oom_kill 为 0。原现场 PID、Popen 退出码、boot epoch 未记录；pytest retention 已移除原临时日志。不能从空日志断言进程真实崩溃，也不能从后续成功断言故障已修。

未改的 `scripts/manage.py` 在 psutil 身份检查返回 None 时使用该错误文本，健康等待超时使用另一个文本。故可定位到启动进程判定路径，不能追溯具体是退出、身份变化还是其他竞态。Linux psutil 7.2.2 创建时间依赖内核 start ticks 与 `/proc/stat` btime；clock basis 变化只是可能性，本轮未观察到，不作根因。生产缺陷、测试启动身份/等待竞态、环境信号/资源原因均 **未确认**；已报告的健康 deadline timeout 与此次错误不符，oom=0 只排除已记录 OOM 事件。

## 限定重复与诊断工具失败

|执行|真实结果|边界|
|---|---|---|
|[原 AT05 原样重复](original-repeat.xml)|4 PASS，39.99s，1 旧 warning|原全部断言，每次独立隔离 PG schema、最低 CRUD role、port/tmp|
|[修正后观察诊断](observed-repeat.xml)|4 PASS，35.59s，1 旧 warning|同原断言；仅在原 launcher 周围观察，无 injected failure/new wait/额外 child flags|
|[初版观察包装器失败](observed-harness-failure.xml)|4 FAIL，14.55s，1 旧 warning|包装器 event 参数 kind 与 snapshot.kind 冲突产生 TypeError；不能归入产品或原 AT05 失败|

初版失败观察保存在 `observed-harness-0..3.json`，有效四次在 `observed-0..3.json`。仅修观察包装器参数名，原 finally 与错误传播不吞错；故障留下的 owned 进程由原 launcher 精确身份验证后 stop。没有删除失败、放宽断言或无限寻找绿色。原先冻结的有效重复上限 4+4 已完成，另四次是保留的无效诊断尝试；本轮停止重复。

[诊断汇总](diagnostic-summary.json)记录 12 个成功 start/24 个 child launch、0 个启动阶段 process 拒绝；24 次停止阶段拒绝随后 stop 成功。其中少量补采样正好处在退出转换窗口，状态 running、cmd 不匹配、create delta 0，随后均为 zombie；这是停止阶段事实，不用于解释原启动失败。有效观察 btime 均 `1791216270`。预期重复启动拒绝为 SystemExit，原断言确认原进程不被替换。退出码仅对当前 start invocation 的 Popen 可获得；独立 stop invocation 明确 `not_this_invocation`，无伪造退出码。

可复查脚本：[原样 driver](original-repeat-driver.py)、[观察 driver](observed-repeat-driver.py)、[观察包装器](at05-probe.py)。用显式合成 `SIM2ACT_TEST_DATABASE_URL` 和该仓库 venv 从仓库根运行 pytest driver；仅测试隔离 DB，不对业务库执行。不能用包装器诊断成功代替原 aggregate 或 root-cause repair。

## 独立 E19 关键边界

只读审查在基线 `e94ddc96db0a5dd1bd4f32c33c860ebde0240520`：既有 API 测试 **18 PASS、1 PG SKIP、1 warning，4.53s**，另[合成 HTTP 负例 probe](independent-negative-probe.py)验证跨 owner/instance 历史与控制 403、foreign/malformed binding 直接读取/control 409 无外来结果；撤权后内容接口 403、owner control-status 不含 input/result/error/events/snapshot，取消仍允许，foreign 仍 403。没有新授权或生产数据。

保留边界：binding 引用错误 AppRun 时，实例聚合历史 join 会遗漏损坏 job 并返回 200 的有效自有历史；直接 job 读取/控制拒绝 409。不泄漏 foreign 结果，但 **不证明损坏账本历史完整**。本轮不拓展 fixture 或新修复此非越权边界。独立未跑 PG/CI/真实浏览器。

## 受保护浏览器：环境方最小接入

[E19 实际错误](../F2-internal-entry-20261006/browser-block.json)、[E11 正式审批错误](../F2-preview-extraction-20261005/browser-block.json)已存。官方可写 SOCKET_DIR 解决 socket 路径后，受保护 Chromium 仍在 DevToolsActivePort 前 abort，SUID helper 必须 root-owned/mode 4755；本轮只读 stat `/usr/lib/chromium/chrome-sandbox` 实际 `65534:65534 4755`，问题包含 owner。E11 正式 require_escalated 同 helper 仍失败，namespace sandbox 路径报 `No usable sandbox`。

需要环境方正常提供 **一个**可用入口：在实际执行 namespace 中正常安装、root-owned helper 且支持其沙箱的 Chromium，或允许正常 namespace sandbox 的受支持受保护浏览器，或已有受保护本地 CDP runner/认证浏览器 connector（本项目合成回环访问即可）。由环境方配置，不由本任务 chown/chmod/改内核策略。若环境长驻，另建议正常 init/reaper 回收退出的 PID 1 child；诊断的 24 个 child 已全部 zombie/ppid 1，无执行中 API/worker，不杀系统进程，不把它视为首次失败证明。

本轮浏览器完成 0/BLOCKED，桌面/手机视觉 NOT_RUN；不 --no-sandbox、不绕拒、不追加 DOM 冒充视觉。入口具备后仅做 E19 真实浏览器验收，无须继续增加业务 fixture。

## 保存状态与精确 CI

生产/tests/scripts/config 与 aaf07f4 差异为空；[精确 Server CI37419363378](https://github.com/T1doo/Sim2Act/actions/runs/37419363378)重新只读核验 completed/success、headSha 精确一致，PG372 PASS/0 FAIL/0 SKIP。文档 push 不匹配既有 workflow paths，不制造重复 source CI；旧 CI 不证明本轮未知失败原因解决。本轮原 AT05 8 次有效通过只是有界复验结果。

专用 `sim2act-e20-pg` stop/remove，正常原 stop 清理所有有效状态，观测 child 已退出但 PID1 zombie 如汇总保留。原 work/V5/历史 AT02/AT05 不改。F1/Win11/真实浏览器、完整 P-A/P-B/F2/AT10/19/20/正式业务 writer 与外部效果恢复仍不签收。最小后续：保持启动原因 UNKNOWN；若再次出现真实原拒绝，保留 child rc/身份/时间再按可复现原因修；环境方提供受保护浏览器后验收现有内部入口。本轮不新增 feature。
