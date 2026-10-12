# 精确安装窗口回归的证据边界纠正

基线提交 `e2b856bb453fc74452583fa10843148758e2d9b9`，同一授权开发分支 `dev/pb-text-extraction-20261011`。本跟进目前只完成只读源/trace核查和待审文档纠正；没有新的动态测试PASS，没有修改产品或测试源码，没有重跑或改签原492分母。

父级指出的缺口已按原字节核实：[trace审计](baseline-trace-audit.json)包含旧作者candidate4及独审extra-latest两份原路径/SHA。两者均 `latest_reads=0`，仅一次 `require_latest=true` 查询且HTTP409，另一actor prepare201；旧结果可证明更早发生的supersession被拒，不能证明已进入候选安装窗口。原 `.cjs` 用任意 `/api/apps/` task_proof预读设置candidateReceived，request hash触发缺少“已收到原key首回执200/精确安装候选GET及真实hash”的阶段条件。

撤回旧维护与独立extra-latest对“原安装异步窗口已动态复验”的具体推论。原492PASS/10PGSKIP/1deselected和独审分组仍是各自历史执行事实；其他分母及授权路径仍在父级独审，本跟进不重新签收或加总它们。原红绿、三个withdrawal、733/11/282清单、原trace和源快照均不删改。这里不据证据缺口认定当前产品漏洞仍在。

[精确源SHA](baseline-source-sha256.json)分列当前生产JS、维护驱动及已存档修复前JS。当前生产代码先完成candidate/request hash，再最后require_latest GET、同步检查回执，顺序可以静态确认；其动态时序资格在本跟进尚未完成。没有在共享源中恢复旧JS，也没有执行或服务旧源。

待取得的同一精准probe必须记录完整原key/候选身份和顺序：首个require_latest200 → 精确安装候选GET及其真实SHA完成 → 该阶段真实并发prepare201 → 最后require_latest409；并断言前端零POST、旧候选未安装。不能把bootstrap/list/source预读当安装候选，不能以任意409代替最后GET。相同触发条件对修复前源应失败、对当前源应通过；未取得就不能认领该资格。

当前具体阻塞见[完整原拒绝](current-rejection.json)。对现有 `/root/pa_independent_review` 的精确对照与独审委派被平台风险筛查标记“possible cybersecurity risk”，代理本turn失败。已停止该受拒动作，没有改名/改写请求、换代理/工具/环境重试，也没有转由root执行该精确对照。仅完成可独立进行的原证据保全和声明纠正。精准修复前/当前动态probe及该轮独审均 `NOT_RUN_CURRENT_BLOCK`/`BLOCKED`。

本跟进没有提交或推送：用户要求独审后普通推送，该独审当前受阻。这批文档是具体可审候选；远端仍为e2b856，main/core dev不改，旧证据保全另按[工作区核验](workspace-preservation.json)记录。解决当前平台拒绝之前不能签收精确安装窗口，也不能以原广义PASS替代。
