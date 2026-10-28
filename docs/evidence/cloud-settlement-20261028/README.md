# 2026-10-28 云端结算协议与真实提取

冻结实现 `1389ae00`，在 `bcc84b1a` 待审开发分支继续修复。完整真实时钟控制器用例失败，尚未形成可用交付。所有记录明确保留这一结论。

## 已完成的实质改动

- 新 P-B 合同明确记录 `sqlite-exclusive-settlement.v1`：普通心跳30秒，单次模型结算预约上限120秒，并受原 Run/节点/合同最早截止约束。旧序列化14字段 caps 仍按原30秒解释；新16字段 caps 与原合同一起签名，未升级旧批准。
- SQLite 在独占事务前真实提交一次 Run/Attempt/fence/version 绑定预约，写入 RESERVED 事件。同一 Attempt 不可再预约；旧lease在预约写前及提交前均必须有效。G0、原五写、G1全段不刷新预约，完整检查不删除。额外 monotonic 截止计入预约提交耗时，防止墙钟回拨延长。
- Worker共享非阻塞锁拒绝预约/body/cleanup任何重入。出事务只对仍有效的同一 RUNNING owner 做缩短 CAS 并写 RELEASED；不会续活取消/终止/过期/换owner。释放故障独立停止worker，绝不把已提交VERIFIED误送到RECEIVED拒绝分支。
- 新caps、原SQLite/test-only/P-B eligibility范围内启用已有有界 owned fact 复用及固定纯段；未知容量仍保留完整legacy。没有把这种优化当作生产PG权限或真实模型资格。
- 新自然请求v2使用固定原Intern端点/model、`thinking_mode=false`、空tools、完整机械字符坐标及明确ID正则。预算预留、实际发送、历史回验用同一wire构造器。旧无版本历史仍逐字节重建v1；未知/null版本、v2缺字段或tools、坏shape均拒绝。原精确引用/finish/usage/身份校验保留。

## 真实免费模型

本次三次新真实请求。初始v2一次HTTP200/stop，引用坐标准确，但ID使用了不允许的连字符，被原校验拒绝；原记录 `intern-v2-extraction.json` 保留。作者一度把该失败误归为引用坐标，随后独审复核并更正；实际失败仅ID格式。

在v2提示schema副本补齐ID/targets正则后，沿同一原端点进行两次有界真实请求，相隔至少60秒。Source与Cold均HTTP200、原引用校验PASS；无重试、无付费fallback、没有新建或暴露凭据。完整安全assistant输出、实际usage和原request/response哈希见 `intern-v2-id-fix.json`。这两次是产品真实提取器验收，不是数据库生产控制器整链；语义/owner验收仍NOT_RUN/PENDING。

调用发生在最终提交前的同一实现阶段。`current-wire-identity.json` 从冻结提交的真实函数离线重建两次wire，均与实发哈希完全一致；该核验没有再次调用模型。

## 验证与保留失败

54项租约、协议、owned边界和legacy纯段检查通过，102.55秒。检查包含过期/撤回/换owner/换版本、同Attempt再次预约、monotonic回拨、预约写后旧lease过期、cleanup故障后VERIFIED仍保留，以及预约前回调重入不死锁。独审核对全部135项清单与唯一归零pin；hash见preflight。

先前定向执行发现旧测试fixture未传新protocol，以及一条仍期待已移除SOURCE_MISSING文案的测试；分别修复fixture调用和缺配置具体拒绝文案。原红日志保留。另一组 `test_model_settlement_continuation` 的旧SimpleNamespace fixture在基线bcc84b1a也同样被当前exact Worker graph要求拒绝：独立只读基线worktree重现日志已保存。没有为这组旧fixture放宽运行时类型检查，也不宣称全库测试通过。部分长回归已在首批失败诊断后中断，原日志明确记录15 FAIL/49 PASS/KeyboardInterrupt，不能当作整套通过。

`diagnostic-sampling.json.gz` 是本轮修改前、显式虚拟业务时钟的被动堆栈诊断：首Cold G0/G1实际wall约62.45/88.21秒。作者在第二Cold入口主动停止该诊断以查看热点，退出2；它不是业务时钟或完整交付证据。它说明单入口30秒续租无法容纳整个独占结算，不能把本轮新协议称作“原30秒性能通过”。

## 当前外部缺口

本云环境既有INTERN_API_TOKEN非空，真实提取已用它成功。`SIM2ACT_DATABASE_URL`未注入，也没有普通DATABASE_URL或PGHOST/PGUSER等连接；缺少现有生产应用连接和现有principal/project/trial/approval选择。没有创建新角色、凭据或权限；生产PG整链不能以SQLite Mock替代。

现有紧凑主工作区代码仍在本分支。Chromium先前因SUID sandbox配置失败；本轮正常Playwright Firefox启动也因`/proc/self/uid_map`只读、framebuffer失败，在180秒启动超时后结束，未导航应用。没有禁用sandbox、改权限、使用用户电脑或部署。没有当前截图、Library附件ID或1366×768/1440×900像素通过证据；需要平台可正常启动的受支持沙箱浏览器。

创建草稿PR此前被自动审批拒绝：认为缺少向T1doo/Sim2Act发布该分支/证据的具体授权。该拒绝没有被绕过；没有main合并、正式Release或部署。

## 完整真实时钟结算结果（失败）

原完整控制器测试在435.82秒后退出1。Source两次结算约1.71/1.69秒，各自真实提交预约及释放。首Cold G0完成51.6544秒，两次commit分别39.2508/5.8226秒，均返回；原五次SQL写入均执行且rowcount=1。G1在68.3411秒处触发120秒整段monotonic截止，结算总计120.1178秒，整个W5事务回滚，Cold无保存成果。这里只完成了原G0阻塞点推进，不能宣称完整修复或交付。该完整测试是6次Mock，真实模型为0，不能与上文两次真实提取拼接成生产整链。

完整失败日志、XML、timings、冻结清单和8个数据库/观察原件的压缩副本保存在`failed-1389ae00/`；durable-artifacts.json记录原字节SHA256。冻结167项源码/产物复核无差异。

## 断连恢复与性能诊断

云执行环境曾短暂unavailable，恢复后确认HEAD仍为完整1389ae00b85bce6ca581641c7c0a1a8209b428a9，源码无未提交修改、没有残留诊断进程。初版诊断在owned frontier上错误调用legacy input_key，被原保护拒绝，115.31秒退出1；保留codec-benchmark-initial.log。修正后的诊断只截获真实encoder收到的完整values，使用虚拟业务时钟，取得40次新鲜编码及100次各类哈希耗时后主动KeyboardInterrupt退出2，73.67秒；它不是完整测试通过或业务计时证据。

435519字节样本40次编码profile约0.087秒，Pickler.dump自身0.056秒，row_storage自身0.004秒。100次SHA256约0.0250秒，BLAKE2b-256约0.0441秒，分块SHA256约0.0269秒。换摘要没有净收益，单独C行投影也不足以解释主要成本；没有盲改摘要、启用未完成owned bridge或继续提高120秒上限。下一步仍需在完整边界保持下缩减重复编码，测量比微优化猜测优先。
