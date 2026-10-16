# CSV PostgreSQL + 真实浏览器验收独立只读审查

审查结论：**有限接受 BLOCKED 报告；不接受本轮产品流程 PASS，也没有实测产品 FAIL。** 当前可核对的产品基线是 `f82869db2dbb53e1616f9c14b108696bb893662f`。root 为唯一仓库/Git 写入者；本审查只读取仓库和本轮原始证据，仅在 `/tmp/csv-pg-browser-acceptance-review-20261016` 写报告。未启动数据库、浏览器、应用、Worker、模型或测试，未更改仓库、权限、凭据和锁。证据审查不等于独立重跑。

## 原始证据核对

- `environment-preflight.json` 的 11 条 argv/cwd/returncode/stdout/stderr 记录逐项与 `preflight-00.log` 至 `preflight-10.log` 一致。开工新普通分支 `dev/csv-pg-browser-acceptance-20261016`；HEAD 与已接受远端分支均为 f828，dirty 和相对 f828 diff 为空；main 为 `6f688e4dd80b5c81d41aecde90e360d3629f9c21`。磁盘 /workspace 26 GiB、/tmp 8.8 GiB 可用。
- Docker 28.4.0 daemon 只读查询成功，但现有 image/container 列表均为空。8 项 PG/DSN 配置只记录存在性，均未配置；postgres/pg_ctl/psql/pg_isready 不在 PATH；常见 PG 安装/套接字目录不存在，所列进程无 PG。由此足以说明**这次受限检查未发现可以复用的 PG 实例/连接**；不是对任意隐藏安装或未提供远端实例的穷尽证明。未读取私有配置或凭据，未建服务/下载镜像。
- `protected-browser-prerequisite.cjs` 使用既有 playwright-core 1.63.0、`/usr/bin/chromium`、`chromiumSandbox:true`，有界 timeout 20000 ms。仅一次 launch；源码没有 no-sandbox、sudo/chmod、系统权限改动或失败回退。没有产品 URL，失败发生在返回 browser handle 之前。
- `browser-launch.log` 的 JSON 与 `browser-prerequisite.json` 全量一致：已安装 Chromium 151.0.7922.173；本次子进程 37073；明确 FATAL `SUID sandbox helper binary ... not configured correctly`，随后 SIGABRT；临时目录 cleanup 在原 launcher 日志中完成。`flow_status` 和 `postgres_flow_status` 均为 NOT_RUN，status BLOCKED。原 browser proof 没有独立 outer subprocess returncode 字段；后补 `browser-execution-receipt.json` 明确转录实际工具 session 40326/chunk 6dd8b3、completed write_stdin chunk 72c857 的 exit_code 1，与脚本失败设置 process.exitCode=1 一致。该补件是工具返回转录，不是独立 OS argv 捕获或第二次执行。
- 后置 `browser-process-postflight.log` 保留 PID 37088 chrome_crashpad 和 37091 chromium 两项，均 PPID 1、STAT Z、开始于本次 launch 同秒。它们是僵尸条目；37073 不在该精确 PID 查询输出。不能把 launcher 目录清理表述为整个进程树条目清零，也不应杀未知进程或触碰 PID 1。
- 更早对 `/root/.cache/ms-playwright` 和 `/tmp/codex-daemon-1000` 的 EACCES 仅由环境 metadata 记录，未提供同级原始拒绝日志；可作为操作者停止声明，不声称本审查重新验证或绕过这些路径。

## 四步流程的准确状态

| 目标动作 | 本轮状态 | 阻塞范围 |
|---|---|---|
| 普通页面选择本地 CSV 并明确保存 | NOT_RUN | 无复用 PG，受保护浏览器未启动 |
| 明确确认保存应用版本/实例并提交运行 | NOT_RUN | 同上，未创建 Run 或调用 Worker |
| 在普通页面下载该 Run 的结果 | NOT_RUN | 同上，未出现浏览器 download 事件/文件 |
| 停止并重启后重新连接找回同一结果 | NOT_RUN | 无本轮服务/PG/结果，因此无重启或冷读证据 |

没有 SQLite、JSDOM、纯接口或历史 PG/Windows/浏览器结果代替以上验收。本轮 0 应用流程测试、0 模型请求；未执行 Windows、真实语义、PG、远端 CI、部署。当前资源不足，保持产品不变并保全证据是合理结果；未把静态问题作为“已修实测故障”。

