# PG 与受保护浏览器：具体卡点及最小恢复动作

核查基线及已交付功能：`4694681d281885184b0dfa52dc3f3c710a547454`，普通分支 `dev/literal-result-download-20261017` 已推送且本地/远端一致。该片 7 个不同节点通过，独立重复 3 项通过。这里仅接续前置资源定位，没有新增产品、权限、执行器或故障矩阵。

## 已定位事实

| 项目 | 实际证据 | 判定 |
| --- | --- | --- |
| PG 服务端与连接 | `current-readiness.json`：postgres/initdb/pg_ctl/psql/pg_isready 均不在 PATH；PG17 server/client 包未安装；Docker image/container 列表为空；8 个已知 PG/应用连接变量均未提供，只记存在性不记值。 | 当前证据未找到已获准的可用服务/连接；没有尝试连接，不是连接被拒绝或事务失败。不能据此断言所有版本及非标准路径均不存在。现有 psycopg 客户端不提供服务端。 |
| 系统 Chromium | 原启动命令及 SIGABRT/RC1 保留在[原始启动记录](../csv-pg-browser-acceptance-20261016/browser-execution-receipt.json)和[原始日志](../csv-pg-browser-acceptance-20261016/browser-launch.log)。致命错误要求 `/usr/lib/chromium/chrome-sandbox` 属主 root、mode 4755。当前 `stat` 为 UID/GID 65534、mode 4755。 | 已安装；终止于 helper 校验，未打开页面。不能归因产品、PG或模型，也未证明由 Playwright 协议版本引起。 |
| 执行上下文 | 当前 UID/GID 1000，uid_map/gid_map 只映射 `1000 0 1`，`NoNewPrivs=1`、CapEff/CapBnd=0、Seccomp=2。 | helper 在当前命名空间可见为未映射属主；不修改映射、属主、SUID 或进程安全设置。单纯改 mode 不能补齐现有上下文。 |
| 正常用户命名空间 | 唯一一次 `unshare --user true`，RC0，见 `namespace-capability.json`。 | 排除“所有用户命名空间都被禁用”的笼统说法；这不证明 Chromium 所需全套 namespace/renderer sandbox 已通过。 |
| 匹配官方浏览器路径 | 现有 Playwright 1.63.0 官方安装器选择 Headless Shell 153.0.8010.12，工作区 cache，无安全参数改动。一次安装调用，安装器内置 5 次同 URL 尝试，均 HTTP403 `Domain forbidden`，最终 RC1。 | 下载被域名策略明确拒绝；未获得新 executable、未发起新浏览器启动。没有手动重试、换源或代理绕过。PATH/标准位置没有其他 Chrome/Firefox/Edge。 |

原浏览器日志另含 crashpad `mkdir: No such file or directory`，尚无证据说明修复该次要目录错误能越过 helper 致命错误。这里未重跑已知失败的系统浏览器。普通 APT 元数据查询还观察到 `/etc/apt/apt.conf.d/80-applied-apt-retries` 的 EACCES；没有重新读取、改配置绕过或执行系统安装，因此不把它冒称为一次安装失败。该 APT 警告仅转录于 `observed-apt-warning.json`，不是另一次原始执行。

安装失败的精确命令（已执行一次，现停止）：

```bash
PLAYWRIGHT_BROWSERS_PATH=/workspace/protected-browser-runtime-20261017 \
PLAYWRIGHT_DOWNLOAD_CONNECTION_TIMEOUT=15000 \
node scripts/engineering-ci/node_modules/playwright-core/cli.js install chromium-headless-shell --no-remove --no-progress
```

目标 URL、RC、5 次尝试及原日志 SHA 见 `browser-install-receipt.json`；原错误全文为 `browser-install.log`。这是网络域名策略拒绝，不是自动审批拒绝或待批准操作。没有改网络/安全权限。

## 当前授权内为何不能完成修复

现有[安装路线](../../Installation.md)要求预先建立隔离数据库、显式迁移及最低 CRUD 应用角色。最新指令禁止配置凭据、安全权限或绕拒绝；自行 initdb、创建角色/密码、改 trust 认证或初始化 Docker PG 均不能作为免授权捷径。直接把 `SIM2ACT_TEST_DATABASE_URL` 指给 pytest 也不合适：既有 fixture 会 CREATE/DROP SCHEMA，`runtime_role` 还创建角色和随机密码。未执行这些动作，PG连接/事务与浏览器四步仍为 **NOT_RUN**。

