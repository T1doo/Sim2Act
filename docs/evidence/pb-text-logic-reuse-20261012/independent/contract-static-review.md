# F2-T03 有限文本无旧内容逻辑复用：合同及基线只读审查

日期：2026-10-12。审查者：`/root/text_logic_review`。仓库：`/workspace/Sim2Act`。基线分支：`dev/pb-text-logic-reuse-20261012`，HEAD：`e2b856bb453fc74452583fa10843148758e2d9b9`。

结论：新合同是可实现的 F2-T03/P-B/AT-10 有限工程子项；当前基线尚未支持此合同。这里只作静态可实现性判断，不签执行 PASS，不签完整 P-B/AT-10、人工语义或发布。源码与测试冻结后才可进行普通独立验证。

本阶段没有运行测试、模型、HTTP 服务、浏览器或 Worker，没有编辑产品源码、作者测试或共享 evidence。所有审查输出仅写到本次独立 `/tmp/pb-text-logic-review-20261012`。此前精确候选安装竞态对照已由用户取消，永久 `NOT_VERIFIED`；本审查不执行、实现、变通或重试该目标，也不以本轮权限/冷 Worker 校验关闭它。

## 已读依据与现有支持

完整读取新合同 `docs/F2/PBTextLogicReuse20261012.md`；对照原 V5 `docs/sources/V5/分阶段开发计划.md:95`（F2-T03）、`:111`（新资料冷运行）、`:340`（AT-10）及 `docs/sources/V5/平台产品设计.md:117`（P-B）。读取相关文本执行、来源提取、CSV 独立逻辑、生命周期和实际队列/最终提交实现。

- `registered_run_extraction.py:45` 的 `verified_source` 已从真实持久 `SUCCEEDED` 初始文本 AppRun/Release 核验当前来源授权、生成记录、typed 结果、操作 intent/receipt 与独立字面检查；可在新逻辑授权**签发前**使用。返回 CSV proof 的分支必须由新入口明确拒绝，不能作为通用兜底。
- `text_apps.py:16`、`:38`、`:102` 已有闭集注册算子、固定输入输出 Schema、单节点接线、4096 UTF-8 bytes/64 行/80 字 term/16 命中行和独立字面 oracle。当前 compile 候选仍仅认识 goal/goal_application/旧 task_proof；新家族需要独立闭集分支。
- `app_jobs.py:55`、`:241`、`:437`、`:589` 已有标准内部 Release/Instance/持久 Worker 链、当前目标授权/字节检查、typed 账本原子提交及 NoModel 字面执行。其调用到新候选验证时可以传递独立逻辑检查。
- `lifecycle.py:176`、`:256`、`:323`、`:422` 可继续负责新应用的内部版本、实例与回读；新 Release 仅含新候选与新材料，不能混入原 Release snapshot。
- `db.py:976` 的普通调度已先用 Run 元数据筛选，再仅加载实际被选 Run 的私有字段；这有利于整段 SQL 屏障，但不等于新链已经通过屏障。

## 必须解决的实现风险

1. **CSV 权限对象不是本合同的无旧内容实现。** `csv_logic_reuse.py:99` 的 `audit` 每次读取原 `internal_releases.snapshot` 和原 `internal_approvals.payload`；`:142` 的 `load` 每次调用它，并从原 snapshot 取 limits、版本及 canonical 参数。新逻辑 load 必须只取签发时冻结的独立对象、私有最小承诺与双 seal，不再调用旧 audit/recipe/read_release/verified_source。

2. **旧 P-B 候选仍携带原 goal 并依赖旧来源。** `registered_run_extraction.py:395` 的 `_candidate` 对文本 deepcopy 原候选、原 goal/goal_ref；`:610` 的 `validate_registered_candidate` 每次重新 `verified_source`。新候选必须从固定 canonical 结构生成，仅带新 IDs、新目标绑定、独立 logic ID 与本次精确请求；标准 goal 文本固定，不复制旧名称、步骤标签、输入、引用、答案或生成轨迹。

3. **派发必须绑定可信独立 marker。** `apps.py:254` 的 `validate_source_family` 当前闭集 task kind 不包含新文本逻辑家族；`text_apps.py:124` 的 `verify_origin` 对任何 task_proof 调用旧验证。新 task marker kind、candidate marker、单一注册 executor 和 fresh runtime 应相互精确绑定。删掉/改写 candidate marker、task marker 或任一 seal，甚至协调重算 candidate hash，都应拒绝，不能回退 goal/CSV/agent 分支。

