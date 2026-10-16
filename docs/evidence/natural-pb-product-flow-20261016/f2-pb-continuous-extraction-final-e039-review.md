# P-B 连续保存与目录复用：最终有限独审

冻结提交：`e039e0e3ec3add3e23eeb75fc9085ea017780c6d`。比较基线：`4855d5250fd576bb04f81faad22ca6a4ccdfcbdd`。2026-10-16。审查者全程只读仓库，自己的报告与探针仅写 /tmp；根线程为唯一仓库写入者。

结论：在本报告列明的静态及轻量动态范围内，无剩余未修阻断。三项 WIP 发现均已修复并实际复测；新完整 HTTP/Worker mock 产品链和受影响完整 P-A/共享模块由根线程执行，本报告不提前声称那些节点通过。

## 冻结与静审

- 实际 HEAD 为上述精确 e039，产品冻结后未修改。最终核对时仅根线程 `docs/evidence/natural-pb-product-flow-20261016/` 证据目录未跟踪，本审查者没有仓库变更。
- 产品仅改变 `web/app.js` 与 `web/internal.js`。API、原 source/review/extract/verify/by-key 协议、executor、权限/Grant 类型、lease/fence、Worker 均未改。新增三个测试文件与一份说明文档。`git diff --check`、两个生产 JS 的 `node --check` 通过。
- app.js SHA256 `fbe8cb904aaf0856ef0c560b8ce7d6d25843a85ca70c74624522d3b80de3583e`；internal.js `44ada6a6aec8c1ec4ac7c5f56eef6d79b8303926d34d56c3cc288c1939323cdc`。这与修后隔离 21-check 执行及最终 DOM 38-check 执行的生产字节相同。
- 原成果 extract 入口现在核 node/view/instance/selection 后才发起。来源证明成功读取后才启动 PB guide；准备目标复用共享原 forms，source-options 同 proof/recipe 指纹及新 Goal 精确版本/绑定重新核对后仅回填，不自动生成 PA、不审阅/保存提取或 Run。
- guide 的 PB inputs/extract/internal 分支与 PA generate 分开；旧 PA guide 在同一来源 view 转 PB 时不会清掉该来源工程视图。普通身份/项目/workspace/应用选择会失效原 guide；未知提取意图 Map 保留，取消不会删除已存材料、Goal 或 app。
- 保存仍是原独立 review、ack、提取 POST、原 key GET+app 回读完整核对；保存后按钮与 action 两层 s.saved 保护禁止重复提交，编辑才失效旧成功状态并要求重新审阅。未知回执不重发，不另换 key。原 naturalTaskRequests 仍仅页面内存，不能宣称跨冷页自动恢复。
- saved app 交接核精确 candidate/来源，完整 showApp→openInternal→refreshInternal 成功与 historyReady 后才按同一函数引用释放临时 opening fence；再绑定精确新 engineering view，原 Release/instance 成功观察器按 id/fingerprint 推进。失败只清自己的当前 guide/view，报告已保存 app 保留并从目录重选；迟到失败不清新选择。
- PB 新 per-use 提交每次 GET 原可用性 metadata 并核 model=intern-s2；无有效离线配置则不建 Run 意图、不 POST。等待返回后再次核同实例其他 pending/unknown/view.busy，保留互斥。原 key GET 恢复不受新 gate 阻断。该 gate 不是模型批准，实际 MockTransport、权限/版本/预算与 LIVE 关闭门仍由原后端执行；PA 新提交没有加入此 PB-only gate。

## 三项 WIP 发现的关闭证据

原 WIP 报告 `/tmp/f2-pb-continuous-extraction-wip-review.md` 和两份反例 JSON 均保留，不覆盖。原 internal 字节 `403859d1...` 下曾复现 cap 等待期间竞争默认 intent 后仍 POST PB，以及 firstCreation returning 无 instance 的 TypeError。

冻结修复：cap 后再核 pending/unknown/busy；showInternalInstance 在读 id 前核 !prep.instance；saved open 增加 current 限定失败收尾、显式错误状态和完整 historyReady 门。使用实际生产 action、showInternalInstance、PB open handler、showApp/openInternal/refreshInternal 函数与合成 API/DOM node 闭包独立执行，修后 21 checks PASS：两原反例关闭，403、candidate 冲突、内部 history 拒绝、workspace/app 选择迟到与正常交接均符合预期。