## 静态核查：后续最小路线与下载待查项

- `src/sim2act/web/app.js` 的材料入口使用真实 FileReader，资源保存显式点击；`tests/resource_file_ui.cjs` business 已说明 UI 顺序：新建项目 → 选文件（不写入）→ 保存并授权 → 创建 CSV 草案 → 可选预览 → 核查内部快照 → 勾选并保存内部 Release → 明确创建独立实例。
- 实际业务使用可从保存应用目录 `use-list` 选择实例，`use-form` 选数值列并明确运行，沿用现有 `/api/internal/instances/{iid}/runs` 和 Worker。`use.js` 已有 selected Run、result_version、历史结果和迟到导航隔离；不能把仅 preview 或历史结果当成本次运行。
- **静态待查缺口：** `use.js::readApplicationUse` 当前只把普通 CSV 成功结果 append 为文字，并渲染持久历史，未见该结果下载按钮/Blob 逻辑。`app.js::downloadResource` 是输入/材料下载，`internal.js::specResult` 是自然规范 JSON/Markdown artifact 下载；两者不等于 CSV 保存实例的结果下载。此为源代码审查发现，不是浏览器复现失败。本轮不应在缺资源时新增未经此验收的产品改动。
- `tests/application_use.cjs` 和 `tests/resource_file_ui.cjs` 使用 JSDOM、真实 HTTP、测试 Worker endpoint，并明确 browser NOT_RUN；`tests/durable_browser.cjs` 明言不是 native-browser acceptance。`tests/resource_download.cjs` 即使使用真实浏览器下载，也注入 syntheticRead/最小页面，不能证明普通用户 PG 闭环。
- `scripts/browser-ci/internal-ui.cjs` 和 `scripts/agent-ui/protected-browser.cjs` 可复用原保护参数、DOM 定位、错误收集、截图习惯；它们当前 acceptDownloads:false 且围绕预先 seed 的实例/Windows 或 agent 流程，并非本轮 CSV 文件导入→结果下载 driver。无需扩成相邻故障/升级矩阵。

## 恢复本轮验收所需的最小现有资源

1. 在指定环境中提供可用且明确允许复用的隔离 PostgreSQL 目标与现有正常访问配置。按既有迁移/应用角色职责运行；不能私自新建权限/凭据、探查未授权 DSN 或用 SQLite 替代。当前 Docker 能力与空镜像清单本身不是 PG 资源。
2. 由环境提供方提供无需降低保护即可启动的真实浏览器/浏览器通道；保留 sandbox/CSP。不能以 chrome-sandbox 的报错建议为授权去 chmod/chown/setuid，不能 `--no-sandbox`、调整 OS 策略或切换未经授权环境。
3. 两项资源齐备后，在同一 PG 的正常应用和 Worker 进程上，用用户可见按钮/原生 setInputFiles 导入合成 CSV，记录精确源 SHA、browser/version、DB dialect、UI 请求和同一 app/Release/instance/Run/result_version；下载必须由普通页面按钮触发真实 download 事件，保存文件并核对内容/字节摘要。文件选择和只读查看不得偷偷提交。
4. 完成下载后，正常停止 owned API/Worker；保留同一 PG 数据再启动新进程和新浏览器会话，重新连接并从目录选择同一实例和历史 Run。核对原材料、版本/结果、已下载内容，冷找回过程 0 POST/0新Run。仅 page.reload 或同进程 GET 不应称为“重启找回”。模型始终不调用。

以上报告只确认本轮资源阻塞及证据表述。任何实际故障修复必须在上述资源具备后获得真正浏览器 + PG 运行证据；真实目标语义与人工验收状态不提升。

## 最终报告与传递复核

已读取仓库 `docs/F2/CsvPGBrowserAcceptance20261016.md` 与证据 README：BLOCKED、四步 NOT_RUN、0 产品测试/PG/Worker/模型，静态下载待查项、启动错误、两条僵尸、未绕过拒绝的边界表述与可见证据相符。报告所列 main/父提交祖先由本审查只读 git 核验，产品源码、tests、scripts、锁/配置/工作流相对 f828 无差异；新增仅本轮报告和证据未跟踪路径。18 份 root 原件在证据目录逐字节一致。早期 EACCES 仍是 metadata 声明而非独立原始日志；RC1 补件仍为工具返回转录。没有把这些来源边界提升成独立重跑。报告可作为本轮资源不足的保全交付，不代表原用户端到端目标已完成。
