# F2-T05 自然规范应用入口独立复核

复核时间：2026-10-16 UTC。只读独审；未修改仓库，未访问旧实例，未复制源码树，未调用真实模型。

## 冻结与范围

- 基线：`8fc70cc43a6ac81cd522249e8a3d367cd66c9238`。
- 当前最终源码复核提交：`bfb3c6c3c1ef8f45fb8cce8cc53dc53c44b86169`；本次复核 HEAD 精确一致，`git status --short` 为空。
- 重 HTTP/Worker 证据分别来自 `f9adaae3b34ef498854e2ac57f955679ee7c1ef8` 和 `b788949cffbac4ee48403e7d65091335324ceda1`。两者产品/driver/navigation 字节相同，b788 只收窄两行新增 PA fixture。最终 bfb 只移动 `showInternalRun` 首次 await 到原 current 捕获后并加 guard，以及新增一条轻导航；后端、Worker、普通 HTTP 参数均未变。未在 bfb 重跑 Worker。
- 已复核前序 `bd23f9f`、`0a3e8d0` 和最终目录 metadata 收窄差异。首次目录自动展开自然应用/实例/私有历史的设计已撤回修正，不作为通过结论保留。
- 比对全部 10 个变动文件：6 个产品文件、3 个测试文件和 `docs/F2/NaturalApplicationEntry20261016.md`。`git diff --check` 通过。
- 规范来源已读原 `docs/平台产品设计.md`、`docs/分阶段开发计划.md` F2-T05，以及 `docs/F2/ApplicationUsePlan.md`；已核实际 `pb_natural_uses.saved_family/review/mount`、`internal_api`、`lifecycle.instance/data_rows` 等原合同。

## 产品静审结论

本次有限接入范围未发现剩余必须修产品问题。

1. 目录分类仅增加 namespace、spec_task.kind、spec_binding.kind 标量和已有生成标记的导航提示；不返回完整候选、Goal 或授权证明。自然目录只呈现所属项目的 summary，后台刷新对该自然分支零详情/实例请求，不再自动读全部私有历史。
2. 自然目录按钮走 `openSavedNaturalUse(app_id, null) -> showApp -> openInternal`，用户显式选择已有实例后才进入 `showInternalInstance -> renderPBUse`，仍用原 `pa-use` / `pb-use` 逐次预览、确认、提交与原 key GET 恢复。提示不天然证明授权、Release 或结果版本；这些在显式打开/选择当前授权实例后核查展示。错误/损坏候选不因此取得执行权限。未改 executor、Principal、Grant 策略、后台派发、预算或数据库结构。
3. `openSavedNaturalUse` 捕获连接、项目、工作区和应用代际；finally 按精确 `selectionCurrent` 函数归属释放。内部历史/实例读取追加连接、工作区及选择代际，不能被迟到响应接管。
4. `showInternalRun` 在成功后读取相同 Run 的人工合同；历史成果卡可回到该 Run。切换到尚未成功/不可读 Run 会清旧人工选择、证据与 ACCEPTED 状态，避免旧声明代表本次任务。
5. 原普通规范 durable localStorage/Web Lock 请求记录、原 per-use pending 结构、精确指纹/版本检查、未知回执禁止重复提交的合同保持原实现；新增入口不创建 Run、Release 或实例。
6. 目录明确家族、定义版本、逐次 TXT/MD + Goal、内部未发布、真实模型默认关闭及人工 PENDING 边界，并明示 Release、实例修订、结果版本和当前权限在打开后读取并选择。不会把定义版本冒充已获授权的 Release 证明。

前轮审查提出的 workspace ABA、finally 归属和旧 ACCEPTED 文字残留问题均已修复并在冻结导航探针复验。最后额外发现 `showInternalRun` 在捕获导航作用域前 await 已 resolved 的 owner 清理也会让出执行；bfb 将 scope 固定到首次 await 前并立即复查 current，堵住同调用栈导航后继续旧 Run GET 的窗口。

## 独立实际运行

运行命令：

```text
/workspace/sim2act-venv/bin/python -m pytest -q tests/test_natural_application_entry.py::test_natural_entry_navigation_synthesized_api --basetemp=/tmp/f2-entry-independent-bfb-final --junitxml=/tmp/f2-entry-independent-bfb-final.xml
```

最终 bfb 独立实际结果：1 passed，0 failed，0 skipped；4.88 秒；一条 Starlette TestClient 弃用警告。精确 XML：`/tmp/f2-entry-independent-bfb-final.xml`；原始导航 JSON：`/tmp/f2-entry-independent-bfb-final/test_natural_entry_navigation_0/navigation.json`。

该测试在最终 bfb 加载生产 index/app/internal/use/owner 脚本，用合成 GET API、局部 renderer stub 和 JSDOM；36 条检查，以及后续实例工作区 ABA 和旧人工 ACCEPTED 清除检查通过。实际验证两族 natural metadata 目录零应用详情/私有实例 GET 且有显式打开按钮；覆盖等待应用 GET/内部历史/实例 GET 三阶段的 workspace/project/identity ABA，双选择及同 view 的实例切换；新增同调用栈 Run 导航实际为零旧 Run GET、无旧内容 paint；零 POST。原始 JSON 含最终加载的精确五资源 hash。

