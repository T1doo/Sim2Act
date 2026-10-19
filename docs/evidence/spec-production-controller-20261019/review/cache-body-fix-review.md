有限静审：最新缓存与归档来源修复

本次最新两处分支未发现新增 P1/P2；此前生产归档误标 OFFLINE 的 P2 已在静态代码中闭合。此结论只覆盖当前源码，第三轮在途原件未读取，不授予运行资格。

- `goal_applications.py` 的两处变更只让精确三个一致 `spec-production-controller.v1` Attempt marker 进入原 SourceReads opt-in。对已关闭 qualified-second 输入逐函数 AST 比较：`source_scope_gate`、原完整 `_source_scope_gate`、`_verified_candidate` 全同；`_journal_scope_anchor` 与 `verified_candidate` 在去除新增 import/marker 条件后全同。首证明仍完整，hit 仍先 owned scalar/项目和原权限重核，再核双标量锚与 epoch；异常清缓存。没有缓存生产 source/approval/permit。
- 原 `_SourceReads` 文件逐字不变，仍绑定同 Store、连接、driver 事务、线程及写 epoch，且只在 test_only SQLite 生效。这不证明非测试 PostgreSQL 上的耗时或 lease 可用性。
- `natural_source_archives.py` 用 `receipt_owner` 核过的原 Run/Attempt mode 选择 body provenance；RESPONSE 复算原 REQUEST 与 `_read` 的期望来源使用同一模式。旧 `_body` 默认 OFFLINE 保留。来源文字表示控制器通路，不证明真实 provider/免费权益。
- PB 的 `_source_prefix`、`_source_bodies`、`_resolve_source_before_extraction` AST 与已关闭第二轮相同；PB archive 仍强 MOCK，原 test_only SQLite/PB 合同门保留。没有借新 provenance 扩 PB。
- 固定 `resolve_account` 函数 AST 不变，仍 SOURCE_MISSING 默认拒绝。最新公开 offline 入口的 ProductionBinding 拒绝在 source/journal/adapter 之前；旧 mock 无 CoreAttempt 历史兼容仍由独立 frozen.mode 锚定。

纯文件核对原件为 `cache-body-fix-observer.py`、`cache-body-fix-verification.json`、空 `cache-body-fix-observer.stderr`；观察器退出 0。未执行产品、测试、DB 或网络；未修改仓库。现目录暂不封存，等待闭合第三轮证据。第二轮真实 2 PASS/1 FAIL 和正例 Source 尚未完成的限制保持不变。
