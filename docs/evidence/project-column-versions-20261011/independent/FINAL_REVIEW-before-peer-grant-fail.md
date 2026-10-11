# 独立审查：LIMITED PASS

审查日期：2026-10-11。基线 HEAD：`a6dd6f401edb3aef997447fb41bd3f39cefd1f58`。本报告验收当前未提交候选的精确源码哈希，不将基线 SHA 当作新增实现的提交 SHA。根代理是唯一产品写入者；本审查仅在 `/tmp/project-column-versions-independent` 写独立探针和证据。

当前最终冻结候选未发现所选有限合同内的阻断问题。后端 **14 PASS / 0 FAIL / 0 SKIP**；页面 **41 次 PASS / 0 FAIL / 0 SKIP**，对应 **38 个不同检查标签**。合计 **55 次通过检查，52 个不同标签**。这些是独立脚本的检查计数，不是 pytest case 数。只计本次重新冻结后的新 fixture；未将旧 31/8/12 项结果累加。

最终结果：`backend-result.json`、`backend-refrozen-final.log`、`ui-final-result.json`、`ui-refrozen-final.log`。可复核探针：`backend.py`、`ui_driver.py`、`ui-final.js`。使用 SQLite、`.venv/bin/python`、实际 Worker/NoModel、FastAPI TestClient，以及通过 IPC 调用该 TestClient 的离线 JSDOM；无原生浏览器或 loopback 实网。

## 已审合同与源码

- `src/sim2act/project_column_versions.py:58` 先核该 peer 当前项目/身份/权限，再读精确 FINISH 账本，从实际 patched Run 重建固定家族来源。`:87` 的 `source_evidence` 重建整个 snapshot 并比较指纹，返回实际 Run 的完整 `execution_source`，包括 accepted fingerprint，未从批准响应复制该值。
- `project_column_versions.py:312` 的预批准来源端点先检查批准身份/类型，再通过 `source_evidence` 核当前来源授权，然后才调用 `validate_family` 读取来源账本。独探用 SQL 捕获确认 foreign/expired grant 均 403，受保护账本未读，GET 零写。
- `project_column_versions.py:297` 的已生成 release 来源端点只返回该 peer 的 origin、完整 execution source、affected 和 patched source。项目后来新增无关 app 会令原整组证明失效，合法 peer 冷读和实际新输入执行仍成功；页面冷读不请求父整组回执。
- `project_column_versions.py:212` 通过一个 `store.tx` 执行全组 `commit_release_tx` / `create_instance_tx`、保存完整回执，再重验定义、历史和到期/取消。提交回执插入后独立注入撤权、精确到期、取消，三例均拒绝并完整回滚，数据库快照无部分变化。常规真实 cancel 同样阻止后续 commit。
- `src/sim2act/lifecycle.py:252` 与 `src/sim2act/csv_dag_instances.py:547` 绑定整个精确 group；通用单 release 提交无法承接固定项目家族，重签批准并删除 group 也无法降级。历史恢复核合法实例谱系，原组 GET 不把已合法切换至 B 的实例重建为 A。
- `src/sim2act/db.py:486` 的 SQLite 等待仅接受 `(0,30]`；原 busy_timeout 在成功和回滚后均恢复。未据此声称 PostgreSQL 验证通过。
- `src/sim2act/web/project-column-versions.js:3` 的页面来源核对首先比较实际端点完整 execution source，再读实际 plan/worker proof。批准、snapshot、overlay graph、版本、fence、列枚举、默认列、预算、回执指纹和截止公式均绑定。每个连续请求 await 后检查当前页面/身份代次；A→B→A 和 token 切换后的迟到 GET 均不能继续发旧 worker-proof 请求。

该实现只复用明确固定 `internal.project-csv-read-sum-report.v1` 家族：冻结 CSV 材料的数值列输入，实际 read/sum/report worker，独立内部 release/instance 和类型化实例数据。保留 canonical app drafts、无关对象及人工锁；整组预览/提交继续重验父项目保留集。未扩展任意 PROJECT/SEMANTIC/UNKNOWN 执行器，也未宣称语义验收完成；`publishable=false`、semantic UNKNOWN、owner PENDING 保留。

