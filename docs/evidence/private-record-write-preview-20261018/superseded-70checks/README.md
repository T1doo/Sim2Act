# 私有记录试写有限交付

基线 `a1649ed443280ad16da45a0a55a0f8086889d8fd`；分支 `dev/production-trial-stages-20261018`。原 F2-T08 / AT17 要求真实试写只影响预览空间；旧测试注入表、仅意图预览及普通空实例均不能满足这项产品功能。九任务盘点、图表/正式发布/真实模型前置的代码依据保存在独审原件中，不重复已交付的 CSV、材料授权或恢复矩阵。

现在用户可在本地记录应用中明确选择已保存内部 Release，单独确认创建私有试写空间，在独立目录分组中选用。原记录表单、预览确认、Worker 和事务控制器把真实 JSON、回执与集合事件保存到受信私有目标，不新增 executor、Grant 或表。业务实例、资源目录和权限指纹保持；选择业务实例会清输入，需要另行填写、预览并明确提交。私有成果及下载、Run/项目历史均标记 PREVIEW，不提供自动采纳或正式发布。

最终资格原件：

- [安装包 API 日志](api-installed-final.log)：6 项 pytest 用例，31.48s；112 条 TestClient/ASGI 响应。
- [安装包页面日志](ui-installed-qualified.log)：1 条 JSDOM 流程，37.51s；70 项页面检查、171 条 ASGI 响应、54 次静态资源加载、2 次 boot。实际确认私有 CREATE→DONE、冷重开/旧 Run/导出、私有→业务选择及迟到回读、项目/工作区 ABA、同账号重连、项目历史导航；撤权后单次403清正文，显式停止元数据读取后单次取消同一排队 Run。
- [55 表页面 oracle](private-page-oracle.json)：全部既有行不变，新增原账本行逐一绑定私有实例/两个 Run/Operation，保存两个真实 `app_previews` 对象；资源/Grant/业务行保持。后续单独确认普通 Run 才新增正常资源及两条派生 READ。API 另有55表和实际插入后故障回滚原件。
- [原业务回归](ordinary-regression-2.log)：2 项源码测试，15.53s；数量不与 API/页面检查或响应数相加。
- [wheel](sim2act-0.1.0-py3-none-any.whl)：957663B，SHA256 `111aa196f23ab165e3ff9eeb088fa307f897fa09f43d224104b01ee5bec59c94`。[141包文件](wheel-verification.json)与源码、实际安装目录逐字节一致；[144源/测试项](source-freeze-final.json)冻结后[0变化](source-final-unchanged.json)。
- Ruff 和 JS 语法通过；focused mypy 新4文件与旧3文件同4条 `tools.py` 历史错误，不能称类型全绿。完整基线 import 检查另有28条历史问题。构建实际使用现有 Python3.12.14/setuptools84、no-index/no-isolation；pin82.0.1 构建未执行。

[作者原件压缩包](author-raw.tar.gz)含所有实际请求/响应/IPC、分期55表JSON、rollback原件、源/安装模块、完整探索失败及被替代的 PASS。[作者 manifest](author-MANIFEST.sha256.json) SHA256 `560d99a38a59827fdca6de5ca311d57ae97641db23d01c7223af5dcfb8065f85`，613文件/63474559B/35个pytest路径链接；[seal](author-SEAL.json)。压缩包10257094B，SHA256 `7afb00828e0ee6d276281b107762cc97ccf8166b2bb455f1ee3698a0e8d56adb`。这是 ASGI IPC 工程资格，并非原生浏览器或原始网络 wire。

修复前66检查页面 PASS 已被替代；其后实际失败复现“新受理 Run 不在旧 projection，首次403丢失停止目标”的 P2。独审两次发现、修复及最终70检查原件分别保留，不提升旧结论。其他失败包括漏fixture、错误状态码预期、错误selector、缺构建模块以及runner提前启动，均在作者档案，最终资格使用以上精确日志。

跨账号 API 与跨私有空间正文前拒绝实际执行且有正向 SQL 校准；跨账号页面只静态。冷页读取发生在撤权前；撤权后仅签本页已核 Run 的停止入口。真实模型0、语义UNKNOWN、人工PENDING；Windows、PG、原生浏览器、真实场景/模型、远端CI、pin82构建未执行。正式 AT17/F2、图表和正式发布未签；可信账户/免费零收费来源仍缺，旧满盘最终独审缺失未恢复。

本轮不访问远端、认证或推送；当前远端HEAD未知。保留最后ACK `a7403b379b1278fd1be533ca21d790f0311244af` 后原12个本地提交，再形成本任务本地提交。无 main、强推、部署或额外费用/凭据/安全权限变更。
