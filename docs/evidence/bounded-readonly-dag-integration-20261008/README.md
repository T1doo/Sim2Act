# 四节点只读组合：限定独审后的 dev 整合

已按父线程报告的限定独审整合候选 c9157fcc66036b6d715542623862bc2efe39da1f。
已审产品源码仍为 **67807be6940cda16007a6a0cca90d9b04a589461**，没有产品代码修复。
整合复验执行 HEAD：**4fcf0486c5336f49eff3793da06abd7f082813d5**；其后只追加文档/证据。
[独审范围与整合前核验](review-and-integration.md)完整记录父线程报告，不能扩大成 F2/AT13 验收。

## 实际整合复验

| 环境 | 收集 | 结果 |
|---|---:|---|
| SQLite 隔离夹具 | 15 | 13 PASS、2 SKIP（PG 最低 CRUD 角色） |
| 自有隔离 PostgreSQL 17.9 | 15 | 15 PASS、0 SKIP |

`scope.json` 为本次必要范围，不是旧全量重跑。执行前后源码、测试及 docs 内
升级 harness 哈希一致，原断言/锁/脚本/工作流字节不变，收集 ID 与 JUnit 一致。
各后端 summary/provenance/log/JUnit 及实际页面/升级证明已保存。

- 四节点双新输出 30/15，条件跳过的独立支路、第四节点冷恢复、同键并发、
  精确确认/预算、原三节点兼容及原锁门控通过。
- 原两个真实源码 archive 升级（5a5543c…、1b65e94…）通过；另实际加载整合前
  dev a02371d…，模块 SHA256 为 d315701b8995a37d8faaff00bdbb806c732a5c4936b8f106e6b4e81941f9caf9。
  旧证明与旧确认失效，重新派生和确认后创建三节点及四节点新运行；新四节点
  amount=30、quantity=15，旧历史行及原始 JSON 字节均保留，不迁移/重签旧证明。
  见 `*-actual-proofs/test_latest_dev_actual_source_0/composition-upgrade-proof.json`。
- PostgreSQL 的已有最低 CRUD 角色 true/false 新组合路径、冷 Store 回读及同键
  恢复通过；角色无超级权限，DDL 尝试被拒绝，身份/授权/资源/旧草案保持。
- 原页面两例各 14 个 HTTP/DOM 断言，通过实际新 Run/Operation 读回双支路，
  丢失接受响应同键恢复、冷页面历史和删为单节点；这是 JSDOM，不是原生 Edge。

父线程限定独审已另报告 SQLite/PG 各 39 独立 PASS，以及四种真实 SIGKILL
重领、第四节点事务回滚等；本次作者整合检查不冒充独立复审、不重复其全量。

## 边界、复现与清理

语义 UNKNOWN、用户验收 PENDING、发布关闭；LIVE=0，无模型、业务写入或新授权。
原 max_tools/max_requests=4、Windows900 / Edge240 / Node150 不变。
原生 Windows/Edge、非 CSV、PROJECT、通用 P-B、真实任务 gold、完整 F2/AT13 仍未完成。

[用户页面/API 指南](../../F2/BoundedCsvCompositionQuickstart.md)。复验必须保持
LIVE=0 / SIM2ACT_LIVE_ENABLED=false，并显式指定自有隔离数据库与 Node/JSDOM 目录。
run_frozen.py 使用 PYTHONPATH=src:tests；三份旧源码 archive 的环境变量为
SIM2ACT_UPGRADE_OLD_ARCHIVE、SIM2ACT_UPGRADE_CORE_ARCHIVE、SIM2ACT_UPGRADE_INTEGRATION_ARCHIVE。

`cleanup.json` 证明本次独占容器无网络/无端口，测试 schema、临时角色及 public
表为零，并正常清理自有容器、镜像、npm/cache、archive、测试目录及初测日志。
普通 dev 推送前再次核直接远端祖先；所有本次提交使用 [skip ci]，不推 main、不部署。
