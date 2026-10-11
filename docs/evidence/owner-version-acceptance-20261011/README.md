# Owner 精确版本签收证据 — 2026-10-11

基线 `d3b375d13e1b235015ec5344152eb9b4c9668120`；独立开发分支 `dev/owner-version-acceptance-20261011`。完整范围见 [合同](../../F2/OwnerVersionAcceptance.md)。生成 text.literal_evidence 应用 → 已有内部 Release/实例 → 正常 Worker 新输入 → 手动冻结 → 每项人工决定 → 不可变声明/停止/重验/恢复。所有测试人工选择均 SIMULATED，不认领真实用户语义签收。正式发布关闭。

## 冻结与实际执行

`source-manifest.json` 保存首个 361 文件封版，因独审实际发现历史完整性缺口，该候选已撤回。`sealed2-source-manifest.json` 冻结修复后的同 361 个 Git 跟踪及新增产品/测试文件，仅改模块和新增回归测试。页面从进程内 HTTP 实际 GET `/`、CSS 和所有脚本，返回 200 后装入 JSDOM，逐次记录资源状态/内容类型/字节/SHA256。没有原生浏览器、网络模型、付费 API、部署或凭据变更。

最终作者 `author-sealed2.xml/log` 实际 142 唯一节点：**140 PASS / 0 FAIL / 0 ERROR / 2 SKIP**，408.30 秒。两项 SKIP 为 `test_pg_minimum_role_authenticated_internal_http` 与 `test_internal_lifecycle_application_role_no_grant_expansion`，原因为 `Application-role subprocess regression requires explicit isolated PostgreSQL`；不称 PG 已验。

`author-final-results.json` 核对 361 文件无差异。作者 25 页面实际 PASS，共 1058 断言、1020 个 JSDOM DOM 手势（另 2 条历史 Undo 诊断记录），51 次启动、969 次实际 HTTP 静态 GET；每次为 HTML+CSS+17 脚本，共19资源，所有200/类型/字节/SHA吻合。真实新输入和错误输入都经过正常 Worker，失败任务保留且无部分结果。10 个新增 owner 页面覆盖接受/拒绝、丢失 PREPARE/DECIDE 回执仅原 key GET 恢复、晚到预览/决定/读取及编辑/导航 ABA、取消、撤销、历史回执不复活、冷读取和新预览重新 PENDING。

独立封版关联集合 **73 PASS / 0 FAIL / 0 SKIP**（owner35 + 原文本应用13 + 实际页面25），367.72 秒；另自建21与原历史红探针2修复后独立重跑 **23 PASS**，78.88 秒。两集合分别记录，不能与作者重叠相加为唯一覆盖。纯设计评审不计测试 PASS。全树 Ruff 10、mypy 5 与前版最终基线逐条一致，静态诊断涉及的未改文件也与 d3 同字节；`static-baseline-comparison.json` 与改动 Ruff PASS 是实际证据。

独立 CONTROLLED 局部字段检查40通过：18个编辑控件×input/change共36项与4个单调选择守卫；它加载本地脚本、没有HTTP，是字段代次检查，不能替代上述实际可见页面链或原生 Undo。另有19个独立实际HTTP资源检查全通过及未知脚本404，它们不计入页面969次资源总数。原始日志/XML含 pytest 自带行尾空格，完整保留；产品与文档的排除原始证据 diff check 通过，完整原始输出见 `raw-diff-check.log`。

## 保留的失败和修复过程

- `original-red.xml/log`：同环境逐个 Git 原字节恢复 d3 的 81 个 src 文件，以 `red-fixture.py` 对缺失 owner API 实际执行，2 FAIL/404；`original-import-proof.json` 验证原包加载路径。它是新增功能的受控基线缺口，不是当前产品回归。
- `backend-first.xml/log`：24 PASS/1 FAIL；原 key 不存在时误映射 400。仅 owner GET 端点修正 OUTCOME_UNKNOWN/409，`key-fixed.xml/log` 实际 1 PASS。
- `backend-gaps.xml/log`：5 PASS/2 FAIL；测试夹具把 PUT 元数据当完整卡及误取 Release 的 source_app_id。改为实际 GET 卡及实例来源，`backend-gaps-fixed.xml/log` 4 PASS（含新结果、真实目标卡 ABA、真实切换 ABA、保留撤销预算）。保留原夹具失败，不称产品失败。
- `page-first.xml/log`：2 FAIL，现有 NODE_PATH 指向未安装 JSDOM 路径。使用当前 `/workspace/node-tools/node_modules` 原安装，`page-second.xml/log` 2 PASS；未安装新包或扩大权限。
- `page-owner-first.xml/log`：9 PASS/1 FAIL。实际页面已完成 DOM 流程，但加载时的 owner-review.js SHA 与测试结束后的源码 SHA 不同：作者在尚未封版时修正了晚到 4xx 的本页 pending 清理。这是实际源码绑定失败，不能计入最终通过；原资源 SHA 和失败均保留。冻结源码后完整重跑独立出证。
- `first-ruff.json` 保留初次新增代码的 B008 等静态问题，已修复。`intermediate-results.json` 只统计中间轮，不能加总为最终唯一节点覆盖。
- 独审实际红探针证实：较早 payload 修改、原 row fingerprint/seal 不变时，GET 会 STALE，但直接 PREPARE/DECIDE 仍能追加。修复为当前内容授权后全历史 payload 同事务验证，`history-fixed-author.xml/log` 实际 2 PASS，两个账本表前后完全不变。`owner_acceptance-before-history-fix.py` 为与首个冻结 SHA 精确吻合的只读历史证据；原独审红探针、错误回执保留，不覆盖。
- 首个封版作者 `author-final.xml/log` 精准 SIGINT 中断，58 PASS；`withdrawn-author-run.json` 保存原因和进程。这不是最终 140 节点覆盖。首个独审封版也中断撤回，按其原始日志/XML实报，不冒称未执行节点通过。修复封版最终新运行 `author-sealed2` 独立出证。

## 原证据与未运行门

`old-evidence-integrity.json` 核对之前三个 P-A 目录共 628 文件与 d3 全部同字节；这里只是历史字节桥。原 70 轮不在本轮计数、不当作重跑；更早 JSDOM 文件嵌入绕过 404 的证明范围撤回继续保留。本轮及独审新增真实 HTTP 资源回执独立计数。

完整256条历史耐久/性能资格、PG/应用角色、Windows、原生浏览器/视觉/系统 Undo、旧源码部署升级、真实模型、真实 owner 人工语义签收、完整 P-A/P-B、正式发布与部署、远端 CI 均 NOT RUN。独立 SHA 不因本地 PASS 获得远端 CI 绿色认领。
