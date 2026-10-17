# 检索词输入的 Unicode 码点上限

基线为已接受的 `63e10935cd4dfc7045d3b8404e0ea4c9f1146a24`。本次实际执行源码冻结在 `51bc5f23210c20910d0545b642662efb5a368ae3`；后续提交仅归档证据。普通开发分支 `dev/unicode-term-input-20261017`。

## 产品变化

后端现有合同按 Python 字符串长度限制 80 个 Unicode 码点。七个检索词输入原来使用 HTML `maxlength=80`，会按 UTF-16 代码单元阻挡合法非 BMP 输入。现统一显示码点计数，使用码点模式与显式提交检查；超限输入完整保留，待用户修改，不改写或截断输入值。输入法组合结束前不创建新预览、样例批准或运行。停用的其他模式字段不参与表单校验。已有请求恢复仍使用原冻结输入。

七字段为 `app-agent-term`、`internal-term`、`text-continuation-term`、`app-workflow-a/b`、`internal-workflow-a/b`。复用现有控制器、API、授权与 Worker；未新增 executor、Grant 或权限。没有改后端 81 码点拒绝边界。

## 实际执行

| 批次 | 源码 | 结果 | pytest 墙钟时间 |
| --- | --- | --- | --- |
| 作者新增两个参数节点 | `51bc5f23` | 2 PASS，RC 0 | 144.14 s |
| 相关三个现有节点 | `51bc5f23` | 3 PASS，RC 0 | 135.76 s |
| 独立重复同两个新增节点 | `51bc5f23` | 2 PASS，RC 0，0 FAIL/ERROR/SKIP | 127.928 s（JUnit） |

以上是 **5 个不同节点**；独立重复须单列，不能加为更多独有覆盖。精确命令和节点耗时见 `source-and-commands.json`、`author-and-related-summary.json` 及原始 XML/log。Ruff、三个产品 JS 与驱动语法检查、`git diff --check` 共六条均 RC 0，见 `static-checks.json`。pytest 的 Starlette/httpx 弃用提示保留在原始日志中。

新增 `events` 节点实际读取完整 HTTP 页面与脚本，在 JSDOM 中对七个字段测试 BMP 80/81、emoji 41/80/81、混合 80/81、组合标记、完整代理对、组合输入开始/结束和模式切换。字段矩阵由驱动临时启用；不等于用户已经走完每种工作流。粘贴先派发事件，再由明确的 `setRangeText` 默认行为适配器插入字符；JSDOM 没有真实剪贴板或可信原生输入。组合事件也由驱动派发。

新增 `use` 节点通过实际 ASGI API、SQLite 和冷启动 NoModel Worker：超限及组合中输入不产生新 POST/intent；80 码点样例批准和预览保留原文；BMP、emoji、混合三次显式提交生成三个独立持久结果版本，逐次双击各只有一个提交。受控地恢复一个真实已接受请求时，即使新草稿超限且正在组合，仍重放原冻结 body，命中原 Run、不创建第四个 Run；这是一条新增输入守卫的有界检查，没有扩展故障恢复矩阵。切换 CSV 后停用旧文本字段。

随后 Python 直接提交 81 码点绕过前端：原 API 接受队列请求，额外一次冷 Worker 将其置为 `FAILED / INVALID_INPUT`，`result` 和 `result_version` 为 null，持久结果仍只有前三份。完整终态响应在 `author-round-1/data/test_unicode_term_input_actual1/database-proof.json`。新增批次页面冷 Worker 3 次、直送边界 Worker 1 次；生成使用 MockTransport 2 次，运行真实模型请求 0。48 张表的只读检查与授权主体/Grant 不变检查由驱动断言，见各 `database-proof.json`。

相关节点只运行：已保存字面目录 use、CSV 应用使用、字面下载 unicode。没有扩展其他私有屏障、回调或故障矩阵。

## 证据与适用范围

`author-related-raw-manifest.json` 列出作者与相关批次目录的全部 36 个原始文件及 SHA-256、大小、绝对原路径、归档路径。数据库采用 gzip 无损压缩，解压字节与原始文件一致，原目录未改动。请求记录保存方法、路径、body、状态；新增 use 中保存 POST 和逐 Run GET 的 JSON 响应。静态资产响应记录路径与 SHA，不冒充逐件原始响应正文。独立报告 `independent/independent-review.md` 有限通过，无失败重跑。`independent-archive-manifest.json` 保全独立目录全部 40 文件（包括原始 36 载荷 manifest、校验清单、报告、证明）；原 manifest 的 36 项逐件匹配。独立 `statics/` 的 21 份文件是与实际 HTTP 响应 SHA 匹配的冻结源码拷贝，来源明确记录，不能冒充原始响应流或新增请求。独立重复同两节点，不增加唯一覆盖。`SHA256SUMS` 覆盖本证据目录全部其他文件。

真实浏览器输入法、原生剪贴板、辅助技术和 Windows **未运行**。PG、真实语义/场景、真实模型、远端 CI 验证与部署 **未运行**。JSDOM 结果不能代替原生输入验收。既有 PG/受保护浏览器阻塞保持原结论，本片没有再次安装、探测、改沙箱或重试被拒下载。原满盘实例缺失的最后独审报告没有补回或改称通过。