前序 f9 导航 1 passed/35（7.51 秒）留存 `/tmp/f2-entry-independent-f9-final.xml`；bd23 导航 1 passed/31 留存 `/tmp/f2-entry-independent-final.xml` 和 `/tmp/f2-entry-independent-navigation.json`。它们仅作阶段记录，不能代替最终 bfb 的 36 条证明。首次尝试默认 `python` 无 pytest，未运行测试；使用已有 `/workspace/sim2act-venv` 后成功，未新增安装。

本独审未自行运行新 HTTP/Worker 节点；已只读核查根线程原始 XML、P-B result/请求响应、persistence-proof、runtime-wire 与 42 次静态资源加载 hash。新 driver 真实点击 metadata 目录按钮、再显式选择已有实例，冷打开前断言未读 app 详情/internal apps。

## 已完成的根线程六节点原始证据

实际冻结为 `f9adaae3` 的六节点批次：**1 FAIL、5 PASS、0 skipped，进程 RC=1，919.158 秒**，不是一次 6/6 绿批。XML `/workspace/f2-entry-f9-evidence/final.xml` 的 SHA256 为 `1feac3efff9061cba28a7560deb7479535ca0a8805e1fad9b943f957b5108c48`；日志为同目录 `final.log`，RC 文件为 `pytest-exit-code.txt`。逐项结果：

| 节点 | 实际结果 | 秒 |
| --- | --- | ---: |
| PA-normal（原 history=True 前置） | FAIL | 151.026 |
| PB-normal 完整可见入口 | PASS | 703.709 |
| 35 条合成导航 | PASS | 7.526 |
| 既有 catalog_instance | PASS | 8.313 |
| 既有 catalog_use_ui | PASS | 5.282 |
| 既有 CSV actual HTTP | PASS | 42.656 |

PA 失败在新页面 Node 启动之前，堆栈为 `prepared_pa(history=True) -> 第二条预置旧 per-use Run -> drive_to_success`，其状态为 WAITING_RESOURCE 而非 RUNNING。任务自有合成数据库只读观察 `/workspace/f2-entry-f9-evidence/pa-extra-history-failure-state.json` 记录原首条 Run 已 SUCCEEDED，第二条旧 Run 错误为 `RESOURCE_UNAVAILABLE: Heartbeat renewal could not acquire the database lock`。这不是本次入口通过证据；本独审不把原因归为已证实仅测试环境，也不声称已修复租约/运行器。

P-B 原始回执 `/workspace/f2-entry-final-metadata/test_saved_natural_app_visible1/result.json` 的 SHA256 为 `c06997ae464deacda036495a9ef63b9118164617dbcbff3c6704b05fa0c963b5`。只读核对：PASS，66 条检查、62 次可见动作、2 次冷页面 boot；受理独立新 Run `run_3308b2beed824df7ba70baad48f1584e`，单次 `/pb-use-runs` POST 返回 202/QUEUED/非 cached；一条显式 MockTransport runtime wire；持久结果由 v1 增至 v2 且旧记录保留；同一 Run 人工合同由 PENDING sequence 0 到模拟 ACCEPTED sequence 2；冷页所有 API 请求均 GET。42 个 served asset SHA256 已独立逐个对实际执行 f9 提交的 Git blob 核对一致。其它主体详情请求 403，目录只读。真实模型和真实人工语义均 NOT_RUN；P-B 该场景未做 grant revocation，撤权由 PA-normal 单独证明。

根线程 `source-after.json` 明记 f9 批次 475 记录差异为空；本独审在 b788 阶段重新对照 `source-before.json`，唯一差异为后述两行 `tests/test_natural_application_entry.py`，该阶段产品/driver/navigation 字节均未变。

## PA 最小前置补测：独立批次 PASS

`b788949` 仅两行调整新增测试：PA 使用 `prepared_pa(history=False)`，两族 `old_versions == [1]`。已逐字核对，无产品源码、Node driver 或导航脚本修改。`base_pa` 仍实际创建并执行一条旧 Run/成果 v1；本次可见入口应产生独立新 Run/成果 v2，旧成果完整保留。未删除材料/Goal 明确选择、精确预览/确认、真双击、一条新运行、实际 Worker、新成果、同 Run 人工验收、冷页只 GET 或撤权断言。额外第二条旧 per-use Run 不属于本任务最低必要前置；原多历史底层测试未修改。

此收窄符合最低范围，不把旧失败改写为成功。b788 独立 PA-normal 补测已经 **1 PASS、0 FAIL、0 skipped，RC=0，352.423 秒**；testcase 本体为 352.055 秒。XML `/workspace/f2-entry-evidence/pa-minimal.xml` 的 SHA256 为 `ad0ae59127ca592b2f4c49f49867b1a8545c9ed087545030f02a5bd7576b35ef`，日志为同目录 `pa-minimal.log`。

