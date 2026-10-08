# 受限 CSV 接线：作者候选证据

分支 `dev/csv-wiring-patch-20261008`；冻结源码及测试 SHA **`645e49479974fa033a19028e195304108afd51b8`**。基于原本地暂停检查点0ec1f29。DAG两P2修复源码依赖4c7d81b，取入为bd4c549/e8c3678，唯一冲突保留wire_proof并使用严格整回执指纹。原独立审查分支3b3534ca保持不动。本接线候选及修复依赖的独立验收 **PENDING**，未并入dev/main，发布关闭。

实际功能是原三节点页面/API中的三个serverallow语义端口，各两个来源；自动生成report双前驱、保留preview验证屏障。方案/精确确认/实际intent/receipt/来源hash/冷恢复都绑定所选来源。没有字段时旧接线兼容；新允许列表用 `/options/wiring`，不占用旧合法wiring-options草案键。详见[页面与接口复现](../../F2/CsvWiringPatchQuickstart.md)。

## 冻结源码定向终态

同一源码十文件 **269个唯一病例**：

| 后端 | PASS | SKIP | FAIL / ERROR | 时间 |
| --- | ---: | ---: | ---: | ---: |
| SQLite | 266 | 3：PG角色子进程专用 | 0 / 0 | 234.941秒 |
| 自有 PostgreSQL17.9 | 268 | 1：SQLite历史NUL专用 | 0 / 0 | 358.040秒 |

46个接线病例和24个原P2防护病例每后端全PASS。新接线覆盖八种允许组合、独立CSV验算amount=30/quantity=15、schema/语义端口拒绝、同键异接线/旧指纹确认、实际父回执与input_sources、来源/授权变化、冷恢复不重执行、锁与PROJECT不确定性阻断、UNKNOWN操作禁止普通恢复/通用核对、真实wall deadline完整回滚、count=true/1.0拒绝。

每后端实际loopbackHTTP及产品JS/DOM：DAG35项（原24原样保留）、列补丁20项、CSV图29项、Report图29项。加载源码SHA256逐项吻合，proof与expected总和见 `sqlite/`、`pg/`。原Python测试文件不改，DAG DOM只追加断言，修复proof测试字节一致、关键防护函数AST一致，锁/脚本/workflow保持；见 `preservation.json`。Ruff src/scripts/tests PASS，mypy50源码文件PASS；只有既有Starlette TestClient弃用警告。Windows900 / Edge240 / Node150标准保留，原生Windows/Edge **NOT_RUN**，旧720/1591不作为本改动证明。

`summary.json`列出终态、跳过原因和阶段区别；双后端provenance保存冻结SHA、全部src/tests前后哈希、source_unchanged=true、returncode=0、LIVE=0、mock。完整范围见 `runner.py`。

## 历史失败与隔离

原0ec暂停阶段37项36PASS1FAIL为httpx surrogate编码失败，后改为escaped JSON真正到接口。本轮67项阶段全PASS；新旧键测试首次1FAIL2PASS为cached:false元数据比较错误，修正后3PASS。

首次PG269项67PASS202连接ERROR、0断言FAIL：作者runner误把pytest basetemp与自有PGsocket父目录重名，pytest清空目录导致socket消失。完整失败日志/哈希及根因独立保存，未冒作源码失败或通过。自然结束后正常停止自有服务器，确认原匿名卷消失，再用独立私有 `/tmp/sim2act-wiring-db` socket与 `/tmp/sim2act-wiring-final-tests-pg` basetemp，在相同645e源码重跑最终十文件。SQLite已通过不重复跑。

所有阶段/最终原始日志与JUnit无损gzip保存，解压后字节数/sha256在 `raw-log-preservation.json`；不删除失败。两轮服务器均network=none、无端口发布、自有合成身份；最终test schema/role均0。自有容器、镜像、匿名卷及11个临时路径已核清理；`.venv`开发环境保留，见cleanup和pg-cleanup-before。

## 用户复现

按原锁定开发依赖与Node/jsdom准备环境，仅用自己的隔离测试目录/数据库：

```bash
git fetch origin dev/csv-wiring-patch-20261008
git switch --no-track -c review/csv-wiring FETCH_HEAD
LIVE=0 SIM2ACT_MODEL_MODE=mock SIM2ACT_LIVE_ENABLED=false .venv/bin/python -m pytest -q tests/test_csv_wiring.py tests/test_csv_dag_proof_guards.py --basetemp=/tmp/your-owned-wiring-tests
```

复现十文件范围按runner中的suite，设置NODE_PATH指向自己的jsdom30.1.2安装目录。PG显式设置SIM2ACT_TEST_DATABASE_URL到自己的隔离库；现有fixture创建/删除test_* schema与受限test_app_* role，不可传生产或用户数据数据库。数据库socket目录必须与pytest basetemp完全分开。证据runner记录作者自有路径，复现时复制并调整输出/临时/NODE_PATH，不覆盖冻结证据。

[作者范围复核](author-review.md)不是独立签收。本候选等待原第二reviewer核对，semantic UNKNOWN、owner PENDING、publishable=false、LIVE=0，真实gold、完整P-B、人工签收及正式发布未完成；无新CI、dev/main合并、强推、凭据配置、安全权限扩大、部署或真实模型调用。
