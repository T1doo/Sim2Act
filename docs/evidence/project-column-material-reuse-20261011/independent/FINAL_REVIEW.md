# 独立审查：LIMITED PASS

本次核准范围是原 F2-T03 / AT10 的有限 CSV 子项：项目改列后的固定内部版本直接绑定另一份当前授权 CSV，或单独批准无内容三步逻辑后再绑定目标。基线 HEAD 为 `d96e20e0f82793c5fe460d408ca48ff69fc0e01f`；独审只读产品，所有脚本和证据写在本 `/tmp` 目录。唯一产品写入者为 root。本报告不代替完整 P-B/AT10、通用语义或 owner 验收。

最终候选没有本有限独审发现的未解决产品缺陷。原 UI 联合剥除来源键/默认列的实际缺陷已修复，原始失败完整保留。

| 证据 | 实际结果 | 最终候选适用方式 |
| --- | --- | --- |
| SQLite、实际 NoModel Worker、进程内 HTTP 后端独探 | 13 PASS / 0 FAIL / 0 SKIP | 实际在修 UI 前完成。最终仅 `web/csv-dag.js` 改动，75 个其余 src 文件、全部 Python/DB/worker 精确同字节；按显式字节桥保留，未宣称重跑。 |
| 修复后 fresh fixture、进程内 HTTP ↔ IPC ↔ 离线 JSDOM | 16 PASS / 0 FAIL / 0 SKIP | 实际重新构造源、目标 Run、Release、Instance，重新执行页面与全部七种恶意响应病例。 |
| 额外只读 typed 数据核对 | PASS 支持证据，无额外计数 | 两个实际迟到内部 Run 都为 WAITING_RESOURCE / GRANT_REVOKED / null result；仅原 units=40 记录和 data_version=1 保留。 |

不将旧 3 PASS、旧 UI 10 PASS 或任何上轮任务结果加到本轮最终数。

后端选择的独立输入不同于作者样本。直接材料的 quantity 独立 Fraction 和为 6.5，amount 为 290；去内容逻辑目标 net 为 9.5、未见输入 units 为 40。全部由真实 read→aggregate→report worker 和独立有理数复算证明，无模型请求。冷 Store/新 TestClient 实际运行两个不同输入并保存两个 typed 历史结果；原 Release/Instance/旧 typed 行、资源、canonical app、身份权限及人工锁保持。

后端另外证明：固定直接入口拒绝将同样有效的目标 amount 列替换已批准 quantity，且零部分写入；原计划键/Run 键回放不产生新任务或写入；重签 Release 和对应 approval 的错误默认列仍由实际源计划/回执拒绝。数据免费逻辑公共白名单没有旧 amount/quantity、default、overlay、原 resource ID/CSV hash、源 Release/Run、CSV内容或结果。删除旧 CSV、使旧来源读取被拒后，逻辑仍在当前目标运行；SQL 全程追踪禁止读取旧 resource 行、旧 Run.context/result 或旧 Operation 行，目标 frozen contract 仅含新 CSV。

固定来源 LOGIC 的实际目标 Release/Instance 另覆盖两道 typed 门：已领实际内部 Run，真正 `commit_result` 插入 typed 行后，独立探针仅推进 logic clock 至精确 expiry，后置权限门回滚 typed 行和 data_version；另一个内部 Run 已完成三条真实 operation 回执后，经正式 revoke API 撤销逻辑，再由真实 worker 最终处理，拒绝 typed 提交。前者是明确标记的 fault injection，未声称真实等待 24h。两个停止结果都是 WAITING_RESOURCE 而非 FAILED；原后端断言正确要求非 SUCCEEDED、无 result、无新增记录。

修后页面从实际来源 Run 的 plan fingerprint 与完整实际计划、worker 回执绑定来源分类。冷页面选择 quantity 而非 target 第一列 amount。七种重新签名 HTTP 200 回包均拒绝，且各病例没有 POST：missing default、null default、wrong amount default、missing/wrong + 不存在普通 plan key、missing/wrong + 真实存在但与来源 Run 不同的普通 plan key。后两例排除仅靠未知键 404 的保护。实际页面加载 15 个仓库 JS 资产，逐个 SHA256 对照；没有启动浏览器或实网服务器。

