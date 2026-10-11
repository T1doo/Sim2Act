当前候选有限范围独立审查：LIMITED PASS。实际独立结果为 **59 PASS / 0 FAIL / 0 SKIP**，并有下述明确 NOT RUN。基线 HEAD `2b53572ded47f83d51898356dae0e99a97a61bc9`；被审候选为该 HEAD 上未提交的四个生产 Python 文件修改，root 唯一产品写入者。独审没有编辑仓库产品、测试、文档，没有推送或部署。

原 `2b53572` 的“未读取旧 Run 私有内容”结论已撤回。原 SQL trace 0 基位置 1091、1097 是无 WHERE 的 `SELECT runs.id,runs.context,runs.result FROM runs`，1092、1098 是全表冻结合同读取。原探针只匹配旧 Run ID 是否出现在参数，漏检此类扫描，是独审方法错误。原报告/脚本/trace/结果/bridge 保持原字节，不能用旧 PASS 或字节桥证明该私有读取边界。尚未证明用户数据泄露或旧结果复用。

| 当前独立专项 | PASS | 实际验证 |
|---|---:|---|
| SQLite 读屏障校准和普通 claim | 16 | 15 种访问负例实际执行并拒绝；精确当前 Run 可领取，成功旧历史未读私有列 |
| 全标记与损坏 JSON | 39 | 五标记全部 31 个非空组合阻止普通恢复；禁止无 scope；两个 Run 重复键、四个 contract 重复键；11 个类型/坏指纹输入作为一个复合检查 |
| 实际共享协议池候选 | 1 | 真实 Attempt Run ID、NULL orphan；保护候选外历史；Run cursor 只返回 ID |
| 实际无原内容新资料 Worker / cold typed / 原行保留 | 3 | 新 CSV 独立 Fraction 复算5.75；冷读新输入 net5.750、units18；旧 SQLite 全列原串值逐行保持 |
| 合计 | 59 | 不是 pytest 59 个病例；每个检查名称和事实列于 result.json |

屏障校准实际覆盖：无 WHERE、IN、join、quoted alias、subquery、aggregate、WHERE predicate、CTE、显式 main、伪装同名 view CTE、leading comment CTE、Operation.receipt、OperationIntent.request、contract.snapshot、resource.content/hash。普通形状由 SQLite 按旧行/列求值的 UDF 拒绝；显式 main 和保留 view 名攻击由 SQLite authorizer/测试入口拒绝。没有靠旧 Run 是否位于参数或删除历史来判通过。屏障是 root 提供的测试 fault injection 工具，独审以独立 SQL 访问形状校准并以真实 worker 执行；它不是生产授权层。

真实 worker 路径保护 5 个旧 Run 和 3 个旧资源，期间记录 47862 条实际 SQL、5016 次允许当前载荷 cell 求值，保护旧 cell 触发 **0**。新目标三步 read→sum→report 完成，独立十进制有理数 oracle 得5.75，3行。随后独立版本/实例创建，另一 Store/HTTP TestClient 冷会话执行 net 和 units 两个新 Run，typed data_version=2，结果5.750与18。旧 CSV、旧 Run.context/result/goal/resource_refs/error、contract.snapshot、Operation.receipt、Intent.request、旧 typed 与 instance 记录全部仍存在；actual-worker-history-before/after.json 对保存前原始 SQLite 串值逐行核一致，并记录本轮新增行。

代码终核：`db.py:918` 到期调度只先读元数据，`:971` 锁定唯一排队 ID 后 `:985` 读取它自己的载荷；`protocol_recovery.py:103` 先选明确到期 ID，再按项目/Run 锁重验当前 status/lease；`protocol_pool.py:20` 从实际非 NULL Attempt Run IDs 提供 scope；`protocol_jobs.py:261` 要求唯一显式 scope、256 ID 分批无 silent cap，Run 查询仅返回 ID。SQLite 类型门和 duplicate Run namespace 保守停止；contract 只读 namespace 命中的候选完整 snapshot 后重核 Python 解码后真实 constraints 数组及指纹。所有生产 `protocol_run_ids` 调用已核有 scope，未发现新的本范围阻断缺陷。

必要范围限制：真实 pool 候选的命名空间谓词允许数据库检查其 JSON 标记；实际标记合同候选允许读取完整 snapshot 核指纹。本报告没有声称“所有旧 JSON 零底层求值”，也没有证明任意其他产品路径或全部数据库列零旧资料读取。此次实际 CSV 路径的屏障覆盖如上逐项字段。

冻结：401 个 src/tests/scripts 非 pyc 文件始末完全一致，其中82个 src 文件包括 editable 安装生成的5个 ignored egg-info 文件。四个生产修改实际 SHA256：

- `src/sim2act/db.py`: `afb404ea797a1bf2c4f834949b138db0510628fe1e6efa88d9170e554da15523`
- `src/sim2act/protocol_jobs.py`: `a197a7c8f5aa2325564c5e5e7bca249f939bcd5e90cb1af6518f8c695c301bb8`
- `src/sim2act/protocol_pool.py`: `b3e5ceb05a4730d9a4554c16b4d2235a51d3f088bf0e5d3bed96ccb49b86e1d2`
- `src/sim2act/protocol_recovery.py`: `d6797143a25efefee4b4cf20d6a8d8f7524a345397a9ecdc290be916e9b55f77`

完整 map 见 product-source-sha256-final.json 与 freeze-before/frozen-after.json。既有2b源代码基线 map 见 baseline-source-sha256.json。独立启动第一轮 first.log 在 flat freeze map 被误当作 nested files 时 KeyError，产品检查执行0，保留旧脚本及分类；夹具修正后本轮从新 fixture 完成，未累计第一轮。parent 正规 editable 安装先遇默认 cache EROFS，后用允许 /tmp cache 成功；原产品/测试字节不变。这不是工具授权拒绝或权限扩张。

作者证据与本59检查分开：原红轮实际私有读取失败、edge 边界失败、reserve helper 错参失败、安装前置失败和中断日志均在仓库 docs/evidence/run-private-read-scope-20261011 保留。作者70专项和当前完整关联回归不计入独立数。审查时作者1698集合分片仍在跑；expanded material UI cold新输入处 DOM wait 的单例失败仍未归因，本独审没有运行或豁免该 UI。整包绿色验收需作者完成关联/串行 UI 并解释全部失败；本有限私有读取修复签收不能替代整包回归。

NOT RUN：PG；Windows；原生浏览器和 socket/device 路径；旧源码升级；真实/付费模型；完整 P-A/P-B/AT10；人工语义/owner 验收；远端 CI；部署。独审只 SQLite 实际 worker、进程内 HTTP；没有重试已知拒绝浏览器路径、没有网络权限升级。

复现：在 /workspace/Sim2Act，`PYTHONPATH=tests:src .venv/bin/python /tmp/run-private-read-independent-20261011/probe.py`。当前结果 second.log/result.json。保护访问细节 calibration-*.json、ordinary-claim.json、pool-scope.json、actual-worker-barrier.json；完整新 Run/Release/冷实例 actual-worker-proof.json。原误报撤回 RETRACTION_AND_SCOPE.md、prior-byte-preservation.json 与 prior-byte-preservation-after.json。
