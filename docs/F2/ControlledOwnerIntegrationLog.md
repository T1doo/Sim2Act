# 受控条件分支与所有权修复：开发分支整合

2026-10-08按父线程授权，把受控条件分支及其所有权P2修复快进整合到 `dev/f1-foundation`。旧dev `5bbc462b4ce0027fe9349e4b42064fe75f1470f5` →冻结执行 **`aea68d2e0022bcaa10b6535cfdbd509ae93516c7`**；产品/schema/tests/scripts/workflows与已独审产品源码 **`6181bf755335a811ab9fbbfa881a4b5ca5e3fda9`** byte-identical，无合并冲突或产品逻辑改动。后续归档提交只补文档证据。原候选 `0325fc2aa3429ed2f9df42e0b241390b182aabf8`、`aea68d2e0022bcaa10b6535cfdbd509ae93516c7` 及其分支仍完整保留。

## 独审范围与状态

父线程报告所有权P2 **限定闭合**：source6181bf7，SQLite和PG17.9各28PASS/0FAIL/0SKIP；旧三个权限回归全FAIL，新全PASS；各39拒绝轨迹仅必要身份/所有权读取、无提前账本。合法分派、项目转移、撤权、重复控制与冷恢复抽查通过。最低权限角色、原生产品页面、真实并发所有权转移**未独审覆盖**。此处归档父线程报告，不冒充作者重新执行或取得审查方原始文件，见[parent-independent-review.json](../evidence/controlled-owner-integration-20261008/parent-independent-review.json)。

此前父线程报告受控条件的独立13.875算术、跳过、最终租约/预算、并发子进程恢复与实际页面子项通过；旧51例每端48P3F原失败保留，不能改写成51例全部重新通过。独审结论与作者756/757、105历史测试范围分开；本轮整合不签收Windows/整体F1/F2/通用P-B/语义gold/owner/正式发布。

所有权修复作者清理证据限制保留：额外零schema/角色目录查询误用缺少SQLAlchemy的系统Python，未完成就正常删除自有临时容器。不得补称之前查询通过；实际容器/临时数据库/镜像/目录删除已核实。本轮另用正确venv在**新整合容器**成功查询零fixture schema/角色/public表，只证明本轮清理，不追溯填旧缺口。

## 本轮必要整合验证

精确执行AEA的40唯一案例，SQLite和PG17.9各 **40PASS/0FAIL/0SKIP**，产品/标准测试运行前后hash一致。旧标准tests/scripts/workflows/锁逐文件与旧dev5bbc核对保持。范围包括三种真实旧源码升级（5a5543c、1b65e94、原dev5bbc），原受控分支执行/冷重开、撤权/来源/输入/跳过篡改、错误精确确认、跨主体，四类真实作业HTTP拒绝及当前项目owner门、合法inspect/command/reconcile与重复控制、generic可信核对。

三个真实旧源码子进程产生运行和账本，再由整合源码读取：旧图/计划/执行证明和旧确认拒绝、零失败写入；新图显示INVALIDATED历史，旧Run控制元数据NOT_VALIDATED，重新派生并精确确认才运行，新quantity=15、旧preview amount=30。历史JSON存储字节保留，不迁移、不覆盖、不重签。各后端24份新的拒绝SQL轨迹，零关联账本读取/零写入。[证据](../evidence/controlled-owner-integration-20261008/)含三份upgrade-proof/端、collection/JUnit/log/字节hash。

首次SQLite40PASS，但证据runner漏计docs中的第40个案例，汇总assert失败；原结果与runner/driver保留first-*，计数修正、证据driver导入格式修正后重跑40例得到冻结结果。产品/原断言不改。Ruff src/scripts/tests和证据driver、mypy50源码、diff通过；原900/240/150保持，原生NOT_RUN，不机械重跑757。LIVE=0、mock/NoModel，无真实模型、部署、新权限、新CI。

## 使用与复核

正常获取 `dev/f1-foundation`；按[现有页面指南](ControlledBranchesQuickstart.md)在已有CSV应用保存图锚/条件草案、核对精确指纹、显式确认输入，再运行。源码升级使旧证明失效时，保留历史，只能重新派生图/新计划、使用新确认与新Run；不得把旧确认移植到新版本。无必需报告仍PARTIAL，candidate/owner/semantic标签不提升。

基础定向回归可用原锁定Python3.12依赖，在自有临时路径运行：

```bash
LIVE=0 SIM2ACT_LIVE_ENABLED=false .venv/bin/python -m pytest -q tests/test_run_dispatch_owner.py tests/test_controlled_branches.py::test_same_exact_plan_distinct_inputs_actual_paths_and_cold_key_recovery --basetemp=/tmp/sim2act-owned-review
```

完整40例范围见scope.json；其中升级测试要求自有git archive，按证据preintegration.json列出的三个SHA分别准备src/tests，并设置SIM2ACT_UPGRADE_OLD_ARCHIVE、SIM2ACT_UPGRADE_CORE_ARCHIVE、SIM2ACT_UPGRADE_DEV_ARCHIVE，PYTHONPATH=src:tests；使用run_frozen.py分别传sqlite/pg及自有`/tmp/sim2act-controlled-owner-integration-final-*`路径。PG数据库必须本人隔离资源，fixture会建/删测试schema。不得使用业务数据库。

四个自有tmp目录、隔离network-none无端口容器及临时PGDATA、自有镜像已正常清理，不force；见cleanup.json。推送前再次核祖先和远端：旧dev和两候选无并行变化才普通push dev；不改main、不强推、不部署。具体远端HEAD在交付回复中提供。
