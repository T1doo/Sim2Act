# 七槽自然离线预算门：独立执行及有限独审

冻结 `4aaea50d4ea40b7d2425f3c1561bc99b5e3def53`，分支 `dev/natural-offline-budget-gate-20261016`。开跑前及结束后 HEAD 相同、工作区干净；产品和新测试文件与该commit逐字相同。本独审只写 `/tmp`。

**结论：本次最小复用切片在所测范围通过，未发现剩余阻断。独立新模块实际 17 PASS / 0 FAIL / 0 SKIP，RC0，24.19 秒。作者相同17项26.65秒另批通过，本独立复跑不新增独立用例数，不合计为34项。**

## 实际命令及原件

`env -u SIM2ACT_TEST_DATABASE_URL /workspace/sim2act-venv/bin/python -m pytest -q tests/test_natural_budget_projection.py --basetemp=/tmp/f2-natural-budget-4aa-independent/data --junitxml=/tmp/f2-natural-budget-4aa-independent/junit.xml`

- `junit.xml`：SHA256 `d8eaede51f615d12d977109b4c6aea27f570612b50439d8b8ced2116e7c17076`，17 tests、failures/errors/skipped均0、24.195秒。
- `pytest.log`：SHA256 `93323dbb9a7b1086d2e6d61d94ef712f592208ab4e72d5a455ad275a69dc75eb`，实际17 passed；1条既有Starlette/httpx弃用warning，无测试失败。
- `pytest.rc`：实际0。
- `data/`：17份唯一JSON回执（排除pytest的current symlink重复），保留所有合成SQLite夹具；没有重放既有业务数据库。
- `independent-proof.json`：SHA256 `3c21daf0f190b5944ff97dc5840afdd3b9928f397f17b353be5cbee6f556c202`，包含各原件hash、完整分类结果及源码桥。

产品 `natural_trial_budget.py` SHA256 `433c954e6cc3087f6c04d56ad7c4938f5d3c78aabe90b55e6928ec647a405b38`；新测试 SHA256 `3800171c880ec9d4228329ca8c024e8e38c582265f9ad7e975c37bea25dfd7ef`。AST比对基线463确认全部旧class/function不变，原_public仅增加budget_projection返回项，新增_projection纯读取；原准入/预留/结算/权限/版本/lease/fee/软件资格门没有放松。

## 原始证明所支持的行为

- 4种pending/unknown/rejected/overflow：请求槽始终持有1、token envelope持有1124；未知usage的total_tokens保持None（已收到的部分prompt=5仍保留）。已知未接受8 tokens及overflow2025 tokens均入证据，不退款或抹去成本。money保持paid_cap0、actual_paid/currency=None、UNKNOWN、NOT_LIVE_VERIFIED、live_allowed=false。冷Store read及duplicate均保持accounting rows原字节，duplicate不重新admit或发送。
- 2个真实SQLite Store竞争同一trial最后阶段额度：requests从2→3，仅1成功、另1 BUDGET_EXHAUSTED；tokens从1→2，总envelope54816，另1 BUDGET_EXHAUSTED，未越64000阶段限额。这些是controlled fixture clock + admitted primitive stub的caller-owned transaction竞争，不是自然执行或provider调度证明。
- 1个同trial三Run primitive：generate/source/cold各1，3个不同Run、累计held_requests3、held_envelope3372、known_tokens24；不因换Run重置预算。
- 2个PA/PB真实冻结合同、真实gate.admit配SyntheticOnlyFeeAuthority及ASGI预算GET：200、total_tokens仍None、重复原key只读，accounting rows不变；无_qualified patch，不尝试生产dispatch。
- 8个PA/PB×缺批准/Goal漂移/过期/撤销：全部拒绝且accounting rows不变。Goal漂移真实PUT保存到v2，仍使用原v1批准合同；不是伪造传入scope代替持久状态漂移。

## 界限

本切片复用现有固定三阶段七槽合同和账本，仅补只读总预算/成本可见性，不是任意普通PA/PB逐次材料的可滚动批准，不新增可收费余额或免费法律资格。所有held槽不退还；未预留容量是数学差额，原HALTED/RECONCILING与dispatch_authorized=false仍约束发送。实际货币费用仍未知，不能由mock或token换算为真实0费用。

本模块不运行Worker自然处理、完整七槽等待、模型HTTP、旧恢复/锁矩阵。fixture中真实claim只用于受控Run/fence/lease/准入边界，不是完整业务执行。原Worker→pa_trial_dispatch.reserved→budget._reserve同事务链已静读；旧test_actual_admission_generate_worker_reservation_combination是先Worker.reserve再budget.reserve的**两个事务**，即使root另跑通过也应分列为顺序组合，不称本次同事务Worker全链实测。

root另跑17个显式旧短节点不在本独立17项内，本报告不代签其尚未核对的原件。LIVE保持拒绝/额度0，pins/guards不变；Windows、PG、真实模型/收费资格/语义、远端CI、部署未执行。旧F9/自然恢复分支、首包异常原因和旧满盘独审缺口不因本次改变。
