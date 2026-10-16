# 自然应用本次材料 / Goal 准备：有界产品验收

基线 `5d6afe2fd23f6fbc059d5243323a071030e5f36d`；新普通开发分支 `dev/natural-use-input-preparation-20261016`。产品字节最终冻结于 `9cac89c998731dc0983d9e8daa005e795f13c62d`，最终定向测试冻结于 `a56db717d34b9425f7701ee971e5214678e24b5d`。后续交付提交仅归档说明和证据。

本轮同一新环境 `/workspace/Sim2Act`，开工 HEAD 与原远端均为 5d6，工作区干净，根为唯一仓库写入者，工作区可用约 27 GiB。并行代理只读仓库 / 写自己的 `/tmp`。未回旧满盘环境，未删除未知锁或进程；旧环境未落盘的独审报告并未补回。`base-remote-check.txt` 记录原 5d6 分支、8fc 分支与 main 精确 SHA。原方案和运行合同继续保留；无新 executor、无新 Grant 种类、无自动执行或部署。

## 最终实际执行

最终各批原始日志 / JUnit / 驱动回执逐项保存；不把分阶段尝试合成单次全绿矩阵。

- `prep-pa-final/`：1 PASS / 0 FAIL / 0 SKIP，360.84s，41 checks / 38 gestures / 42 asset loads；精确单参数 P-A，实际 TestClient HTTP + 实际可见 JSDOM 表单手势 + 实际 Worker / MockTransport。动态从 201 回执采用新材料和 Goal ID；材料/Goal保存后无自动 Run、精确原应用/Release/实例返回、显式预览及确认、新 v2 / 旧 v1、同 Run 人工 PENDING、冷页 GET。新 Run `run_afb938c3c391416286179249add1361e`；新材料 `res_71872441c8d8452ea1f2f2ebf1a7863d`；新 Goal `goal_3025e214e76442e0969325c3a2eeaf50`。结果以该目录 XML 与 result.json 为准。
- `prep-pb-final/`：1 PASS / 0 FAIL / 0 SKIP，568.61s，38 checks / 32 gestures / 42 asset loads；同一产品流程 P-B；实际家族合同和唯一 Goal 材料绑定、返回和新结果，mock-only。新 Run `run_0c03d8a5013c41ae8562d280a09f1ef9`；新材料 `res_a8be0aaebe0e49c8be5c7d59aeaeb5cd`；新 Goal `goal_e8f76fc79cb4461aa5164f7e92ae6882`。结果以该目录 XML 与 result.json 为准。
- `prep-ui-final/`：4 PASS / 0 FAIL / 0 SKIP，5 个未选参数。真实页面脚本 + 合成 API 的隔离探针 39 checks；另有 CSV 本地文件 business/guards/manual 三例真实 loopback HTTP，business 运行 NoProvider Worker。身份/项目 ABA 的材料与 Goal accepted 迟到隔离、未知 Goal 只读核对及禁止重 POST、取消恢复原表单与通用 Goal / CSV 保存、后台共享 renderer 仍锁已保存材料均覆盖。
- `prep-shared-regressions/`：18 PASS / 0 FAIL / 0 SKIP。Goal 执行 UI、实际 HTTP、Goal API 版本/授权/拒绝，CSV 保存应用的真实 HTTP 使用，原自然目录导航。最早一例 Goal 合成 UI 运行在 044 产品字节；最终材料锁修复后的同例由 `prep-goal-ui-final/` 单独重跑 1 PASS（27 checks），不把早期摘要冒充最终源字节。HTTP Goal 例加载的 app.js 摘要已与最终冻结一致。
- `independent/`：有限独审无剩余必须修问题；独立探针 1 PASS / 39 checks / 7.42s。合成 API，无 HTTP/Worker，不代替两族实际验收。实现报告 SHA256 `18db21dcc6ccb76783d19f0fd735fde2d84f554eaab14886092d084a42276859`。
- `static-checks.json`：7 条静态检查全部 RC0（受影响 Python 测试 Ruff、5 个 JS 文件 Node 语法、Git diff 空白检查）。

`source-freeze.json` 保存 25 个 web / 受影响测试文件 SHA256。两族最终驱动记录两次冷/热页全部实际服务器资源摘要、可见 enabled 手势、所有 HTTP 请求/回执；`runtime-wire.json` 仅本轮新 per-use Run 的 mock wire。其 wire=1 不包括 fixture 准备阶段的其他 mock 调用。`persistence-proof.json` 与阶段 checkpoint 证明旧 Goal/应用/Release/实例历史保留，保存仅增加新材料及其原项目授权、新 Goal 版本；不声称没有使用原保存 API 的授权效果。

## 保留的先前尝试

- `prep-regressions/`、`prep-core-regressions/`：命令误引用不存在的 `test_natural_application_navigation.py`，0 个测试执行；已改为真实已有测试节点。
- `prep-resource-regressions/`：2 FAIL / 1 PASS。business 因根在运行中修改 app.js，冷页资源摘要不一致而失败；guards 中旧测试错误地把 `.txt` 当非法扩展，而已验收 5d6 通用导入已支持 TXT/MD。测试仅改无效扩展为 `.bin`，保持拒绝断言；最终 4 例批次重跑通过。不是生产放宽限制。
- `prep-pa-first/`：2 FAIL。P-A 首次跑到 Goal 保存 checkpoint 后测试错误读取 `goal_cards.content`（该列不在 metadata 表），现从 `goal_card_versions.snapshot.content` 验证绑定，未降低断言。`-k pa` 又匹配函数名 prepare，误选 P-B 前置 fixture；根只对已识别的本轮 pytest PID 7711 发送 SIGINT，中断其事务后该误选 fixture 报 PendingRollbackError。原始失败完整保留，未称该后端问题已修复。
- `prep-pb-first/`：0 个完成测试，根对已识别本轮 pytest PID 7939 发 SIGINT，停在 fixture，XML / 日志记录 KeyboardInterrupt。修测试后两族均用精确参数节点运行，无长矩阵重试。

初次产品独审发现的已保存材料字段被共享 renderer 刷新解锁缺陷已在 9cac 修复，轻量双独立验证覆盖；不以重跑 Worker 代替该 UI 缺陷的定向验证。

## 限制 / 未执行

旧多历史 fixture 的心跳锁失败继续 OPEN，本轮未修复、未补跑旧恢复矩阵。既往原批失败未改写为通过。Windows、原生浏览器、真实模型、真实场景/语义与真实人工验收、PostgreSQL、远端 CI、部署未执行。JSDOM 可见性与真实 HTTP 是工程证据，不等于原生浏览器或真实语义通过；新 Run 保留 semantic UNKNOWN / owner PENDING / 正式发布关闭。

最终交付 SHA、远端 direct-SHA ahead/behind、未提交/未推送差异由交付消息和仓库外 final-delivery-verification.json 给出；文内不写自指 SHA。