原始修后隔离证据 `/tmp/f2-pb-fixed-isolated-probes-v2.json`，SHA256 `188cada574459fe40ba0150cc2504477b98bf326649c416efc3068fddd967c69`；脚本 `/tmp/f2-pb-fix-isolated-probes.cjs`，SHA256 `b993fd547c729b8fa10524799e0795959efee0d74b57e3bc1d33b722359593c9`。这是隔离真实函数测试，不是完整 DOM/HTTP/Worker。其初轮夹具遗漏 appPreviewRequests，导致未到 held API 的 FAIL，保留 `/tmp/f2-pb-fixed-isolated-probes.json` 与 `.log`，未计通过。

## 本审查者最终独立 DOM 运行

```
/workspace/sim2act-venv/bin/python -m pytest -q tests/test_pb_natural_product_flow.py::test_pb_product_navigation_synthesized_api --basetemp=/tmp/f2-pb-independent-e039-nav-correct --junitxml=/tmp/f2-pb-independent-e039-nav-correct.xml
```

实际 RC0、1 passed / 0 skipped / 0 failures，10.29 秒；JSON PASS，38 checks；一个既有 Starlette/httpx 弃用 warning。driver SHA256 `707bbcb6e698d738555f428c361c64098ad40254cb1aa25f988e0f719c004046`。

该例为实际生产完整 DOM/脚本、合成 API、分阶段设置的 source view 或 review；其分类明确 `ACTUAL_PB_EXTRACTION_PREPARATION_AND_USE_GATE_SCRIPTS_SYNTHESIZED_API_STAGED_VIEW_OR_REVIEW`。不冒充真正 HTTP 来源链或真实后端权限证明。worker、real_model、native_browser 均 NOT_RUN。七个页面资产 hash 与实际文件相符。

实际覆盖来源读取后启动 PB guide、新材料/Goal 共享表单返回仅 GET/清旧确认、取消还原原表单、source proof 改变拒绝回填；source-options 身份/项目/workspace 迟到与 review 迟到；saved-app 打开 workspace/cancel 迟到；新 PB gate BLOCKED 零 Run POST/零 pending、能力 GET 身份/项目/workspace 迟到、原 key 恢复仍可 GET；cap 返回后默认 pending 互斥；403 打开失败保持 saved 内容提示；firstCreation returning 实例切换；saved 后直接重复 submit handler 零 POST。

原始证据：

- `/tmp/f2-pb-independent-e039-nav-correct.xml`，SHA256 `5ba2ce12e63bc0bc1f91521e3874c083ce9a7db8e19705111f0af12565816030`
- `/tmp/f2-pb-independent-e039-nav-correct.log`，SHA256 `ca542c62cec0b1fa7db87899af0edd188ce055a965f758cc3282948880f84bd2`
- `/tmp/f2-pb-independent-e039-nav-correct/test_pb_product_navigation_syn0/navigation.json`，SHA256 `6d51c53b55debb21eec7ff77918374e9c39cd582176fc2210b98850df44a2729`
- 同目录 `driver.log`

本审查者首个命令手误节点名多了 natural，collection RC4、0 selected，原 `/tmp/f2-pb-independent-e039-nav.log` 与 `.xml` 保留；随后改正节点的上述实际 PASS 独立记录，不覆盖或计入通过。

## 新重链测试的静态验收范围与尚待实测边界

已阅读 `test_pb_natural_product_flow.py` 和实际可见手势 driver。设计包含真实成功来源→准备目标→编辑图与精确提取→实际接受201丢失+双击一 POST→仅原 key GET→原审批版本/实例→目录冷打开→另一份材料/Goal→PB per-use 新 Run 首次 v1/同 Run owner PENDING→冷只读→实际 API 撤销原来源 READ 后新读取拒绝。主线程仍在运行，不把测试代码存在当成通过。

source_unchanged 精确比较原 app/Release/instance、typed result 行、artifact 资源行，且原 Goal/version 行保留；未逐字比较所有原 runs/internal_app_runs/attempts/events 行，因此不能仅凭 source-preservation-proof 的 source_run 字段宣称全部旧账本逐字不变。该证据限制不构成此次纯 UI 变更的未修阻断。

PB 保存时绑定的目标材料尚未执行；随后目录里的另一份材料产生该 PB 实例首次 v1，不是 PB v2/旧 PB 成果保留验证。owner 同 Run 入口仍 PENDING，不代表实际人工 DECIDE 或语义验收。

没有执行重 Worker fixture、旧恢复矩阵、真实模型、原生浏览器、Windows、PG 或远端 CI；不声称修复旧多历史 heartbeat 数据库锁失败。最终产品链和完整受影响模块结果以根线程冻结实测日志为准，不能与本次独立轻测拼成同一批全绿。