## 实际行为证据

- 原键整组 GET/replay 保留相同 release/instance 标识并零写；unknown group POST 结果仅用原键 GET 恢复，无第二次 POST。
- 新 Store 冷读实例后实际两种新输入计算 quantity=15、amount=30。各执行三个已核 worker 步骤、一次类型化内部实例写入；新 run ID 不同。
- A→B→A 实际版本切换，revision=3、data_version=3、三条版本历史保留；旧终结 run 证明冷读成功；原 group GET 零写。
- 固定新输入 POST 真实接受后故意丢回包，实际 worker 完成，页面只 GET 原 request_key 恢复，不重新排队。
- 页面对 11 组损坏字段同时伪造 definition/base 两份预览与一致的 approval 响应并重签：plan、fence、receipt fingerprints、run version、accepted 格式、另一合法 64hex accepted、execution version、runtime limits、source hash、默认列、expiry。真实来源证明保持为服务器结果；所有损坏均令确认不可用，恢复过程只读。

## 失败历史保留

1. **实际产品缺陷**：`ui-accepted-dual-first.log`、`ui-accepted-failure.json` 和 `ui-accepted.js` 记录合法 64hex accepted fingerprint 被同时重签两份预览/approval 后错误启用确认，2 项先通过后 1 项 FAIL。根代理据此新增实际 Run 来源端点及完整比对。当前最终 `ui-final-result.json` 的 `accepted-valid` 检查已在新 fixture 通过。原失败文件未覆盖。
2. **独探夹具错误**：`backend-final.log`、`backend-prior-result.json` 保留 7 PASS / 1 FAIL；错误要求项目 patched `/runs` 为 HTTP201，而合同返回 HTTP202/CHECKS_QUEUED。修改独探断言后先完成 cold/history，记录于 `backend-history-final.log`、`backend-history-prior-result.json`；最终本次全新冻结完整 14 项通过。旧结果不计入当前总数。
3. **中断**：`backend-first.log` 因根代理要求重新冻结源码而 SIGINT；仅有部分通过，不计整套成功。
4. `ui-accepted-first.log`、`ui-accepted-mirrored-guard-result.json`、`ui-accepted-one-preview.js` 是仅损坏一份预览的早期探针，其拒绝由另一份真实预览触发，不能替代实际合法 hash 攻击证据。旧 `ui-first.log`/`ui-result.json`、`ui-extra.log`/`ui-extra-result.json` 同为早期冻结结果，不累加。

## 哈希与边界

运行前后两套独探的 **77 个 src 文件哈希完全一致**；最终复核 `frozen-before.json` 的 **294 个 src/web/test 文件均一致**。完整实际 SHA256：`product-source-sha256-final.json`；证据索引及文件哈希：`review-manifest-final.json`。

关键当前源码 SHA256：

| 文件 | SHA256 |
| --- | --- |
| project_column_versions.py | ef5234520af80b7773506066bd7de3f2d7e7b83c69c551b64766d73f28c743be |
| csv_dag_instances.py | a232077b886c622356733385d05723d766f99715c466fd03f8998fdd699ae530 |
| lifecycle.py | 502d7a5c5fbb6b5b5d892962c1819422276b9086d48fc3762556e8e0b89ba732 |
| db.py | 7793b5e06315d5996ab0cc794851a8db6ce85cc60734d10f7228948d4b89dede |
| web/project-column-versions.js | 0b2d5c7b2859c835af3390beec98c2ef54a4ab71c7c7834f982b54f71cb89387 |

**NOT RUN**：PostgreSQL/roles、Windows、原生浏览器/Edge、旧源码升级、完整 P-A/P-B、真实模型/付费 API、远端 CI 和部署。本报告未运行作者完整回归套件，亦未执行 Git 推送。作者 suite/lint 和最终提交/远端核验由根代理另外记录。当前所选有限 SQLite/HTTP/离线页面范围没有剩余阻断；以上未跑项保留为验收边界。
