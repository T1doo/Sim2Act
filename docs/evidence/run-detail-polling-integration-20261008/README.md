# 已审页面读取修复整合到 dev

按父线程明确授权，`dev/f1-foundation` 从 42b7a992 普通快进至候选 8bcafb0；
产品/原测试/脚本/锁/工作流字节与已独立审查源码
`3fe824b826df6f1040989ddb5f821290dfc33e4b` 完全一致。
仅增加整合证据，不带入后端修改或诊断仪器，调查分支保持独立。

父线程另一个执行环境报告限定实测通过：source 3fe824b，SQLite/PG 各
12 页面病例、101 断言，旧各 2 个确定性反例 FAIL、新 PASS；403/切换晚响应/
并发点击/新状态轮询与确认保护通过。该报告来自父线程消息，原始文件未复制
到本检出；不冒充本轮新运行或原生 Edge，也不是人类签收/完整 F2 验收。

本轮必要整合检查用原页面聚合、新确定性交错、原自然目标 valid、后台轮询、
读取失败恢复，实际两后端各 5 项均 PASS：SQLite 16.97 秒，PG 30.00 秒，0 SKIP / FAIL。`run_checks.py` 保留精确选择、collection、
stdout/JUnit、实际页面 proof 和逐文件前后 SHA；结果在两份 summary。
所有测试顺序执行，无并发 pytest；Ruff 与 mypy（52 文件）均 PASS。Node/jsdom 使用新私有安装目录，PG 为
固定原 17.9 digest、network=none、无端口、私有 socket 和合成自有 schema。

**全量首轮仍是原源码的 SQLite 1954 PASS / 97 SKIP / 0 FAIL，PG 2021 PASS /
28 SKIP / 2 FAIL，不宣称原全量全绿。** 页面竞态修复有旧源码确定性反例及
已审候选双后端去重 93 项支持；第二个 `resources-history` 原 10 秒超时仍
未解释。独立受控阶段调查没有提交产品补丁，见
[调查证据 e49e272](https://github.com/T1doo/Sim2Act/blob/e49e27241811fe1be52f8e0b74afd963559a126c/docs/evidence/pg-history-timeout-investigation-20261008/README.md)。

调查只证实正常原节点的池/事务/退出有界，且诊断校准能区分 Python 校验等待
与客户端退出等待；首轮缺少 Future/线程/池/资源快照，不能用重跑 PASS 推断
资源干扰。校准注入、仪器自身一次 NameError 与无故障观察均分别保留，不算
产品新 PASS 或原根因证明，未修改任何旧断言/超时。

[原 F2 状态矩阵](../linux-convergence-42b7a99-20261008/F2-status.md) 保持：通用
P-A/P-B、非 CSV 明确要求变更实际检查闭环、PROJECT 扩验实际消费/回执仍缺；
内部 Release 已有受限工程实现，正式发布关闭。Win11 普通用户安装/重启与
实际 Edge、通用真实任务、语义/人工验收仍未完成。原 Windows900 / Edge240 /
Node150 不改，LIVE=0，真实模型=0，无新 CI、部署、main/强推/安全权限改变。

整合后复现页面读取回归，可在原开发环境按正常 Node/jsdom 设置运行：

```bash
LIVE=0 SIM2ACT_LIVE_ENABLED=false NODE_PATH=<private-node-modules> \
.venv/bin/python -m pytest -q tests/test_run_detail_polling.py \
 tests/test_product_integration.py tests/test_background_poll.py \
 tests/test_task_read_failure.py \
 'tests/test_natural_goal_ui.py::test_natural_goal_actual_http_ui[valid]'
```

PG 需显式自有隔离 `SIM2ACT_TEST_DATABASE_URL`；不要指向共享数据。
原完整页面、身份/项目入口和执行确认逻辑保持，修复只保护正在读取的详情。
本轮所有自有资源在测试结束后按 `cleanup.py` 核零并删除，结果在 cleanup.json。
推送前重核远端 dev 基线/main/候选、祖先和无并行变化，使用普通推送及
`[skip ci]` 提交，不触发未授权新 CI。
