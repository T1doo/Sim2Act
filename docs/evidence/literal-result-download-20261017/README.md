# 字面检索历史结果 JSON 下载

执行源码：`12a57e0ed0cf8085e28c09ddfec1a684b65194c4`；父版本：`0c94d8cc6979027ac607bed1fa69b96a6d1692cb`。

成功的字面检索历史结果各有“下载此检索结果 JSON”按钮。点击通过既有 Run GET 重新鉴权，核对普通 Run、typed AppRun、实例、Release、结果版本与完整结果一致，才生成白名单 JSON。文件包含实例、Run、Release、结果版本及材料修订/哈希、检索词、完整引文和 `semantic_status=UNKNOWN`。空命中保留空引文数组。没有新增 executor、Grant、接口、自动运行或模型请求。

作者运行两批，共 **7 个不同 pytest 节点通过**，没有失败、错误或跳过：

- `author/junit.xml`：新增 3 个参数节点，164.291 秒；`bytes`、`navigation`、`revocation`。
- `related/junit.xml`：4 个回归节点，301.876 秒；字面目录 2 项、CSV 下载版本/拒绝 1 项、自然规范 P-A 正常入口 1 项。

新增验收加载实际服务提供的完整页面和 JS，经 ASGI TestClient HTTP 运行。每例用 2 次 MockTransport 响应生成夹具，再由 3 个冷 Store/NoModel Worker 实际运行 Alpha、Beta、Absent，得到 v1/v2/v3。所有模型响应均为合成；下载阶段只有 GET，48 表快照不变，撤权例只有明确的既有撤权接口改变 Grant。

下载字节逐字节对照原持久结果，保留中文及 HTML 字面完整引文。拒绝测试在实际 HTTP 200 之后修改响应，覆盖 Run/typed AppRun/实例/Release/版本、材料哈希、检索词、引文及语义状态漂移；这属于传输适配器注入，并非数据库篡改。导航测试挂起真实 200，覆盖工作区、Run、实例、项目、不同账号、同账号重连与刷新防重；撤权例在发送前挂起，真实鉴权返回 403，清空受保护内容。网络失败及 anchor 异常均核对锁和 URL 回收。

`info.json` 保存夹具最初三个实际 Run GET 响应；`result.json` 保存请求状态、注入标签、资源哈希和断言记录，未保存每次下载 GET 的完整响应。`captured-blob-*.json` 是 Node Blob 适配器捕获的准确 UTF-8 字节，不能冒称真实浏览器落盘。

独立复验结果另见 `independent/`。同一新增 3 节点的重复运行不增加不同节点数。原始未压缩作者材料在 `/workspace/literal-result-download-evidence-20261017`；执行命令、源码哈希和语法/静态检查见 `source-and-commands.json`、`checks.json`。相关回归更完整的运行目录保留在该外部路径。

本片的 PG、正常受保护浏览器下载、Windows、真实模型/语义、远端 CI、部署均未执行。本片工程测试不关闭既有 PG/浏览器验收卡点；按后续要求单独定位。此前旧环境满盘丢失的独审报告没有补回。
