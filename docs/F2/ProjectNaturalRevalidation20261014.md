# F2-T07 / AT-14：有限自然应用项目重验账目

本切片接续 `fbffaca5a5ca289b2c13d26d50c131d238389a21`，在既有项目内提供完整成员清单、逐应用隔离 CHECK、精确局部修改与冷启动账目读取。它不宣称完成原方案的任意项目依赖闭包或产品总验收。

## 实际合同

`project-natural-check.v1` 只接受整个项目恰有 1–2 个既有、已授权的六步双模型自然应用。服务端枚举全部 app_drafts，不允许客户端遗漏成员、过滤失权成员或自动派生图。最多一个应用引用既有的精确局部预览；其他应用执行原有效定义的普通隔离 CHECK，不假造编辑、不消耗额外局部版本机会。原有第二次修改上限不变，没有第三次修改。

清单冻结项目与身份、全部成员、源实例版本和数据版本、原 Release、原 Goal/材料、有效图、节点 ID/定义/版本、人工锁、授权与 Limits。接受时、排队时、Worker 读取时及提交时重验。PLAN/SOURCE/START/JOB/PROOF 与版本审批均保留独立回执；CHECK 实例不能反过来成为来源。只读角色发现使用标量索引，完整授权后才读取账目正文。

执行复用原实际 Worker、模型账目和六步确定性检查。每项在独立新实例中保存 CHECK 工件，原应用、原来源实例和无关应用版本保持不变。机械 PASS 要求实际两次模型请求、完整验证和 SAVE，收到模型结果或已验证五步均不构成 PASS。取消、失权、竞争和迟到结果不得提交。

项目守卫仅在同一事务、同一连接、同一写入 epoch 内复用完整成功证明；每次复用重验全部逻辑授权及期限，任意写入和事务结束清除缓存。局部预览复用限定同一已证明清单中的精确来源/key。SQLite 使用现有 BEGIN IMMEDIATE/项目锁；跨连接 PostgreSQL 隔离与锁纪律没有在本切片验证。

局部全部 CHECK 可以显示 `local_checks_status=PASS`，但项目仍固定为 `dependency_completeness=BLOCKED_UNKNOWN`、`project_revalidation_completed=false`、`overall_run_acceptance=NOT_ACCEPTED`、`semantic_status=UNKNOWN`、`owner_acceptance=PENDING`、未发布。`source_application_writes=0` 指原对象保持，不表示隔离执行没有模型调用或 CHECK 工件。

## 页面与恢复

普通项目页提供完整范围预览、逐项明确确认、所选应用独立版本审批及另一次提交确认。已接受的 key/范围被锁定。未知写回复保留原意图，仅 GET 原 key；冷启动读取旧账目不会自动继续写入。版本存在索引只是发现信号，必须完整验证版本回执，失败时保持 unresolved 并禁止重复审批/提交。

实测两连接同 key 竞争暴露 SQLite 默认等待期后 `BEGIN IMMEDIATE` 锁异常。只在 SQLite 驱动异常、整数 BUSY/LOCKED code 5/6、精确事务入口 statement 时转换为 409 `VERSION_CONFLICT`，`safe_retry=false`，要求 GET 原清单解决另一个并发请求的结果。原事务执行体不变，无自动重写、无等待期或预算调整；任意内部 SQL、其他驱动/statement/code/缺 code 均原样抛出。这个拒绝只表示该入口尚未写入，不能推断原 key 没有另一条已接受运行。

人工锁沿用既有合同：刚修改锁时，旧图封印失效；需要用户在冻结项目前明确重新派生图，服务不自动派生或解锁。人工锁正向夹具第一次漏了这个步骤，GET 图返回冲突，支持套件留下 13 PASS / 1 FAIL；按既有 `test_manual_locks.py` 合同修正夹具后另行运行。第一次两连接支持套件留下 10 PASS / 1 FAIL，原异常及两次失败 XML 均保留，不混入最终唯一用例计数。

