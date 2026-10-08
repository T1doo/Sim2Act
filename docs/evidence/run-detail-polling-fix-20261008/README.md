# 显式任务读取与后台轮询竞态：修复候选

产品候选：`3fe824b826df6f1040989ddb5f821290dfc33e4b`，分支
`dev/run-detail-polling-fix-20261008`。首轮证据提交：`7ab6390`，冻结原源码
`42b7a992524d9f2e00136711c70cb4e16f3e419b`。

## 首轮结果与根因

原全量各执行 2051 项：SQLite 1954 PASS / 97 SKIP / 0 FAIL（1528.84 秒）；
PostgreSQL 2021 PASS / 28 SKIP / 2 FAIL（2836.28 秒）。原源码前后哈希一致，
[完整首轮证据](../linux-convergence-42b7a99-20261008/README.md) 不覆盖、不改成全绿。

第一个失败为自然目标页面 `valid`：异常读取后有效计划的确认框缺失。
后台 `showRun(false)` 也推进选择代次，抢占正在等待实际 HTTP / 异步摘要的
显式读取，显式动作完成但确认区尚未完成。新增 oracle 实际服务原完整页面，
持有真实 loopback HTTP 响应、调用页面原后台定时器；原源码先确定性重现额外
后台读取，再直接重现缺失确认框。见 `baseline-*-pg.log/xml` 与
`baseline-ui-missing-failure.json`，加载哈希为原 `app.js`。

修复只增加 `app.js` 十行包装：同一身份、项目和 Run 的显式读取期间跳过后台
详情读取；结束/失败后释放。对象引用比较保证旧前台结束不会清除新前台保护。
原身份、项目、选择代次、selectionGuard、回执校验和错误恢复仍执行。
新增两个独立回归文件，原测试断言、超时、锁、脚本和工作流均未改。
[独立只读审查](independent-review.md) 为 LIMITED PASS，无产品阻断问题；其提出的
新夹具迟到响应清理风险已用 closing 标记加固，并在双后端再次验证。
新增 oracle、原自然目标 valid 和原页面聚合均 PASS。

第二个失败为 `resources-history` 原 Future 等待 10 秒超时。保留的真实 PG
锁证据显示项目锁顺序正确、没有 SQL 错误/死锁；图历史阶段记录持续约 17.76
秒才结束。原五项锁用例在原产品代码上单独复查均 PASS（30.31 秒，history
用例总时间 9.636 秒）。这只说明未复现，不能认定产品锁缺陷、夹具故障或资源
干扰已经解释。该超时的根因仍未判定，本修复不声称解决它。

## 定向验证与边界

SQLite 原页面批次 43 项：41 PASS / 2 SKIP（258.95 秒）。随后候选哈希约束
补充 51 项：51 PASS（173.52 秒），包含加固后的新 oracle。去重覆盖 93 个
节点：91 PASS / 2 沙箱 SKIP。前一批在源码提交前运行，但 30 份实际加载
`app.js` 回执与最终候选哈希一致；新 oracle 清理变更经补充批次再次验证。

PostgreSQL 同一 93 项：90 PASS / 3 SKIP（623.72 秒），无失败、源码前后哈希一致；精确结果见 `pg-target-summary.json`。
选择、实际节点、前后逐文件哈希、stdout/JUnit 和原页面 proofs 全部保存。
这不是修复候选重新执行全部 2052 项，也不是 Win11/Edge/人工签收证明。

`ruff check src scripts tests`、`mypy src` 和 JavaScript 语法检查通过。
LIVE=0、真实模型请求=0；原 Windows 900 / Edge 240 / Node 150 保持。
无新 CI、main 写入、强推、部署、生产凭据配置或安全权限扩大。
实际 Win11 普通用户安装/启动/停止/重启与 Edge 仍 NOT_RUN；Linux/JSDOM
不得替代。受保护 Chromium 门控 SKIP 不使用 no-sandbox 修复。

## 复现与交审

在候选分支安装原依赖、Node/jsdom，然后执行：

```bash
LIVE=0 SIM2ACT_LIVE_ENABLED=false NODE_PATH=<private node_modules> \
.venv/bin/python -m pytest -q tests/test_run_detail_polling.py \
 tests/test_natural_goal_ui.py tests/test_product_integration.py
```

使用自有隔离 PostgreSQL 时另设 `SIM2ACT_TEST_DATABASE_URL`；不要指向共享数据。
`run_targeted.py` 保存完整选择和源码哈希，拒绝覆盖既有 summary。首次复现
必须使用新证据目录；原源码反例应单独检出 42b7a992，并只带新增 oracle，
不要反向覆盖已有全量目录。实际测试的自有 PostgreSQL、Node、档案和临时
目录在全部测试终止后由 `cleanup.py` 精确清理，结果在 `cleanup.json`。

候选交父线程审查，不合入 dev/main。下一步先受控定位仍未判定的 PG
10 秒超时，不靠重跑绿放行；再按 [原 F2 矩阵](../linux-convergence-42b7a99-20261008/F2-status.md)
推进现有非 CSV 明确要求变更的实际输出/检查闭环和 PROJECT 扩验受权终态。
