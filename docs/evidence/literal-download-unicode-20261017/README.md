# 字面成果下载：Unicode 码点边界修复

执行源码：`ba74572af2722ed38d763316603548417000d7dc`。产品仅改 `internal.js` 一行：`Array.from(value.term).length > 80`，与既有 `text_apps.compute` 的 Python `len(term) > 80` 一致；服务端、授权、Run/Release/版本绑定及下载白名单均未改。

旧逻辑使用 UTF-16 code unit 数，合法的 41 个 emoji 已超过80，因而静默隐藏已持久成果的下载按钮。旧源 `968144fe3083fda7a58924f5abce17cadfb87ea5` 只增加回归测试，产品字节仍等于469468；实际重现 **1 FAIL，33.736秒**。API与冷 NoModel Worker 先实际持久化41/80码点结果，81码点实际失败，随后页面断言合法版本应有两个下载控件失败。`red/` 保留原日志/XML、实际 Run 响应、失败页面记录与 SQLite 原件；原未压缩文件仍在 `/workspace/literal-download-unicode-evidence-20261017/red`。

修后作者一次执行 **4 PASS / 0 FAIL / 0 ERROR / 0 SKIP，318.931秒**：原 `bytes/navigation/revocation` 三项回归及新增 `unicode` 一项。独立只重复同一 `unicode` 节点 **1 PASS，37.552秒**，不增加不同节点数。红绿之间测试字节未改，产品只改上述计数。见 `verification.json`、`final/junit.xml` 和 `independent/independent-proof.json`。

新增用例用单一码点非 BMP 字符 😀 重复41/80/81次，经原 HTTP 接受和冷 Store/NoModel Worker 执行：前两条成功且无命中，持久成果 v1/v2；81为 INVALID_INPUT FAILED、无 result/result_version、无第三条成果。完整实际服务 JS 在 JSDOM 中展示两个下载按钮，分别重新鉴权 GET 后逐字节比较 UTF-8 JSON、文件名及空引文，URL全部回收；同一完整绑定的80码点证据允许，81码点证据拒绝。下载阶段48表快照不变。生成夹具仅2次 MockTransport/例，实际运行不调用模型。

这是**已持久合法成果的下载**修复；运行请求由实际 HTTP 测试夹具建立，没有证明浏览器原生输入框可键入80个非BMP码点。既有输入框 `maxlength=80` 的UTF-16行为未在本片调整。PG、原生浏览器落盘、Windows、真实模型/语义及远端CI均未在本片验证。

此前469468的3项新增、4项相关回归及独审原证保持原字节和原分母，不能算作本轮新执行。缺失归档的18份独审 `data/*` 已从原 `/tmp/literal-result-download-independent-12a57e0e-20261017` 按未变的原 proof manifest 逐件核对并补入[原证据目录](../literal-result-download-20261017/independent/)，没有为补原件重跑；核对见 `original-evidence-verification.json` 和[补充收据](../literal-result-download-20261017/independent-raw-supplement.json)。它们包含原始请求状态、初次实际 Run 响应和 Blob，不虚构未记录的完整下载 HTTP 响应流。

本次独审完整11原件均按 `independent/raw-manifest.json` 保留，含两份 Blob、实际 Run 响应、数据库、页面/数据库证明、日志/XML和源码前后快照。SQLite与失败日志/XML采用无损 gzip，`compressed-originals.json` 给出原 SHA256、字节数、归档及未改外部原件路径；核验应先解压到字节再对原 manifest，不把压缩包 hash 当作原文件 hash。

另依父级要求仅补一次标准目录/平台暴露配置存在性库存，PG报告已收窄为当前实际检查范围和“当前证据下最小可行平台动作”；[存在性补充](../pg-browser-prereq-resolution-20261017/bounded-existence-inventory.json)不证明全机无PG或 renderer sandbox 可用。没有重读拒绝路径、再次下载/启动浏览器、换镜像、改 sandbox helper、安全权限或新建凭据；PG/browser继续保留阻塞。
