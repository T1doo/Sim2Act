# 受控条件分支候选复现

仅离线工程，沿用现有配置与已授权 CSV 应用，不新增迁移、Grant 或身份。LIVE=0/mock；正式发布关闭。候选 dev/controlled-branches-20261008，待独审，不合入已验 dev。

1. 打开已有 CSV 应用，使用原“保存派生图锚”。在原三节点运行区选择求和列。
2. “可选受控条件”选节点 report、op=eq、引用本次输入 include_report、JSON值 true，然后保存草案。核对保存的 when、来源、版本和 plan_fingerprint，确认框不会自动勾选。
3. 本次 include_report 选 false，核对并勾选精确确认，再运行。读回实际 preview/aggregate 回执及 report SKIPPED/CONDITION_FALSE；终态 PARTIAL、output=null、output_status=SKIPPED，页面明确未产出报告。
4. 保持同一已保存计划，将本次输入改 true（会清除确认），重新明确确认后运行。新的 Run 实际执行 report，核验后 SUCCEEDED/PRODUCED。两个 Run 共享 plan_fingerprint，输入各自冻结；不改变旧 Run。
5. 节点改 aggregate 时，false 会使 aggregate 跳过，report 因 DEPENDENCY_SKIPPED 跳过，不读取不存在输出。exists 不带比较值：输入缺失时 false，但显式 false 仍是“存在”。eq/in 遇缺失输入则 INVALID_INPUT/FAILED，不自动补值。in 比较值必须是有界 JSON 数组，例如 report 读 aggregate:count、[2]；只能读该节点已声明前驱。
6. 刷新后重连原身份，打开应用→读取已有计划与运行→核对运行回执；来源、授权与版本会重新验证。若接受响应丢失，页面冻结原输入与原键；使用“原键恢复未知接受回执”。整页刷新丢失内存原键时先读持久历史，不自动重发。

条件 false 不是错误，也不制造输出；下游因跳过而没有必需报告时 PARTIAL，不是业务/人工验收。semantic UNKNOWN、owner PENDING、publishable=false 保持。撤权、来源/源码版本变化或证明篡改时旧证明拒绝继续，只能使用原停止控制信息；不修改旧记录或无缝升级。

API 在现有 POST /api/projects/{pid}/apps/{aid}/csv-dag 的闭合 body 中可选加入：

```json
{"branch_patch":[{"step_id":"report","when":{"op":"eq","source":{"source":"input","field":"include_report"},"value":true}}]}
```

其余原 expected_candidate_fingerprint、expected_graph_fingerprint、column、request_key 保留。在原 /{plan_key}/runs 精确确认请求中加入 branch_inputs={"include_report":false} 或 true；每次显式新运行用新 request_key，同键恢复必须同输入与指纹。省略 branch_patch 保留原请求/定义/回执结构，旧无条件计划不接受 branch_inputs。

开发者用锁定依赖、自有 jsdom30.1.2 和隔离数据库，可运行新专项：

```bash
NODE_PATH='/your-owned-jsdom/node_modules' LIVE=0 SIM2ACT_MODEL_MODE=mock SIM2ACT_LIVE_ENABLED=false .venv/bin/python -m pytest -q tests/test_controlled_branches.py tests/test_controlled_branches_ui.py --basetemp=/tmp/your-owned-branches
```

SQLite 中两项 PG CRUD 角色测试明确跳过；PG 只给自己的 SIM2ACT_TEST_DATABASE_URL（绝不传用户/生产库），fixture 隔离并删除 test_* schema/role。socket路径与pytest basetemp分开。Node/JSDOM仅工程证明，产品无Node新增依赖；Win11/Edge原生 NOT_RUN。完整实际范围与来源见 docs/evidence/controlled-branches-20261008，不复用旧全量作为新改动证明。
