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
