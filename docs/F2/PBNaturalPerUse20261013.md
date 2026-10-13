# P-B 同一保存逻辑的有限逐次材料绑定（2026-10-13）

本切片接续 b605e80ef9af43e6ecaf29ba9eb5d97e4e58a094。旧 P-B 抽取只在抽取时绑定目标材料，不能证明同一个保存应用用于第三份材料。本实现保留同一个 app、runtime、不可变 Release、实例和保存的 edited recipe，新增每个 Run 的精确目标 overlay；不克隆应用，不修改保存版本，不导入旧答案。

## 有限合同

- 仅现有 `pb_natural_spec_task.v1` 自然规范应用、当前同一所有者项目内已授权的 TXT/MD、明确引用恰好该材料的自有 Goal。每实例最多 64 个接受的 use。UNKNOWN 语义和 PENDING 人工状态始终保留，正式发布仍关闭。
- `POST /api/internal/instances/{iid}/pb-use-reviews`：明确 resource_id/card_id、材料 hash、Goal version/fingerprint、实例 revision、保存 app/recipe/Release fingerprints 和原请求 key。预览只读，无模型请求和成果写入，返回完整计划、预算、目标、现授权前态及指纹。
- `POST .../pb-use-runs`：提交整个精确 review DTO、preview fingerprint 和独立确认 consent。事务内重算预览，授权前态（包括自然到期）变化拒绝；必要时只向同 app runtime 签发此次材料的精确 READ，仍需现有项目 SAVE。接受一份原 Run/AppRun/binding，封存独立目标 scope 和双份原 key 回执；任何失败整体回滚。
- `GET .../pb-use-requests/{original_key}`：先读取 scoped scalar Run ID，再核本次材料权限，再读完整封存回执；原 key 幂等恢复不重新执行。无接受回执为 OUTCOME_UNKNOWN。页面未知意图锁住同实例的默认和逐次提交，只允许原 key GET。
- Worker 使用现有执行器和确定性出处检查。每次回调及最终提交重验当前权限、材料/Goal、源谱系、实例/Release、lease/fence/cancel 与冻结预算。当前撤权、取消、版本或出处冲突、迟到结果不能形成成果或 typed result。
- 保存应用与原 Release 始终字节不变。历史读取重建接受时的实例 revision，新的副作用仍需当前 revision；当前 Goal、材料或授权改变可使历史验证失效，不重写历史为通过。

## 证据边界

实际测试使用 SQLite、实际 Worker、独立冷 Store、TestClient 进程内 HTTP，以及 JSDOM DOM 手势与当前 20 个页面资产；所有模型响应都是独立 synthetic fake transport。没有真实模型请求、付费 API、凭据配置、安全权限扩展或部署。

第三份此前未用材料为 field beacon，先对默认 garden sensor 保存 typed v1，再同一个应用/Release/实例显式运行 beacon 并保存 typed v2；保留旧 typed 行、应用和全部 Release。实际模型请求仅带此次材料，结果材料 ID/全文来自第三份材料。

前两次核心诊断运行在 Worker 实际成功后，分别因测试夹具误读成果 JSON 外层和比较无序 Release 行失败；页面首轮因夹具误取 manifest.name 失败。原 stdout/stderr/XML 保留，不当作最终冻结验收。独审 R1（双 META 删除降级）、R2（恢复先读完整回执）、R3（错误 SQL 列）和 R4（授权自然到期）历史证据同样保留，修复后另行重跑。

实际最终计数与完整提交 SHA 记录于交付证据 manifest。没有把旧 SHA 的测试算作本次源码通过，也没有宣称远端 CI 绿。

NOT RUN：原生浏览器、Windows、PostgreSQL、真实模型/付费服务、人工语义验收、完整通用 P-A/P-B、旧源码升级、来源退休。原本被取消/拒绝的安装窗口探针保留 NOT_VERIFIED，不重试、不换路径。

## 最终交付矩阵

核心 `8ad15c61cb87fbec878d43f902f75900be0691bd`，资格 `0b70a25c5006c69bac1549434c01ba4ac33cc918`，仅测试夹具修正 `8f2e1b04588702f706b7dd8f00160fcdd850b7aa`。

修复后合格矩阵 **62 唯一用例 PASS / 0 FAIL / 0 SKIP**：作者 61 唯一用例，独审 5 唯一用例中 4 与作者重叠，取消隔离补足 1。该矩阵共 68 次 PASS 执行（作者 62、独审 6，包含到期反例重复），历史诊断执行另存，不重复加分母。作者资格 22、集成回归 24、核心 10、原页面 4 通过及修正后 2 重验；旧页面的禁用编辑失败由真实晚预览导航用例替换。

五个页面场景共 **59 检查 PASS**：正常 10、实际丢失回执 12、晚提交导航 12、回执污染 12、晚预览导航 13；每例实际 20 个页面资产 SHA 相符。未知提交同时阻止同实例的默认运行与新材料运行；只原 key GET 恢复，迟到预览不能进入重新选择的视图。所有成果由独立冷 Store/实际 Worker 的合成 transport 执行生成，语义 UNKNOWN、人工 PENDING。

资格、24 集成、10 核心、原页面和独审均保存完整 445 文件前后映射。修正后的夹具仅变化 3 个 tests 文件：自然到期反例先断言初态有效，按原 expires_at 自然等到期且数据库字节不变再确认；页面从禁止控件编辑改为真实资源页签导航和重选实例。生产全部源码、资格 75 文件和 20 页面资产未变；晚故障函数 AST 未变，桥接证据独立复核。作者及独审最后各 2 项均完整 445 文件前后不变。不称所有历史矩阵使用相同的测试夹具字节。

实际晚故障：目标撤权 `GRANT_REVOKED`、取消/Goal/实例 revision 竞争 `VERSION_CONFLICT`、污染引用 `VERIFICATION_FAILED`；收到的原始响应保留，全部 `REJECTED_KNOWN`，无 SAVE/typed 提交。fence 竞争保留收到的原响应并拒绝旧归属结果，Run 保持新 fence 的 RUNNING，不声称其 Run.error 存在具体错误码。独立 API queued cancel 只取消第一个 Run，第二个不同 key/材料/Goal 的 Run 在同 app/Release/实例中冷执行成功。PrivateReadBarrier 实际观察覆盖其 Run/contract/resource/operation receipt/intent 列，未声称观察所有账本私有列。

新增历史夹具失败仍保留：页面误设最少 11 检查而正常实际只有 10；重负载下 2 秒授权在预览时已经过期，不能当作预览后竞争；尝试对 busy 禁用 select 做原生编辑；独审错误测试文件名导致 collection exit4/0 selected。均保留原始日志并在修正后实际复验。

`ruff src + 新增 Python tests` PASS，JS 两项语法检查 PASS；`mypy src/sim2act` 为 status_report.py 3、tools.py 2 项既有 FAIL，两文件未改，76 文件实际检查。未改 main、core dev、历史开发分支及 owner WIP。正常独立分支推送及完整最终 SHA 另以远端核验记录为准。

[封存证据及完整命令/原始日志/SQLite/源码映射/独审](../evidence/pb-natural-per-use-20261013/README.md)。