只读复核 `/workspace/f2-entry-pa-minimal/test_saved_natural_app_visible0/result.json`（SHA256 `5d568973dc35979f946158bf4636ba46cf859b00964e0fe71d157ff7e8a98f99`）：PASS，72 条检查、64 次可见动作、2 次 boot；独立新 Run `run_d62f170178134e94b1f6d823a8a43401`，单次 pa-use-runs POST 202，一条 MockTransport runtime wire；v1/v2 均保留，自己的 Goal/新材料和同一 Run 人工合同明确对应；模拟 PREPARE/DECIDE 均201，冷页全 GET。精确旧材料 read Grant 通过授权 API 显式撤回后，旧目录按钮 fresh app GET 收403、无额外运行、旧成果和人工内容清空，route-contract-proof 和 persistence-proof 均留存。

PA 的 42 个 served asset hash 已独立逐个对实际执行 b788 的 Git blob 核对一致；与最终 bfb 对比，仅预期的 `internal.js` 首次 await 顺序修正不同，不能声称重 HTTP 已执行于 bfb。`source-after-b788.json` 明记该阶段 475 文件差异为空。

旧 PA history=True 失败与多历史 v3 本轮未完成的限制继续保留。原 f9 六节点 1F5P、b788 单 PA 1P、最终 bfb 轻导航独立 1P 是三个不同执行阶段，不合成为某一次 6/6 全绿批。

## 测试合同修正复核

此前指出 `bd23f9f` 新 HTTP driver 把 PA 专有 `instance_data_version` / `real_model_allowance` 字段用于 PB。`0a3e8d0` 的 8 增 2 删仅修这两个断言：PA 仍核原字段，PB 核已有有效候选的有限 max_requests 和原允许动作集合；两族共同核零 new_model_requests、零 artifact_writes、formal_publication_enabled=false。与原 per-use API 家族差异一致，没有为测试扩展 API；此问题已闭合。小差异的 `git diff --check` 通过。

本报告结论：最终 bfb 产品静审、两行 fixture 范围复核、独立 36 条导航，以及上述分阶段最小 P-A/P-B 入口和既有 CSV/目录回归证据满足本轮有限合同；无剩余必须修问题。重 HTTP/Worker 未在最终 bfb 重跑，最终差异为受影响 UI 作用域先捕获的防护和其轻导航，已独立验证；不得将旧 HTTP 的精确资源 hash 冒认为最终 internal.js 运行证据。前两批中断的 0 完成节点/XML/log/RC2 均不计通过；长耗时不能当作单请求 latency 测量。原 f9 六节点 FAIL 不撤回、不替换、不计通过。

非阻塞的证据精度说明：PB driver 的 permissions.every 证明现有列表没有其它动作，并非单独证明两个权限项均存在；原始响应回执和服务端现有重建门仍保留，不能据该一句断言声称权限集合的完整精确等价测试。

## 未执行与原有缺口

本次新增 PA-lost 场景保留但 NOT_RUN；不冒充此次恢复验证通过。防重复的计划证据为正常场景真双击及既有 CSV 回归，实际结果由根线程记录。Windows、原生浏览器、PG、真实模型、真实材料场景/人工语义、远端 CI 和部署均非本独审执行证据。未重复底层 Worker 重启/取消矩阵。旧环境最终独审未落盘及历史作者 1P XML 独立核验不足仍未补回。

## 冻结文件 SHA256

```text
b659bfd6d1eb46a9de5c07c879cd6726788339b3726d832afdc0b1ed0865abfe  src/sim2act/api.py
dc8a663af5b29e768d58ff4b8aad535f49f687b3132826fc502dafaa39c3c164  src/sim2act/web/app.js
f072c927b78fac20e66fe8d11421b7c1e684404c2fe7e7d1111a1d9dd70b6831  src/sim2act/web/index.html
777979be28f60cb42b5c8981e6d70ab5f28d6ec01e8705aabb1503f655c1219d  src/sim2act/web/internal.js
7d2c748910520f1d1aa811ec208387c994aad8fe1577cf420da0b228b76d58d0  src/sim2act/web/owner-review.js
0e2c8d6ad6aaed5ff4466bbe8d74b68f0e9093b4cbc21ddb401a648fcfb576fa  src/sim2act/web/use.js
2286fd354463bc228adc79bd79957ebd207fbe4cb44677e324da34d76daa0e84  tests/natural_application_entry.cjs
33082c5b8d99a64aa6c52dcd3e19439d02c7307264943c21459e9b26245d0721  tests/natural_application_navigation.cjs
107986de13032403795c6d88a05a7a78cf9bcb79ea0afde5d941ae4a33c6dc4d  tests/test_natural_application_entry.py
9436a168d9f283f77a29680c908fb1129cd15c62291f823ff097c69d72c11e63  docs/F2/NaturalApplicationEntry20261016.md
```
