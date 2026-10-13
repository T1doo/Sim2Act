# 冻结提交有限最终独立审查

结论：**有限工程 PASS**。冻结 HEAD `bea218d546cd1578e5bf0450c9be9ad9b1667f4e` 对照 `147a6da63ecb8fe15b9dea99d1ff8035f31122c3`；本次只读复核未发现该切片的剩余阻塞代码问题。未修改仓库、Git、产品或测试；未启动新测试或 baseline probes，未终止外部进程。

## 可核查动态结果

沿用原独立 runner 的终态 `selected-result.json`：退出码 0，39 PASS，失败/错误/跳过均 0，耗时 965.67 秒。独立重新解析完整 `selected.xml` 得到 39 个 testcase 和 39 个唯一 `(classname,name)`；分组为授权事件边界 4、原键与成果 API 10、资格 22、页面 3。同一项的历史运行与作者结果均不加入分母。XML SHA256 为 `637be089d7b82131783f1f19c05b9077b735a66d1dba6efc5d1aec20b9617e1e`。

三个实际页面回执（run-lost、artifact-poison、artifact-late）均 PASS：加载实际静态资源，通过进程内 HTTP/API 桥接与真实 SQLite 工程状态，冷材料产生新结果；每次 JSON/Markdown 下载再 GET 成果。浏览器为 JSDOM，不是原生浏览器，模型为合成响应。tmp 的 current 符号别名与 artifact-late 正本同 SHA，不是第四项；完整请求、下载字节、DOM检查和文件 SHA 见 `summary.json` 指向的 receipts。FastAPI TestClient 有一条 httpx 弃用警告，不影响本次退出码。

源码桥独立重算：原 `selected-source-before.json`、runner `selected-source-after.json`、当前工作树、原 `source-snapshot` 的全部 436 个 src/tests/pyproject 文件逐个 SHA 同字节；提交一致，Git 状态为空。精确资格清单为现有算法排除 config.py 后的 73 文件，归一化仅替换 sole QUALIFICATION_HASH literal；实际清单与 pin 均相符。ANCHOR_HASH、CHANGED、来源集合与资格算法未扩大；资格 review_candidate 指向 core07c2，并非当前最终 HEAD，实际字节映射仍精确绑定当前实现。初读全 py glob 得到 74/exact_map=false，仅因审查者未排除 config.py，原结果保留于 `static-checks-initial.json`；按生产合同重新计算 73/exact_map=true，不能把两个分母误称产品差异。详见 `static-checks.json` 与 `source-map.json`。

## 静态判断与原方案对应

已读取当前 Operations 合同、封存 V5 平台产品设计及分阶段开发计划、既有 STATIC_REVIEW 和 checkpoint；独立复核核心 diff 与相应测试。

- `natural_spec_runtime.py` 在模型 SPEC_STEP_VERIFIED 后先 fresh commit_guard，再读取完整回执/Attempt；`pa_spec_apps.py` 本地步骤事件后先 guard，SPEC_COMMITTED 后先 job_scope_gate，再读取终态和完整 Run。后续 full verify_job、模型账本/审计指纹、原 lease/deadline、事务回滚仍保留。
- 原键 GET 先验证当前授权实例/Release，再从原 AppRun key 定位并复验 job scope、原请求指纹、binding、accepted 与步骤。UI 在各 await（含哈希）后检查身份、项目、应用、实例选择及工作区代际，只清除同一 pending 对象；恢复只 GET，无重排队/模型调用/项目写入。pending 仅在本页内存，页面重开读取既有历史，**不承诺跨版本冷 key journal**。
- 成果 GET 验证已保存真实资源；UI 核对完整作用域、结果版本、资源 ID、原 JSON 字节/SHA、输出指纹和独立 Run Markdown，核对通过后才文本节点展示或下载。迟到工作区响应不渲染/下载；finally 仅恢复同结果控件。清单保留要求、条件、例外、未决项、引用、未覆盖非空白片段及完整原文。覆盖不等于语义完整。
- owner-review 对此家族明确 PENDING/UNKNOWN，禁用未支持签收入口。该工程链路补进 V5 P-A 从应用使用、历史版本分开与授权复核（F2-T02/T08、AT-09/21）的一段，不能推导完整 P-A 或自然规范 P-B 已完成。

## 历史、观察边界与未运行项

原失败/中断保留在 `../history-author-original/`：red-callback 为固定时钟事件排序夹具失败，r2 为观察器误挡原始响应 NULL CAS，r3 四例为实际私有字段读取顺序缺陷的历史复现；operations-r1 四处为夹具 app_id 类型及既有 HTTP 状态断言问题。原 final-backend/final-ui 被 SIGINT 中断（reason 文件记录用于修正非空白覆盖措辞），即使残留 XML 无失败也不是完整 PASS。历史分类索引、原 XML/log/test 与中断 reason 保留引用并列入 SHA manifest。

新四例 UDF 观察真实求值的合成非空 Attempt parameters/response/usage，校准后在撤权/到期事件边界观察 0 受保护 cells，GRANT_REVOKED，lease/deadline 仍有效并无成功 typed 制品。观察器放行写入以保留 NULL CAS；SQL 改写仅覆盖实际生产查询形态，不能当作所有可能 SQL 的证明。撤权 monkeypatch 是同事务故障注入，控制时钟是 Grant 到期观察；生产 Store.event 只 INSERT，SQLite BEGIN IMMEDIATE 排斥外部写者，**不得称真实外部并发攻击或 API 内容泄露**。未新跑两项 baseline expiry probes。

真实模型请求 0、真实语义 UNKNOWN/NOT_RUN、owner PENDING。自然规范完整 P-B 仍缺独立入口与成功任务来源合同；新材料 P-A binding 不能代替 P-B。正式发布、真实授权资料验收、完整 P-A/P-B、原生浏览器、PostgreSQL、Windows、CI 与旧取消安装窗口均 NOT_RUN。作者 frozen backend/UI 在本次捕获时尚无终态，不影响独立 39 项有限判断，也不计入其分母。

父任务报告接管 session32281 的 write_stdin 返回 Unknown process id，属于会话读取限制；本轮从现有 PID/runner 产物收集真实终态，未重跑或 kill。显式 spawn 参数不能核验实际模型、reasoning、service tier 或 Fast；这些状态 NOT_VERIFIED，不能声称 Fast 已关闭。

本目录在生成本报告、summary、源码映射及 SHA manifest 后停止写入。