浏览器可以继续探索的正常 namespace 路径尚未获得可运行的匹配二进制；现系统 helper 的身份映射与官方 runtime 下载拒绝都无法由工作区内普通文件修复关闭。没有使用禁用 sandbox/setuid sandbox、root 浏览器、放松 Seccomp/NoNewPrivs、修改系统权限或新增下载源的替代路径。

当前证据下最小可行平台动作是在**同一指定任务环境**预置验收前置资源：一个能保持正常 sandbox 启动的浏览器 executable，以及既有获准 PG 连接、已迁移 schema、最低 CRUD 应用身份和合成登录配置；通过平台私有机制预注入已批准的应用配置/令牌，勿贴聊天。无需给 API/worker 管理员凭据，也无需先安装本机 psql。若这些身份不存在，由平台先取得单独的创建授权，agent 不自行创建新凭据。

后续仅存在性补充见 `bounded-existence-inventory.json`：标准 PG 12—18 二进制目录、`/usr/local/pgsql`、`/opt/postgresql`、标准 socket 目录均未发现；列出的既有常见浏览器 cache 路径未发现，前次下载创建的工作区目录存在，不能当作已有浏览器 executable。平台暴露的浏览器管理 socket 目标不存在，Node 路径是存在的文件；仅记录存在性，未打开 socket 或启动未知服务，亦未取得本 agent 可调用的浏览器工具。这些提示不证明 renderer sandbox 可用。未遍历非标准安装/秘密目录，未读取配置内容，跳过所有前次拒绝路径；这不是全机服务或配置库存完备性证明。

## 前置资源修好后的命令与验收顺序

以下**尚未执行**；不包含凭据值。由平台预置 `SIM2ACT_DATABASE_URL`、私有 `SIM2ACT_DATA_DIR`、mock/LIVE=false 等既有应用配置，以及 `SIM2ACT_BROWSER_EXECUTABLE` 的绝对路径。浏览器 helper 复用原 launcher 的全部保护参数，仅接受明确 executable 与证据输出目录；本轮只通过 `node --check`，不是实际启动 PASS。

```bash
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py doctor
node docs/evidence/pg-browser-prereq-resolution-20261017/protected-browser-ready.cjs "$SIM2ACT_BROWSER_EXECUTABLE" /workspace/pg-browser-after-platform/browser-ready
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py start --port 8000
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py status --port 8000
```

Doctor 必须实际 `STRUCTURAL_READY`，浏览器 readiness 必须返回真实 handle/CDP 参数并在开启 sandbox 的正常 renderer 上打开 about:blank。两者只是前置门，不是产品验收。随后在该受保护浏览器按[四步原要求](../../F2/CsvPGBrowserAcceptance20261016.md)和[实际入口说明](../../FirstUse.md)运行：选择合成 CSV 文件并证明未自动保存 → 显式保存、预览并人工确认 Release/实例 → 新 amount Run 得 v1 字符串30，真实下载并检查文件及 Run/实例/版本 → 正常关闭/重开浏览器及正常重启自有服务，找回同一实例/Run/v1且无新提交。

```bash
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py stop
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py start --port 8000
PYTHONPATH=src /workspace/sim2act-venv/bin/python scripts/manage.py status --port 8000
```

保留实际页面/HTTP/下载字节/服务 PID 与重启原件及 PG 类型/角色证据。另列 quantity 新提交 v2=15 是新 Run，不能混作恢复。这里没有声称存在已通过的全链自动 driver；上述是可执行前置/生命周期命令加明确页面验收步骤。PG、原生浏览器落盘、Windows、真实模型/语义和远端 CI 均未签收。

独立 PG 路线审查见 `pg-minimum-route-review.md`。关于当前机制的解释：[Chromium zygote sandbox 选择源码](https://chromium.googlesource.com/chromium/src/+/HEAD/content/browser/zygote_host/zygote_host_impl_linux.cc)显示正常 namespace 路径；[Linux NoNewPrivs 文档](https://docs.kernel.org/userspace-api/no_new_privs.html)说明该标志继承且 setuid exec 不提升身份。它们用于解释实际观察，不能替代本机启动证据。
