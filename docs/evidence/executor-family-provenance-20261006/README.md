# executor 来源家族边界：隔离复现与最小修复

基线为已发布 `96a6ae034993db282a6569d2bfb3c08f4e411885`；本轮没有 push、CI、LIVE 或外部上传，模型调用 0。

## 实际失败基线

`baseline-reproduction.log` 与 `independent-baseline-reproduction.log` 分别保存主开发和独立复跑的 **2 FAIL**。两个本地合成 SQL 损坏 fixture 均先为既有 runtime 建立合法 MD read 权限，再撤销原来源 CSV；未篡改 app GET 403。仅协调改写 app_drafts.candidate 和 fingerprint 为 initial bounded_agent，独立 goal_candidate_requests / preview_extractions 原记录不变，结果 GET 200，真实离线 Replay 两轮、批准、Release、Instance 和 QUEUED Run 创建成功。没有执行该排队 Run，不据此声称公开接口越权、生产攻击或 Worker 成功。精确来源/测试 hash 和实测状态在 baseline.json。

调用链是 inspect_draft / prepare_release → load_draft → validate_frozen_candidate；此前 bounded_agent 在独立 goal/preview 标记检查前提前 return，validate_agent_origin 只读 task_extractions，导致原来源链被跳过。

## 修复范围

仅在 apps.py 的 validate_frozen_candidate 中，指纹检查后、compile_preview 和 executor 分支前加入 validate_source_family。查询三张既有来源表全部匹配行，拒绝同家族重复、跨家族冲突、owner 不一致、未知/损坏 task snapshot、候选顶层来源字段不一致及 executor family 替换。task 表只支持明确 agent_source.v1 或既有 proof.kind=completed_fixed_csv_task 且无外层 kind 的记录。无独立来源标记的 initial app 不得宣称 task_run / source_run_ref 或生成/提取来源字段。

原 goal / preview / legacy task / agent 的材料权限、snapshot、版本及接受请求 fingerprint 等详细验证仍运行。没有新增 Grant、Principal、表、迁移、API、工具或模型能力；不改变安全策略或已有角色。冻结 Release 回读与 Worker 经 validate_frozen_candidate 同样受此检查。信任边界仍假定独立来源记录可靠；未宣称能抵抗同时改写全部数据库信任锚点。

## 验证与失败保留

23 个新增负例检查双向 executor 替换、两个原失败 fixture、legacy CSV task 转 initial agent、保留或删除 agent provenance、来源重复/冲突/owner、虚构来源、未知 task kind/坏 snapshot 及坏 actions/executor。拒绝为 VERSION_CONFLICT / HTTP 409，批准前 Replay 0 请求，业务/授权表计数不变。fixed-focused-sqlite.log 已实测 23 PASS。fixture-lock-failure.log 保留扩展测试曾因 HTTP 写事务嵌套导致的 1 FAIL；修复仅将 fixture HTTP 写移至事务外。

完整数据库回归与独立终态以最终 result.json 和 independent-review.md 为准；不以先前 CI 或此轮中间结果代替本轮实测。原 V5、AT02、Win11/F1 签收、完整 P-B 及 semantic UNKNOWN 边界不提升。本轮无 UI 改动，未执行新的 Windows/浏览器验收。
