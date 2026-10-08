# 已审产品字节的 dev 整合

父线程于本次授权报告限定独审通过，无新增阻断：最终产品源码
67807be6940cda16007a6a0cca90d9b04a589461；SQLite / PG17.9 各 39 项独立 PASS，
四种真实 SIGKILL 重领、第四节点事务回滚、双支路新算术、授权/预算/fence、
旧对象字节保持及 16 个页面断言通过，源码与文案差异链核验通过。
这是父线程报告，未把作者测试冒充为独立审查。

独审未覆盖原生 Windows/Edge、最低 CRUD 角色重测、完整旧源码升级、非 CSV、
PROJECT 或 AT13。整合只补必要检查，不改变产品逻辑或扩大权限。

直接远端 dev 为 a02371d44208dc2bc4b561a540dd4afa665e57d8；候选为
c9157fcc66036b6d715542623862bc2efe39da1f，main 为
6f688e4dd80b5c81d41aecde90e360d3629f9c21。确认工作树干净、无 merge/rebase/
cherry-pick/revert/sequencer，候选是 dev 的后代，候选与已审源码的产品/测试/
schema/脚本/工作流字节一致，然后本地 fast-forward dev。未依赖过期 tracking。

整合复验增加一个 docs 内的隔离测试 harness（不是产品代码修复）：实际载入
旧 dev a02371d 的 archive，并复用原升级断言；确认旧证明/原确认失效、旧历史
字节保留、重新派生与三节点新确认后，再显式保存并确认四节点新组合，产出
amount=30 / quantity=15，复核所有先存历史行及 JSON 字节仍在。

另外重跑原两个更早源码 archive 升级、四节点双支路、条件跳过、第四节点冷
恢复、并发同键、精确版本/预算、原三节点兼容、原锁门控、原页面两例，以及
已有自有隔离 PG 最小 CRUD 角色 true/false 组合路径；不会重跑旧全量。

产品保持语义 UNKNOWN、验收 PENDING、正式发布关闭，LIVE=0。
原 max_tools/max_requests=4 与 Windows900 / Edge240 / Node150 不变。
每个提交带 [skip ci]；整合证据与清理完成后才普通推送 dev，不推 main，不部署。
