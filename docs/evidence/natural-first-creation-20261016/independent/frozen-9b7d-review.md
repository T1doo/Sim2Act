# 自然应用首次创建向导：冻结提交有限独审

审查提交：`9b7d30b8f4aec699b1c3b9574b6dc6971ca4262e`。比较基线：`9d12e321d556c4b9c6ec2bf1ef4ccd7b958a645c`。审查日：2026-10-16。审查者仅只读仓库；根线程是唯一仓库写入者。

结论：在本报告列明的有限静审范围内，未发现阻止交付的未修缺陷。此结论并非完整动态验收通过；源冻结后的从零 HTTP 正例仍由根线程执行。旧 WIP 报告 `/tmp/f2-first-natural-creation-implementation-review.md` 保留原样，本报告替代其中对当前源码状态的判断。

## 冻结核对与已关闭项

- 本次实际 `git rev-parse HEAD` 为上述完整 SHA，`git status --short` 为空。基线到冻结提交的 `git diff --check` 通过；`app.js`、`goal-application.js`、`internal.js`、`use.js` 的 `node --check` 通过。
- `app.js:continueNaturalFirstGoal` 的默认应用名确为 `Array.from(card.content.title).slice(0,100).join("")`，与后端应用名 100 码点上限相容。保留的 `activeGoalCard.snapshot` 与完整 Goal 标题、正文没有被该操作截断。先前 WIP 长标题项已关闭，不是 remaining blocker。
- 能力读取结束的 finally 仅移除本次 gate；当前 key 相同即重新渲染当前状态，旧 gate 的 current 为 false 时不会采用其可用性结果。相同 Goal ABA 的按钮残留禁用问题已关闭。
- 首次模式的未知 Goal 保存回执重置会 `clearNaturalFirstGuide()`，不留下已还原表单但无法继续的 guide。取消内部阶段还会对精确当前 `g.view` 调用 `clearInternal()` 断代际；不删除已保存内容，不声称取消后台工作。

## 本轮核对的安全与交接合同

1. 空目录入口仅启动共享 TXT/MD 材料及 Goal 准备。保存材料、保存 Goal、继续、生成、双确认候选、内部检查、保存 Release、创建实例、返回目录均由不同显式用户动作触发；没有新增 executor、Grant 类型或自动 Run。
2. 新能力字段只读。仅 test-only Store、mock、live disabled、intern-s2 返回 OFFLINE_TEST_ONLY；真实请求额度始终 0。前端自然生成每次先重新 GET 能力，不合格或读取失败在建立 goalApplications 意图及 application-runs POST 前停止。原 wire、权限和 check_provider 未改，实际离线发送仍须原 httpx.MockTransport 检查；该 metadata 不是模型批准，未开放 natural LIVE 路径。
3. guide 保留只由精确对象传给受控 showApp/selectWorkspace。身份、连接、项目、workspace、应用选择和 Goal 选择/编辑代际均继续核对。取消通过 clearGoalCard(true) 失效旧生成/确认 handoff，内部取消只清当前精确 view；普通导航不会把 guide 扩大到另一个选择。
4. openGoalApplication 在 refreshApps、showApp 的读取都完成后再次核对 shown、context.current、精确 app/project，才按同一函数引用释放临时 engineering.selectionCurrent，再进行受控 workspace 跳转。没有在未完成异步打开时提前释放，后续内部操作仍依赖原内部控制器自己的守卫。
5. naturalFirstCandidateOpened 核原 entry 的 expectedAppId 与当前工程 view；Release 完成观察只接收该 view，实例观察再核该 Release id/fingerprint 与当前实例 id。向导返回目录仅刷新读取；创建版本、创建实例不隐式执行。
6. 原候选回读、完整目标/样本/指纹、双 ack、原 request_key、未知回执只读恢复与内部 per-use 规则仍由现有控制器实施。目录继续只使用 owned summary 元数据，不批量读取自然应用私有历史或把 metadata 当权限证明。

## 证据范围与未执行项

- 本审查者实际执行：冻结 SHA/status、静态差异检查、四个生产 JS 语法检查；并阅读本轮产品差异、新 HTTP/可见 DOM driver 与说明文档。尚未独立运行新增轻量 probe；如收到最终 probe 将在独立追加记录中列出实际结果。
- 根线程报告缺配置 HTTP WIP 正例已通过，此处没有将其记作本审查者独立执行；完整源冻结的从零 PA HTTP mock 正例仍在执行，不预先认定通过。
- 新 available HTTP 测试的精确范围是：空目录首次材料/Goal 生成候选，保存内部版本/实例，返回目录，第二份材料/Goal 进行该实例的首次 Run 并产生 result_version 1。它没有先执行第一份材料的实例 Run，不能据此宣称验证了旧实例结果保留或第二次实例结果 v2。
- 新 owner/result UI 核对的是同一 Run 的结果与人工验收入口；本轮这条链不会实际提交人工 DECIDE。原有此前验收是其他独立证据，不把它拼成新单批通过。
- 无真实模型、Windows、PG、远端 CI 或真实语义/场景验收。没有重跑旧恢复矩阵，也没有声称解决旧多历史 heartbeat 数据库锁故障。

## 冻结生产文件 SHA256

```
106118cb44ce1763a2f84a91b8d370a4bab4f7fd22e08dfbb1f773e3025372d7  src/sim2act/api.py
5f2b8858d232e5db992e380f20eec65969ff7a23fd2141ae905e17eff433109c  src/sim2act/web/index.html
515d2d427bf0074e0f25f178e3043cdcf989ec968645ba2693dc284d024d2dd1  src/sim2act/web/app.js
c421e74077718155bc15806feb664ff7d67489138cbf9ca243f52924cc40754f  src/sim2act/web/goal-application.js
ae076c3b664cadcc39cee5401b3b4b9be0b2733860d7b766f25beb76d421d708  src/sim2act/web/internal.js
a3af90ffd734335beceaebe26996393f4fad33752a9f82e2bee338bf04417c97  src/sim2act/web/use.js
```
