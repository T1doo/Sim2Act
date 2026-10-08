# Run 分派所有权前置修复：候选待复审

本轮接父线程独审 P2：旧候选 `0325fc2aa3429ed2f9df42e0b241390b182aabf8`（执行源码 `041cf8ec5fbfeffde6ee3103bba8a4188eb08861`）的三个公共入口在拒绝他人之前读取其 context/接受事件。该独审结论由父线程报告；旧候选、历史断言及证据完整保留。

开发分支 `dev/run-dispatch-owner-fix-20261008`，冻结执行源码 **`6181bf755335a811ab9fbbfa881a4b5ca5e3fda9`**。产品改动仅 `src/sim2act/db.py` 增加17行：Store.inspect、command、reconcile_operation 先按 Run ID＋principal 只读 project_id，再验证当前项目所有权；之后走原 CSV DAG→protocol→AppRun→ordinary 分派和原 handler 校验。不替代当前来源/权限/版本/恢复校验，不增加事务锁或权限。原候选未合入 dev。后续证据提交不改产品、schema、测试和脚本字节。

## 冻结验证

同一105例范围，见 [scope.json](../evidence/run-dispatch-owner-fix-20261008/scope.json)。SQLite **101 PASS /4 SKIP/0 FAIL**（四项隔离PG角色），PG **105 PASS /0 SKIP/0 FAIL**。新增55例覆盖：真实已接受四类作业，三个Store/HTTP入口foreign拒绝、主体匹配但项目owner已变、missing ID，全表快照零写，授权inspect/command及旧版本/重复拒绝，generic只读工具未知结果可信核对与重复拒绝，typed marker不误降级，PG最低CRUD角色。协议context类型变化仍由协议持久标记正确分派，不伪称其既有合同会拒绝该变化。

每后端42份拒绝SQL轨迹可复核（只记录SQL，不记录参数），均无 context/result/相关账本SELECT，也无INSERT/UPDATE/DELETE。PG角色另有三个入口零读取/零写测试断言。原foundation、protocol恢复、AppRun控制/过期租约、DAG未知操作、条件执行冷重开及generic恢复做定向回归。Ruff全src/scripts/tests及mypy50源码文件通过。运行前后hash一致；旧tests/scripts/workflows及锁逐文件与0325核对未改，900/240/150不调整。

[证据目录](../evidence/run-dispatch-owner-fix-20261008/)保存collection清单、JUnit、原始日志、source/test字节hash、静态检查及SQL轨迹。`repro.log/xml`保留修复前三个实际失败；`first`/`extra`保留编写新测试期间两项错误假设的失败：DAG cancel既有返回CANCELLED；protocol持久标记保留原分派。只改新断言适配真实合同，未改原断言或扩大产品范围。上述阶段不作为冻结通过证明。

未重跑先前独审已通过的全部条件算术/页面DOM/并发子进程案例，也未重跑旧1591/756全套。旧通过不得跨源码自动升格；本轮仅证明此105例影响范围，Windows900 / Edge240 / Node150标准保留而原生执行 **NOT_RUN**。LIVE=0，真实模型/部署/新CI均未运行。候选待独立复审，不是人工签收或业务验收；P2是否关闭交原独审方判断。

## 复现

获取上述开发分支；按原依赖锁使用Python3.12。隔离临时路径须自有。最小权限分派回归：

```bash
LIVE=0 SIM2ACT_LIVE_ENABLED=false .venv/bin/python -m pytest -q tests/test_run_dispatch_owner.py --basetemp=/tmp/sim2act-owner-review-sqlite
```

SQLite预期51 PASS/4 SKIP。双后端完整105例可读取证据中的scope.json并传给pytest：

```bash
LIVE=0 SIM2ACT_LIVE_ENABLED=false .venv/bin/python - <<'PY'
import json, subprocess, sys
scope=json.load(open('docs/evidence/run-dispatch-owner-fix-20261008/scope.json'))
sys.exit(subprocess.call([sys.executable,'-m','pytest','-q',*scope,'--basetemp=/tmp/sim2act-owner-review-full']))
PY
```

PG使用同命令并提供 `SIM2ACT_TEST_DATABASE_URL` 指向本人隔离数据库；fixture创建/删除自有schema和临时CRUD角色，勿指向业务数据库。PG预期105 PASS。冻结精确执行可检出6181bf7后使用run_frozen.py，基准0325仍有严格字节核对。新候选HEAD的产品/测试字节与6181bf7一致，证据commit仅补文档。

## 清理

自有 `--network none` PG容器（PGDATA在容器临时文件系统，无端口）已正常停止自动删除；自有镜像普通删除，无force。六个自有/tmp测试/数据库目录已删除，容器/卷/镜像均复核无残留。fixture teardown无错误。清理前目录查询脚本误用缺少SQLAlchemy的系统Python，随后容器删除，故**不声称额外完成数据库目录零schema/角色查询**；容器及其临时数据库实际移除有证据，见cleanup.json。没有清理其它资源或配置凭据。
