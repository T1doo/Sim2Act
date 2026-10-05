# F2 CSV 草案预览工程证据

2026-10-05；实施基线 e171182，源文件精确 SHA-256 见 source-hashes.json；本证据随本地 F2 切片提交，未推送。F1 未签收、F2 正式准入 BLOCKED，无 Release/实例写入。

## 实际完成

固定 CSV 目标模板真实生成 ActionSpec/AppManifest，通过严格预检并消费输入/动作/输出连接；创建应用最小读取身份和 Grant；每次重新验证用户、项目运行身份、应用身份授权交集，锁定候选/资源哈希。F1 工具和预览共用 authorized_read 可信网关。预览独立持久表，不创建 F1 Run、模型 Attempt 或业务 Resource。同步只读计算，不承诺 worker 长任务/暂停取消/崩溃恢复。

11 个新专项检查 PASS；完整现有 SQLite 工程回归 123 PASS、0 FAIL、2 SKIP、1 warning，6.81s，详见 sqlite.xml。两项 SKIP 是既有 PG 应用角色/独立进程检查；这不代表 PG 通过。本恢复环境无本地 PG 工具/服务和显式隔离测试 URL，因此本轮 PG BLOCKED。新代码有 PG 兼容的 SQLAlchemy 表/锁调用，但不能以此冒充实测。

ruff 全源码/测试 PASS；mypy 14 个源码模块 PASS；node --check 前端 PASS；diff --check PASS。V5 原文、冻结 AT 与双依赖锁未改。Starlette 的既有 TestClient/httpx 弃用 warning 保留；没有为消除 warning 安装或改锁。

浏览器使用现有 agent-browser 0.38.2 和 Chromium，独立 SQLite 合成夹具，loopback 8877 API，MOCK，无 worker/真实模型。6 个检查点：UI 创建/授权草案，amount=4.00，未见 quantity=50，missing 列 FAILED 记录，明确标记历史回读，刷新/重连后三条历史仍在。见 browser-results.json、browser-snapshot.txt、preview-history.png。输入是本轮新合成双列 CSV，不使用静态42或缓存旧答案。

## 真实失败和限制

初次 agent-browser 默认 socket 目录只读，改用本轮私有 /tmp socket 目录；Chromium SUID sandbox 不可用，仅本轮受限到 127.0.0.1 的独立工程浏览器用 --no-sandbox 启动，未改变系统权限/产品配置，不能把此当产品隔离证据。初次等待不可见 option 超时，改为 options 数量条件；刷新检查初次标签未切换而超时，增加 load/login 完成等待后通过（原因判断为时序推断）。每项事实保留，未当成功忽略。

截图是在本轮合成项目内回读历史时拍摄；UI 单词“新预览成功”随后改为“预览成功”，避免历史回读里出现“新”字。只是文案改变，JS syntax 再检查；逻辑/结果未变。

PG、Win11、修复后的 Windows Server CI、LIVE/P-A/P-B、复杂 DAG/分支、发布/实例数据、增量修改和 AppRun 故障恢复均未验证或未实施；不签收任何完整冻结 AT。预算0，模型HTTP0，GitHub请求0，付费服务0。测试 API/浏览器已停止；合成夹具不用于生产。
