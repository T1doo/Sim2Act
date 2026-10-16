# F2-T05 自然规范应用入口独立复核

复核时间：2026-10-16 UTC。只读独审；未修改仓库，未访问旧实例，未复制源码树，未调用真实模型。

## 冻结与范围

- 基线：`8fc70cc43a6ac81cd522249e8a3d367cd66c9238`。
- 最终复核提交：`f9adaae3b34ef498854e2ac57f955679ee7c1ef8`；本次复核 HEAD 精确一致，`git status --short` 为空。
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

前轮审查提出的 workspace ABA、finally 归属和旧 ACCEPTED 文字残留问题均已修复并在冻结导航探针复验。

## 独立实际运行

运行命令：

```text
/workspace/sim2act-venv/bin/python -m pytest -q tests/test_natural_application_entry.py::test_natural_entry_navigation_synthesized_api --basetemp=/tmp/f2-entry-independent-f9-final --junitxml=/tmp/f2-entry-independent-f9-final.xml
```

实际结果：1 passed，0 failed，0 skipped；7.51 秒；一条 Starlette TestClient 弃用警告。精确 XML：`/tmp/f2-entry-independent-f9-final.xml`；原始导航 JSON：`/tmp/f2-entry-independent-f9-final/test_natural_entry_navigation_0/navigation.json`。

该测试在最终 `f9adaae3` 加载生产 index/app/internal/use/owner 脚本，用合成 GET API、局部 renderer stub 和 JSDOM；35 条检查，以及后续实例工作区 ABA 和旧人工 ACCEPTED 清除检查通过。新增两族目录各两条，实际验证 natural metadata 目录零应用详情/私有实例 GET 且有显式打开按钮；其余覆盖等待应用 GET/内部历史/实例 GET 三阶段的 workspace/project/identity ABA，双选择及同 view 的实例切换；零 POST。原始 JSON 含最终加载的精确五资源 hash。

前序 `bd23f9f` 的导航曾为 1 passed/31，留存 `/tmp/f2-entry-independent-final.xml` 和 `/tmp/f2-entry-independent-navigation.json`，仅作阶段记录，不能代替最终 35 条证明。首次尝试默认 `python` 无 pytest，未运行测试；使用已有 `/workspace/sim2act-venv` 后成功，未新增安装。

本独审未自行运行新 HTTP/Worker 节点；只静审其实现。新 driver 真实点击 metadata 目录按钮、再显式选择已有实例，冷打开前断言未读 app 详情/internal apps。根线程最低六节点计划为 PA-normal、PB-normal、导航、旧 catalog_instance、旧 catalog_use_ui、旧 CSV；其实际结果应单独作为 HTTP/Worker 及回归证据。

## 测试合同修正复核

此前指出 `bd23f9f` 新 HTTP driver 把 PA 专有 `instance_data_version` / `real_model_allowance` 字段用于 PB。`0a3e8d0` 的 8 增 2 删仅修这两个断言：PA 仍核原字段，PB 核已有有效候选的有限 max_requests 和原允许动作集合；两族共同核零 new_model_requests、零 artifact_writes、formal_publication_enabled=false。与原 per-use API 家族差异一致，没有为测试扩展 API；此问题已闭合。小差异的 `git diff --check` 通过。

本报告结论：最终 `f9adaae3` 的产品静审、测试合同复核和独立 35 条导航证据通过；无剩余必须修问题。本报告不能单独当作 PA/PB 新 HTTP/Worker 节点已通过的证明。前两批被中断的 0 完成节点、XML/log/RC2 均不计通过；其中一批约 6 分钟仍执行也不能当作单请求 latency 测量。

非阻塞的证据精度说明：PB driver 的 permissions.every 证明现有列表没有其它动作，并非单独证明两个权限项均存在；原始响应回执和服务端现有重建门仍保留，不能据该一句断言声称权限集合的完整精确等价测试。

## 未执行与原有缺口

本次新增 PA-lost 场景保留但 NOT_RUN；不冒充此次恢复验证通过。防重复的计划证据为正常场景真双击及既有 CSV 回归，实际结果由根线程记录。Windows、原生浏览器、PG、真实模型、真实材料场景/人工语义、远端 CI 和部署均非本独审执行证据。未重复底层 Worker 重启/取消矩阵。旧环境最终独审未落盘及历史作者 1P XML 独立核验不足仍未补回。

## 冻结文件 SHA256

```text
b659bfd6d1eb46a9de5c07c879cd6726788339b3726d832afdc0b1ed0865abfe  src/sim2act/api.py
dc8a663af5b29e768d58ff4b8aad535f49f687b3132826fc502dafaa39c3c164  src/sim2act/web/app.js
f072c927b78fac20e66fe8d11421b7c1e684404c2fe7e7d1111a1d9dd70b6831  src/sim2act/web/index.html
2fc015917cf2908fa59503f4453c48029542e00e80a8daae0dd886546bd00564  src/sim2act/web/internal.js
7d2c748910520f1d1aa811ec208387c994aad8fe1577cf420da0b228b76d58d0  src/sim2act/web/owner-review.js
0e2c8d6ad6aaed5ff4466bbe8d74b68f0e9093b4cbc21ddb401a648fcfb576fa  src/sim2act/web/use.js
2286fd354463bc228adc79bd79957ebd207fbe4cb44677e324da34d76daa0e84  tests/natural_application_entry.cjs
39c2688d19f804adc479d63a988ff4e132afcc295599abff97aaf4ad56d65da1  tests/natural_application_navigation.cjs
709eb61e486f85629afb6c70b1370dfdc1a1b130828e13738d8b49f8ff3d01cd  tests/test_natural_application_entry.py
9436a168d9f283f77a29680c908fb1129cd15c62291f823ff097c69d72c11e63  docs/F2/NaturalApplicationEntry20261016.md
```