只读代码审查的关键位置：`csv_material_reuse.py:69` 完整原来源授权/overlay/Run 验证后才规范化；`:175` 固定直接列必须保持精确批准，`:310` 缺默认列的目标过滤；`csv_logic_reuse.py:73` 仅有限固定三步允许规范化，`:103` 私有来源 audit 的元数据投影，`:161` 双 seal 与原逻辑 ID/原键绑定，`:197` 公共模板与私有 opaque 审计分离；`csv_dag_instances.py:156` 新目标默认由本目标实际 plan 与 aggregate 证明生成，`:445` typed 原子提交并独立实读复算；`csv_dag.py:673`、`:723` typed 前后真实 commit guard；`web/csv-dag.js:548` 修后的 Run→plan→default 来源门；`web/csv-logic.js:84` 固定来源 UNKNOWN 的原逻辑 ID / 原 plan key GET-only 恢复。未重写执行器，未放开双 sum、递归转移或未知/模型家族。

最终所有 314 个冻结 src/web/tests 文件在独审 UI 开始和结束精确一致，其中 src 为 76 个。完整实际 SHA256 在 `product-source-sha256-final.json`，完整冻结清单在 `freeze-final-before.json`；`backend-byte-bridge-final.json` 明确列出唯一改动 JS 的前后字节及 backend 未重跑事实。基线 Git HEAD 与候选内容哈希是不同事实，独审没有提交/推送。

主要证据：`backend-result.json` / `backend-second.log` / `backend_probe.py` / `data-free-sql-trace.json`；`backend-byte-bridge-final.json` / `backend-typed-final-read.json`；`ui-final-result.json` / `ui-final.log` / `ui_driver.py` / `ui_probe.js`。原始完整页面数据在 `ui-29_dqojd/result.json`。审查清单和各证据 SHA256 在 `review-manifest-final.json`。

失败历史保留：

- `ui-first-result.json` / `ui-first.log` / `ui-0ce0mlsi/result.json` / `ACTUAL_FAILURE_REVIEW.md`：10 PASS、2 实际 FAIL，二失败属于同一个来源分类漏洞。所有原脚本、13 个后端结果、SQL 与冻结清单另有 `pre-plan-key-fix-*` 不可覆盖副本。
- `backend-first.log` / `backend-first-result.json` / `backend-first-script.py` / `backend-first-error-classification.json`：3 已完成 PASS，两个情景在额外小数字符串比较停止。实际 6.50 / 9.500 已通过 Fraction oracle；夹具误要求 6.5 / 9.5。初始 freeze JSON 取错层造成空 hash 集，也已保留并修正为全 314 文件检查。均非产品 FAIL。
- `backend-typed-read-first-error.json`：额外 raw SQLite 支持读取误假定状态 FAILED / SQL NULL；实际既有协议为 WAITING_RESOURCE / JSON null，修正读取后通过，未增加测试计数。
- `baseline-snapshot-first-error.json`：初始独审资料捕获误以为 root 开始合法开发后工作区仍须干净，属于元数据夹具假设错误，无产品执行。
- 作者的首轮/二轮/三轮与已中断套件属于作者证据，独审没有把未完成运行记为 PASS，详见仓库 evidence 的原日志。

NOT_RUN：PG、Windows、原生浏览器、旧源码升级、真实/付费模型 API、完整 P-A/P-B/AT10、语义/owner 验收、remote CI、独审自有 fixed-origin typed cancellation 和并发版本竞赛专项。独审 UNKNOWN 与撤权结果局限在上述实际病例；其它范围由作者本轮最终套件另报。本切片保留 UNKNOWN/PENDING、正式发布关闭，未部署或扩大权限。