4. **另一份材料的判定必须在无需旧资源读取时成立。** 独立审计只有原 app/instance/Run/Release opaque ID 与证明/指纹承诺，单凭原 app ID 不能排除“不同初始 app 指向同一旧 resource”。建议在合同明确允许私有 source-binding 不可逆承诺：签发时承诺原 resource identity（必要时明确不同内容的语义），绑定时从目标计算比较；不保留原 resource ID/hash，不重开原 app 或材料。相同字节但不同 resource 是否算“另一份”须由合同明确。直接沿用旧 `_target` 的原 hash 比较不满足本合同。

5. **fresh runtime 的权限闭集与有效期。** 创建一个无 token_hash 的新 `appruntime_*`，只写一条新目标 `resource.read` Grant，并在同项目锁事务提交全部候选、task marker、绑定双 seal、principal 和 Grant。不得调用 `Store.add_grants`（同时给 user/runtime 增权）或复制目标 app 全 Grant。权限有效期可按独立 logic expiry、绑定时有效 user/目标 app read 授权终点取最小；多个有效 Grant 应与 Store 的 any-active 语义一致。后续执行按当前 user + fresh runtime 交集判断，目标初始 app runtime 不应无意变成永久第三重运行身份。

6. **复用现有容量函数会违约。** `column_patches.py:150` 的 `require_capacity` 是 50/同 app/kind，不是新合同的 64/project 与 64/logic。需要新项目/逻辑粒度计数，历史/CLOSED 计入上限，满额在新写前拒绝。同 key 回读不计新对象，不删旧对象腾额度。

7. **最终提交时间边界需要覆盖。** 现 `app_jobs.commit_result` 先做授权/计划/字节校验，再写 typed 数据及成功状态；单节点计算在事务外。新家族须确保 dispatch、计算边界和最终提交时当前 logic、limits、user/runtime Grant、目标 bytes/hash 被核验。合同写明“最终写前后重核”，应在 typed 写后、事务 commit 前再核独立 logic/expiry/current budget；失败必须整事务回滚，不能留下 SUCCEEDED/typed 行。撤销走同项目锁；到期时间必须真实有限且不允许 bool/NaN/Infinity 被接受。

8. **未知回复恢复不能抄旧 CSV UI POST 重试。** `csv-logic.js:111` 仍提示未知接受原 key 重试；新合同仅允许原 key GET 查账，不自动 POST 重放。新页面必须保存精确 action/key/body/identity/project，核回执的原 key、request fingerprint、新 app ID 与 candidate hash，再安装/打开。正常选择/编辑/切换保护使用既有代次门；本轮只测试正常使用链，不开展被取消的精确安装竞态 probe。

9. **身份范围先于私有字段读取。** 新 authority、binding、target 查询应在 SQL 中先限定 owner/project 或先定位公开身份元数据后锁 owned project；不能先读取外项目私有候选/authority payload 再判断 owner。targets 枚举应先排除原 app，并在进入目标生成 provenance/bytes 前排除原 resource alias。

10. **历史只读与可执行 read 要分清。** 项目索引和撤销入口须能保留并显示 REVOKED/EXPIRED/CLOSED 元数据，以便处理已失效授权；执行与候选/结果读取须严格当前授权。合同“每次读重验预算”宜说明历史管理 read 不等价于执行授权，否则预算收紧可能妨碍撤销。旧 source task/app/Release 仍保持原内容权限门，撤权后不得通过新 logic API 旁路读取。

## 冻结后最低必要校验

以下是独立验证的最低覆盖，不是已通过项目。所有用例基于冻结同一 SHA，记录命令、退出状态、source/test hashes、完整失败日志与模型请求 0。

