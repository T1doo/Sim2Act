# 空目录自然 P-A 连续向导：工作区实现只读独审

2026-10-16 UTC。基线 HEAD `9d12e321d556c4b9c6ec2bf1ef4ccd7b958a645c`，本轮根为唯一仓库写入者。本报告审查当前未提交的 api.py/index.html/app.js/goal-application.js/internal.js 差异；没有仓库写入，没有真实模型、Worker 或旧矩阵执行。待源冻结及实际新用例结果后补最终 SHA/证据。

## 已核主合同

- capabilities 新 `natural_spec_generation` 是 read-only metadata。仅 Store.test_only + mode mock + !live_enabled + provider intern-s2 返回 OFFLINE_TEST_ONLY，其余 BLOCKED，live_request_allowance固定0。不新增 activation/Grant/executor；原自然 API 与实际 wire guard 保持 offline-only、MockTransport 必须。
- 原自然 start 现先 fresh GET capabilities，核固定版本、known availability、provider/allowance/mode。blocked/缺字段/错误返回发生在 goalApplications entry 和 generation POST 之前。合法 mock 不要求 gaapproval；通用 provider choice 仍不能给自然 LIVE 兜底。
- 首次向导复用共享材料/Goal form 和既有准备保存锁；每个 save、next、继续生成、generation start/read、候选双 ack/confirm、内部 check/version ack/commit、实例创建、返回目录均保留显式用户动作，未见自动连 mutation。
- 保存 Goal 后恢复共享表单并保留当前已填写 draft，使用精确 savedCard 历史建立 activeGoalCard；自然 family 固定，生成读取仍核完整 frozen Goal、candidate digest、原 request key 与 sample-preview。
- guide 身份/连接/项目/工作区/appGeneration 和精确 saved Goal、family/expectedAppId 联系保持。clearApp/showApp/selectWorkspace 的 preserveFirstGuide 只由 exact naturalFirstGuideForEntry 经原 openGoalApplication 传递；普通用户导航/Goal切换/身份切换会取消，已接受后台对象不被删除。

## 候选打开 fence 的专项结论

`openGoalApplication` 只有在 showApp 完整返回 shown、context.current、activeApp/project 均通过后，才调用 exact naturalFirstCandidateOpened，并按 `engineering.selectionCurrent === context.current` 清该函数引用，再同步 selectWorkspace(apps, guide)。这些检查至 intentional workspace 切换之间没有 await。释放范围是本次成功打开的 view，没有提前释放等待 GET 的 fence；避免了原代码因成功切换工作区而永久把 engineeringCurrent 变 false 的问题。

取消 internal 阶段另外按 g.view===engineering 清旧 internal view，防止其 pending 回填；不删除后端已存应用/Release/实例。

## 独审发现

### 已修：first 模式未知 Goal 意图 reset

初版 reset 只 clearNaturalUsePreparation，留下 stage=inputs 的 guide、disabled start 和已消失 forms。已报根并核修为 firstCreation 时 clearNaturalFirstGuide，否则保留原 per-use clear。零新增 POST、无自动认领。

### 已修：同 Goal key 的旧 capability 请求清锁

初版旧 capability GET 在相同 Goal key/不同 selection 返回后删除 Map，但 gate.current=false 不 render，当前新页面 start 会残留 disabled。已报根并核修：删除自己的 gate 后，当前 key 相同则 render 当前状态；旧 availability.current 仍 false，未采用旧可用性，不产生 generation POST。

### 待修：合法长 Goal 标题与应用名称限制

continueNaturalFirstGoal 当前直接令 goal-application-name=card.content.title。Goal title允许200码点，而 ConfirmInput.name最多100；HTML maxlength不截断程序赋值。合法101–200标题可因此使候选确认400，且原 confirmBody 已冻结，用户无法直接缩短后重提。

已报根：只对默认应用名称按Unicode码点安全截到100（例如 Array.from(title).slice(0,100).join('')），不更改完整Goal标题/内容。不需要扩大后端或重模型测试；一条轻边界断言即可。

## 实际静态检查与证据限制

`git diff --check`，app.js/goal-application.js/internal.js 的 `node --check` 实际通过。本独审本阶段未运行动态用例。

检查时产品 hash：

```text
106118cb44ce1763a2f84a91b8d370a4bab4f7fd22e08dfbb1f773e3025372d7  api.py
5f2b8858d232e5db992e380f20eec65969ff7a23fd2141ae905e17eff433109c  index.html
1a2cc52f85d9214cd3f8157157eda6ca9e8522d0200733a2a0339bd0b5786406  app.js
c421e74077718155bc15806feb664ff7d67489138cbf9ca243f52924cc40754f  goal-application.js
ae076c3b664cadcc39cee5401b3b4b9be0b2733860d7b766f25beb76d421d708  internal.js
```

当前结论：除上述默认名称边界外，有限静审未见新的权限/LIVE放开、自动 Run 或过早 fence 释放；动态零开始链、blocked 零 POST、迟到读取/reset 的结果待实际回执。不同源码阶段必须按精确 served assets/最终冻结 SHA 分别报告。无 Windows/PG/真实模型/真实语义/远端CI/部署证明，旧多历史心跳失败未被解决。
