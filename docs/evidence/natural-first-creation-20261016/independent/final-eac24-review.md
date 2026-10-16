# 自然首次创建向导最终有限独审

最终源码提交：`eac24d0396c05d9a481337c42b1708e9824afccf`。上一生产冻结：`9b7d30b8f4aec699b1c3b9574b6dc6971ca4262e`。审查日：2026-10-16。审查者全程只读仓库，仅在 /tmp 写证据；根线程为唯一仓库写入者。

结论：本轮有限审查无剩余阻断。长标题、能力迟到/同 Goal ABA、首次未知 Goal 重置与取消的 view 隔离修复已在 9b7d 核实；eac24 的新 HTML 文案已消除字面家族与 natural 家族混淆。新 HTML 的独立轻量动态例通过，不将此前完整 HTTP 正例冒称为使用新 HTML。

## 最终差异只读复核

- 实际 HEAD 为上述 eac24 完整 SHA。工作区仅根线程正在整理的 `docs/evidence/natural-first-creation-20261016/` 未跟踪目录；没有本审查者造成的仓库写入。
- `git diff --name-only 9b7d..eac24 -- src` 仅 `src/sim2act/web/index.html`；API 和所有生产 JS 字节完全相同。`tests/natural_first_creation.cjs` 主 HTTP driver 字节相同；新的 pytest wrapper 精确保留 9b7d 的全部旧字节，仅末尾追加轻 probe 节点。差异格式检查通过。
- 本审查者独立用 HTMLParser 比较，2049 个标签/属性/声明等结构事件完全相同；仅两个文本节点变化。legend 由“字面引用应用”改为“有限能力应用”；首段分别说明字面完整行匹配、自然条件/例外/未决清单、人工语义检查、精确候选/样本/来源/预算、分别确认权限，以及自然仅受限离线且没有 LIVE 批准路径。没有改变任何 HTML 控件、属性或执行代码。
- 原 HTML SHA256：`5f2b8858d232e5db992e380f20eec65969ff7a23fd2141ae905e17eff433109c`。新 HTML：`9cf2503265176ca8e8a94f0c266867b86c3b2206cc40c2c0e94b786228c04c2f`。
- 独立静态原始证明：`/tmp/f2-first-independent-eac24-html-proof.json`，SHA256 `7d9b4ba702ec61c4429ae62cf41bb16bab359722846fbf9f8b1dd4b2db809efc`。

## 本审查者实际独立执行

```
/workspace/sim2act-venv/bin/python -m pytest -q tests/test_natural_first_creation.py::test_natural_first_creation_navigation_synthesized_api --basetemp=/tmp/f2-first-independent-eac24-nav --junitxml=/tmp/f2-first-independent-eac24-nav.xml
```

结果：RC0；1 passed、0 skipped、0 failures；7.61 秒；JSON PASS，30 checks。唯一 warning 是既有 Starlette/httpx 弃用提示。driver SHA256 `3073933ddeb05e3a3af3d73787b08cb22126a79fcc1166d895bc026257dfc4b2`。

该例实际加载新 HTML 与生产共享表单、向导、生成 gate 脚本；使用 JSDOM 与合成 API。核对 workspace/project/identity/cancel 导航之后的迟到可用性响应零生成意图/零 POST，不复活旧 guide；同 Goal ABA 只释放原读取锁，后续显式动作重新读取 BLOCKED；首次未知 Goal reset 不新增写入；合法长 Goal 仅默认应用名截至 100，完整 Goal 保持；取消恢复原共享表单节点、文件 accept、格式选项与通用 Goal 控件。worker、real_model、native_browser 均明确 NOT_RUN。

原始证据：

- `/tmp/f2-first-independent-eac24-nav.xml`，SHA256 `1e87f1829580ed87d3090507f6076a54e491923c70ae5fc5324a43858a537972`
- `/tmp/f2-first-independent-eac24-nav.log`，SHA256 `2074c912c9776519c036394214fb01885bd15880da19a42ff73203949cca6ae1`
- `/tmp/f2-first-independent-eac24-nav/test_natural_first_creation_na0/navigation.json`，SHA256 `fde826c57a506f9a999373770547784df205bd374f0715978736d5d8a7d3b2fc`；assets.index.html 与上述新 HTML SHA 精确相同。
- `/tmp/f2-first-independent-eac24-nav/test_natural_first_creation_na0/driver.log`

## 完整 HTTP 正例的分阶段证据边界

完整 HTTP/Worker mock 正例由根线程在 9b7d 生产字节执行，本审查者未重跑 Worker。已只读核 `/workspace/first-guide-pa-final/test_empty_directory_natural_c0/result.json`：PASS、54 checks；generation-wire 为 3 条，runtime-wire 为 1 条；三个页面 boot 的 HTML 均为旧 `5f2b8858...`。结果 JSON SHA256 `bf93a56c37e7f5c196fb472fbf87773b907f79ec068a996d9228cfc9bff729c6`。根报告该节点 1 PASS / 334.53 秒，该时间不是本审查者独立计时。

这条链覆盖空目录新材料/Goal → 候选确认 → 一个 app/Release/实例 → 返回目录与冷只读 → 第二材料/Goal → 首次实例 Run 的 v1 结果与同 Run owner PENDING 入口。它没有先运行第一份材料成为实例成果，不证明旧实例成果/v2保留，也没有实际提交人工 DECIDE。eac24 的新 HTML 仅通过本次静态结构复核和独立轻 probe；根线程另行执行的新 HTML blocked UI 节点不预先计入本报告通过数。各阶段不拼成同一冻结全绿批。

此前两份 9b7d 静审/动态补证与原 WIP 报告均保留，未覆盖。没有实际模型、Windows、PG、远端 CI 或真实语义/场景验收；没有追加旧恢复矩阵，也没有声称解决旧多历史 heartbeat 数据库锁故障。当前有限范围内无待修阻断。