第二次锁用例已经实际完成 Worker CHECK、原图/锁/应用定义一致，却因比较整个来源实例显示响应而失败（支持套件仍为 13 PASS / 1 FAIL）。唯一差异是新项目清单增加一个派生 `switch_policy.roles` 中的 `project_source` 防切换标记。最终断言要求所有其他实例字段完全一致、策略除 roles 外全部一致、roles 精确等于旧列表新增一个 project_source；不能减少 blocked_release_ids、解锁或笼统忽略元数据。原对象不变与新增相关清单的防切换标记分别验证，此失败历史也保留。

## 保留的失败与限制

初次与第二次核心夹具失败分别来自生成请求 key 冲突和固定 SOURCE 材料不符；修复夹具，没有放宽产品验证。第三次和第四次实际 Worker 用例未完成，分别留下 RUNNING 和两次模型结算、五个验证步骤的公开回执；没有被登记为 PASS。第五次较旧源码的 6 PASS 保留为历史，随后版本发现界面和类型/接口修复后的结果另列。首次页面流程未出现选择控件；第二次明确发现 `/api/apps` 返回 envelope 而界面按数组处理，原始失败保留。

运行期间发生一次 exec-server transport disconnected。实际原目录/文件/Git 读取恢复，同一测试进程继续并终止；没有切换环境、重启测试或重复写入者。完整错误保存在证据中。这是连接中断，不是自动审批拒绝。

旧独审第一次报告的分析 SHA 与封存时观察 SHA 不同，单独边界说明保留原报告，不把其静态检查冒充最终运行。所有后续修复各自留有独审。历史被拒的私有诊断/浏览器路径保持停止；本切片使用 SQLite、普通公开 TestClient、实际 mock Worker 和离线 JSDOM。

PostgreSQL、Windows、原生浏览器、真实付费模型、人工语义、完整 P-A/P-B、旧源码真实升级、部署和远端 CI 均 NOT RUN。新增成员迟到测试使用自有合成第三 draft，证明保守拒绝；它不证明第三个完整合法应用的产品支持。

最终源码、唯一用例计数、XML、独审和归档校验见本文件后续验收表及同目录 evidence 归档。

质量检查保留精确范围：本轮改动 Python 文件和整个 `src` Ruff PASS，新页面 `node --check` PASS；`mypy src` 留有 `status_report.py`/`tools.py` 的 5 项既有错误。额外执行的 `ruff check src tests` 为 29 项错误，`ruff check .` 为 14,752 项（其中历史 docs/evidence 脚本 14,723 项、tests 29 项）。全部报错路径与接受基线逐路径 git diff 均无变化，详见 `lint-baseline-scope.json`；这些更宽命令与历史“10 项”记录的范围不同，不能称全库 lint 通过，也没有修改历史证据脚本去消除诊断。

## 同一冻结源码验收

实现 SHA：`e93e098e5e9834237bca48f536aff9eadd5c6ee0`。冻结 SHA：`e03923d9e5216fdf05c42a6fe89d1f4458b22bc4`。78 模块资格 pin：`8424659abaf1047b28652168726c96608de2019b2c725c3e04344ca562f13dd9`。源码/tests/pyproject 清单共 470 项；每组均保存运行前后完整哈希、精确命令和 XML。

| 最终组 | 实际结果 | XML SHA256 |
| --- | --- | --- |
| core-last：22 资格 + 6 实际核心/迟到回调 | 28 PASS / 0 FAIL / 0 ERROR / 0 SKIP | `56fd65ff599c786f6171deb0f2d06c0419964996262c1bad6e73ca1329e7b892` |
| pure-final：8 错误分派 + 1 实际 CSV sum/report | 9 PASS / 0 FAIL / 0 ERROR / 0 SKIP | `4745761b78c4a2d248d89867b513db7e4be5a0316666a707e04d4d8a28c34985` |
| support-complete：12 边界 + 损坏版本冷页 + 人工锁真实 Worker | 14 PASS / 0 FAIL / 0 ERROR / 0 SKIP | `efa0838fb040359e4d3b1d13adee66ac4daa6b045163a5198ac1cb70fe6637f2` |
| page-last：正常与丢失回复两场景 | 2 PASS / 0 FAIL / 0 ERROR / 0 SKIP | `a5ee44a423cd368e9c578fbb19f98dc7eafb789eac8008fa865f7946c48c504c` |
| legacy-last：原局部逻辑/切换/R2/两种第三材料使用 | 21 PASS / 0 FAIL / 0 ERROR / 0 SKIP | `4eb109d48ec9504a4323317d6b36d6d0d15b4e76e8c4d0d6564b077742c14062` |

