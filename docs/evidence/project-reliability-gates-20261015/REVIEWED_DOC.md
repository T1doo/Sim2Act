# 项目 CHECK 取消、原 Run 历史与有限试验原语整合

接续正常推送的 `80329152ff4b9f39c72f59fafed4828f0d68b6bb`。根工作树单一集成者，分包在独立工作树/数据库完成并分别独审；main、f1-foundation 与既有开发引用不修改。

## 已交付的有限产品行为

项目页面明确 GET 原 Run 历史，核对用户点击时的精确项目/key/清单/应用/CHECK/Run/Release/版本及取消状态。失联仅读原 key；撤权后只恢复公开控制元数据，恢复失败清除旧私人结果并保留未决原 key。历史读取不创建 Run、重发取消或释放证据锁，迟到响应不能覆盖另一明确 Run。

普通 Worker 对已确认取消、原租约真实过期且完整持久回执证明已知的 PROJECT CHECK 回收为 CANCELLED；递增 fence/version，同事务更新 Run/AppRun 与完整回执。每轮最多 16 个候选，进程内游标仅公平扫描，坏候选不获得执行权限或阻断普通队列。未知保持 RECONCILING、不派发或填零；已有用量/效果/无关对象/人工锁保留。后台回收读取原持久模型审计字节验证指纹，不重取受撤权 Goal/材料，也不重放语义；不能将整个 helper 称为只读标识元数据。实际 queued pause→resume 使用原 frozen contract 的 Limits，修复原 None.model_dump 错误，不扩预算。

## 离线 P-A 试验原语

新增精确 Trial/Stage 批准、原 key 历史恢复及跨 Run 不可退款总账。仅 P-A：Generate/Source/Cold 为 3/2/2 槽，冻结材料/完整 Goal/身份/软件/原未来 key/预算与独立截止；阶段绑定真实 Run/runtime/实例/Release 和同试验实际 Generate 三 Attempt 的 wire/raw/usage。原槽 UNKNOWN→KNOWN 仅相同响应指纹/字节与原已知分量单向补齐，保留初始历史，accepted 不恢复，已耗槽不退。

这些是离线控制器工程原语及实际 synthetic Worker 组合。**生产 LIVE API/sender 尚未接线，P-B 真实试验合同未实现；生产运行仍默认拒绝**。唯一收费证明实现为 test_only SQLite 的 SYNTHETIC_ONLY，不能代表真实免费权益或用户布尔“免费”。没有读取/配置真实凭据、真实模型或付费调用，没有部署。

## 实际源码与结果

| 冻结源码 | 实际结果 | 范围 |
| --- | --- | --- |
| `ce6a0595c47dde0c5561265c3dbfa2ccc9b8721d` | 52 唯一：51 PASS / 1 FAIL / 0 ERROR / SKIP | 取消阶段；原双应用第二 Run 三次领取仍 RUNNING，未修，完整失败封存于上一阶段 |
| `92c7cbd8f103fad9519479c58ded63a311667956` | 95 唯一 PASS / 0 FAIL / ERROR / SKIP | 根 60 核心 + 8 HTTP/JSDOM 页面 + 27 预算；各 483 文件前后 0 diff |
| `b5b6e62c92f560bb3d8fb3f40f23bf9d6e4cde51` | 82 唯一 PASS / 0 FAIL / ERROR / SKIP，另 2 deselected | 类型收窄后的当前批准/预算/22 资格负测；483 文件前后 0 diff |

92 源码七槽真实 mock Worker 3+2+2 全部结账/accepted，7000 mock tokens、48354 保守 reserved envelope，六个相邻间隔均至少 60 秒；原 Run 300 秒/lease 30 秒未改。8 页场景为 119 内部断言、143 动作、887 API 请求、189 静态资源/9 次启动；189 资源均 200/精确 SHA。不是原生浏览器。当前类型修复仅 Any/cast 与已有条件隐含的非空收窄，加两份精确资格文件；旧七槽和 95 PASS 不伪称当前新字节重跑。当前 82 例与独立行为桥分别封存。

全库 mypy 在 92 先实报 19 错（旧 5 + 新预算 14），原输出保留；修复后当前仅 status_report 三项/tools 两项既有错误，预算新增错误已消除。当前 scoped Ruff PASS；原 Node 两检查 PASS，JS 与 cjs 字节未因类型修复改变。整合时 I001 import 排序失败与修复历史也保留。

精确资格为原 78 + admission/budget/recovery = 81 模块；pin `276815ce7ff92ecec3b377f7896928c71f8774c8036a16f7e7bdcab054295586`，review_candidate `a72d2deedcbb93a39554bd14034ea7cf01bc5db3`，仅唯一 pin 字面量归零规范化；ANCHOR/CHANGED/config 排除及原键/来源/基线不扩。

环境重启后核原 result/XML/483 前后与当前源码及 owned 进程均终态，无未知测试重复启动。辅助旧失败夹具副本公开控制读回 CANCELLED，但完整状态 409 旧图基线冲突，原历史数据库当前 SHA 对更早记录不等；来源未确定，不作私有诊断，辅助项 NOT_VERIFIED，不计 pytest PASS。原 43/8d 页面失败、两轮试验失败及未知末槽、全部修复前源码/日志保留。

## 未过的门

原双应用进度回归未修，不能签整个项目通过。生产接线、合法强制零收费证据与精确真实试验批准，干净 Win11、当前 PostgreSQL、原生浏览器、真实模型/人工语义、完整 P-A/P-B、真实旧源码升级、部署/远端 CI 都不能签通过。整体 NOT_ACCEPTED / BLOCKED_UNKNOWN / owner PENDING / semantic UNKNOWN / publication false。

用户硬目标为北京时间 2026-10-22 00:08（UTC 2026-10-21 16:08），不是已核实赛事截止。原 V5 首版仍 F1→F2→F3→R0→C0。最长外部依赖是零付费证明/精确实际试验授权、Win11/PG原生条件、真实材料及独立语义/公平对照、赛事与第二项目身份。P-A/P-B 是两条路径，不是两个项目；这里只明确 Sim2Act。最小合并输入为第二项目和官方规则/主体、原生设备操作者、材料及 owner、无秘密的免费/强制不收费证明；token 不发聊天。详细只读关键路径报告与其 17 文件指纹随最终证据包保留，不给未验证百分比或完工保证。