| 组 | 必须实际证明的结果 |
| --- | --- |
| 来源与显式授权 | 标准真实成功初始文本 AppRun + Release 可预览 proof 并签发；wrong proof/Release fingerprint、无 consent、失败/UNKNOWN/CSV/agent/递归源拒绝，未写 authority |
| canonical 无旧内容 | 独立 authority/public JSON、新候选/Release/task marker 不含原 goal/输入/term/引用/结果/路径/自定义标签/原 resource ID/hash；仅私有最小 opaque 身份与承诺保留；源冻结 limits 与固定版本/Schema 保留 |
| 主链与整段 SQL 屏障 | 先签发→原 source user+runtime 撤权→原 resource content 删除→选择预先已有授权目标→绑定 fresh runtime→fresh Store/API→普通 Worker claim/dispatch/compute/commit/history；对原 resource content/hash、原 Run 私有字段、原 Release/approval snapshot、原生成轨迹、原操作/typed 单元的屏障全段保持，无缓存/直调绕行 |
| 新与错误输入 | 冷会话未见 term 得到由新 bytes 独立计算的完整正确行引用；无命中得到空引用；missing/wrong-type/blank/untrimmed/>80 term、>4096 bytes/>64 lines/>16 hits 明确 FAILED，typed 版本不增加，历史保留 |
| fresh 身份/Grant | 新 app/action/runtime 与两初始 app 身份均不同；principal 无 token；只有新目标 read Grant；有效期不超过 logic/已有目标授权；原 user/旧 runtime/目标 runtime 其他权限未复制或修改 |
| 权限与撤销 | 新 user read Grant、fresh runtime read Grant、logic 分别撤销或过期后拒绝执行/读结果；binding 前目标原 runtime 无授权拒绝；logic consumed 单边恢复或任一 revocation seal 存在都不能复活 |
| 同 owner/project | 另一 owner/项目猜测 logic/app/resource/key 必须拒绝且无未授权私有 SELECT/新写；同 source app、同旧 resource alias、非初始文本 target 拒绝 |
| 封印与闭集 | authority/binding 任一 seal 缺失/污染、body 改写、candidate/task marker 改写或删除、executor/tool/check/Schema/限额版本污染均拒绝；协调 candidate hash 不恢复可信家族 |
| 幂等与恢复 | 同 key/body 仅一个 principal/Grant/app/marker/绑定效果；同 key 改 body 冲突；丢 POST 回执只用原 key GET 恢复，GET 不产生新写，不借新 key隐式重做 |
| 事务与保留 | 在各插入/最终写位置注入失败时 principal/Grant/app/marker/seals/typed/SUCCEEDED 原子回滚；所有原对象与指纹保持；撤销/CLOSED 历史保留 |
| 期限/预算/取消 | enqueue 后、计算前、计算后但最终提交前分别撤销/到期/收紧预算/版本变化/取消，均不能成功提交；这些是新目标运行权限检查，与已取消安装竞态目标完全独立 |
| 容量与正常 UI | 64/project 与64/logic 边界：第64可写，第65无写；旧 key 可读。实际进程内HTTP的HTML/CSS/JS/API + 正常可见JSDOM完成来源预览/授权、cold index/新目标范围预览/绑定、原key GET恢复、打开内部版本/实例、未见与错误term/history、撤销；不得调用原 source app/Release/material GET |
| 既有家族回归 | 冻结后的旧 text goal、registered text extraction/recovery、CSV logic、AppRun/lifecycle 中与派发/来源门交接相关用例通过，不放宽旧来源权限门 |

SQL 屏障应证明实际单元求值受阻，包含 alias/join/CTE/subquery/aggregate/全表 SELECT 等形状；只检查询字符串里的原 ID 或只扫描最终结果没有旧文本不足。可用已有 `tests/sql_private_barrier.py` 的能力，但不能把历史 CSV 探针记录当新文本运行证据。

## 边界及剩余状态

此处尚无新实现、源码冻结通知或测试执行，所有运行项 `NOT_RUN`。PG/应用角色、Windows/native browser、真实设备崩溃、真实模型/付费、人工语义、全旧源码升级、完整 P-A/P-B/AT-10、正式发布/部署保持 `NOT_RUN`；owner PENDING、semantic UNKNOWN、LIVE0、正式发布 false。已取消精确安装竞态对照单独永久 `NOT_VERIFIED`。

无工具/平台动作拒绝。本阶段只读命令中 `rg` 查询两处不存在的辅助路径产生普通文件不存在诊断（`.agents/.codex`、`goal_generation.py`）；没有变更权限或换工具绕过。仓库及 `/workspace` 父目录未发现适用 AGENTS.md。审查后的 `git diff --stat -- src tests` 为空，基线产品/测试未改。

## 审查文件哈希

```text
484334d7a755ff3075e527a9376f8783259e65bb8e2b0261e64377355dbc522c  docs/F2/PBTextLogicReuse20261012.md
aef7275c34a02b4c562c0144fa7a7e729625eebeffb90a18fd54119596194c98  src/sim2act/text_apps.py
22b59be22ff29507c5c57833badc6b83c2cbe4cefc66f71cb2a5f20c3e6ff0f6  src/sim2act/apps.py
d7edf63b2d6e854cf6cff297c92b4fb56823ea7c90b310abda5eebff57b6c52e  src/sim2act/registered_run_extraction.py
3ea23ffa27748c9022834ddc48eca7bf7f8a5a62721785dea59582031eaf71e1  src/sim2act/csv_logic_reuse.py
ed8ab6c36211557b7c30033c0dde756c92bebe02eae325001c88615fc8958039  src/sim2act/lifecycle.py
6455166415607fe0a5b73faf0bb28b3def8e635861c1a410f12560f4204c659f  src/sim2act/app_jobs.py
03763e3c21c92044549a63f9af1fe164b6207abdcb020d4b185019059e121eec  src/sim2act/text_run_checks.py
43562f69ebf723b18446f28417b5791e7fd9f6a953bead48ed6fbf974160b4b4  src/sim2act/db.py
```