真实竞争记录为 202 + 409、一个 Run/一个 CHECK 实例、model 0、原 key GET 恢复同一运行且无再次 CHECK POST。损坏版本冷页有 5 项检查、21 次实际静态资源读取，均为原 key GET，写按钮保持锁定。正常最终页 20 项检查 / 25 次可见操作 / 268 次 HTTP 请求 / 42 次静态资源读取 / 2 次启动；丢失回复最终页 23 项检查 / 31 次可见操作 / 311 次请求 / 63 次资源读取 / 3 次启动。加损坏版本冷页共 48 项页面检查、126 次资源读取，资源字节逐项对照当前源码。两完整流程各 4 次 mock 模型请求，其中一项丢失回复 CHECK 在原 30 秒租约、原 300 秒截止内真实恢复，第二次认领完成；没有移时钟或增加请求。最终 `FINAL_INDEX.json` 从五组 XML 独立重算 74 个唯一 PASS / 0 FAIL / 0 ERROR / 0 SKIP，无重复 ID；五组 470 文件的 before/after/current 完全一致，完整源码清单 SHA256 为 `2aed0433d0c419d8fbc1bf9c2b17ac90e0e7ef4a2bd532935447e54382fed1b1`。历史失败及较旧源码 PASS 均排除，不借用旧页面结果。

第二次收到环境断连通知后，原目录实际命令于 13:02:41 UTC 成功：HEAD 与全部 470 项源码哈希保持，原测试会话 66746 随后实际终止，最后 21 PASS 的 XML 已取得。未重启测试、未换环境或写入者、未删锁；这次没有观察到新的工具传输或审批拒绝错误。两次环境事件分别保存证据，不把通知或无失败输出当作通过。

## 证据封存与交付

最终独审接受上述有限 SQLite 工程切片；[独审报告](../evidence/project-natural-revalidation-20261014/INDEPENDENT_FINAL.md)与[唯一用例索引](../evidence/project-natural-revalidation-20261014/FINAL_INDEX.json)已封存。独审 manifest SHA256：`6eb5acce45aa1ffbf0e4febec1c5b64b6c2c6bc2d51fc67acc156037f4c21641`。

[完整证据归档](../evidence/project-natural-revalidation-20261014/project-natural-revalidation-evidence-20261014.tar.gz)实际生成并逐成员回读校验：3,996 个常规文件，归档 43,627,389 字节，原始成员 389,024,961 字节；文件名集合、大小与 SHA256 全部匹配 manifest。归档 SHA256：`ec3ec0f4720a543146240bc6fb9f0d6613d2415e76ba85146c5677fec5db82b9`。[归档回执](../evidence/project-natural-revalidation-20261014/ARCHIVE.json)记录实际结果；9 次历史失败、13 次此前独审封印和最终独审均保留。

最终交付提交仅增加文档与证据；源码/tests/pyproject 保持冻结 e03923d9e5216fdf05c42a6fe89d1f4458b22bc4。正常独立分支为 `dev/project-natural-revalidation-20261014`。实际推送后的完整 SHA、远端一致性、ahead/behind、工作区与保护分支核验另保存于 `/workspace/project-natural-final-git-20261014.json`，避免将尚未发生的推送结果写入封存归档。远端 CI 仍 NOT RUN。
