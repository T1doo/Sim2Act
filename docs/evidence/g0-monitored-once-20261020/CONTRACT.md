# 唯一一次监测型本地诊断修订合同

授权依据：用户明确同意一次“最多6次模拟调用、10分钟工作+10秒自有资源清理、无真实模型/费用”的本地诊断，并明确把此前过重的64MiB原生硬总量门改为磁盘预算监测，超限即停。此合同替代此前BLOCKED_BUILD_ONLY构建的原生配额/API前提，不代表旧硬配额方案合格；旧证据不改。

基线为`cd3ec8c903e687c49add33174eefacbbcbc6aab1`，原开发分支`dev/production-trial-stages-20261018`。执行前须冻结最小补丁、必要纯单元和独审，正常提交到干净分支，再将精确HEAD/源码依赖摘要绑定唯一grant。根为唯一写入者，独审者仅只读；不假设旧实例或共享文件仍正确。main不改、不强推、不部署、不新增费用/凭据/安全权限，不做第三次PGCI。

1. 原`conftest.env`新SQLite、既有configured三项隔离合成替换及精确MockTransport接线保持；原生产环境默认拒绝条件、审批、真实业务全图扫描、账链、原始wire/response/用量、Run/version/fence都不改。不读取/更新旧过期DB，不恢复旧JS窗口。
2. 最多6次实际Mock收发：Generate3→Source2→Cold1；最多8次Mock方法入口，包括原Source两次同步本地委托。不重试补齐。进入首次G0后所有Mock额度永久关闭；第7收发/第9入口在handler前拒绝。HTTPTransport/AsyncHTTPTransport、DNS、socket连接/监听及MockModel fallback继续阻断，实际InternModel只经原fixture的Mock客户端，无真实模型/网络服务。
3. 原TTL1800秒、run300秒、lease30秒、RPM60秒、原完整七槽预算及鉴权不变。480秒构造前缀/120秒G0保留作更严外层分段边界，整个唯一子进程工作最多600秒；TERM5秒+KILL5秒，固定总候选上限610秒，不重新开清理预算。原期限先到仍按原条件拒绝。
4. **64MiB是采样磁盘预算，不是硬配额**。父进程每0.1秒以内的正常监督轮次遍历唯一新目录的全部已知/未知/嵌套条目，记录逻辑字节和分配blocks峰值；计入该子进程可写regular fd中的已unlink原生临时文件，按inode去重。TMPDIR/SQLITE_TMPDIR在子进程导入前指向新目录。任一数值超64MiB或监测权限/扫描失败即UNKNOWN并停止已核归属自有进程组。SQLite正常删journal导致FileNotFound可跳过。目录采样和普通调度存在延迟/瞬时超量，绝不声称硬上限或完整原生VFS封闭已证明。
5. 不安装原生VFS、不加载第二份SQLite、不要求公开其C API、不启用扩展或改变journal_mode/temp_store、不设置新增单DB12MiB限制。已有Python日志/诊断/控制/receipt writer上限保留，截断/短写/证据失败都UNKNOWN，不删原件腾空间。
6. 停止shim完整委托原`_cold_model_before`的进入、body及退出。首个原DomainError完成原失效/异常展开后保留同一异常作cause，再抛专用BaseException；成功必须完成原第二commit、全图hash关闭及最后stop/deadline检查才抛同一信号。均在W5下一句前退出。确切同一SQLite连接重装authorizer，拒DML/DDL/写PRAGMA及非SQL写API，保留rollback；任何保护拒绝不能冒充原业务拒绝。原其它连接心跳保留，不称全库DML为0。
7. 原`_cold_admission_diagnostic`、命名finite/end/stop、五阶段wall/check/input_key差值及partial/NOT_REACHED原样保存，不重读DB/时钟填补；保存有界cause/context/frame图，无locals。原G0结果或任何失败先写诊断，再做原心跳/客户端/Store收尾；多项清理错误单独追加，不覆盖首拒绝。控制日志另记前缀阶段时间。未完成业务状态标INTERRUPTED，不补拒绝/settle/终态、不续跑该库。
8. 父仅监督唯一新子进程组，信号前核PID/PGID/SID/UID/出生tick；不按名称杀进程、不删未知锁、不干预旧服务。收尾检查整个自有组，不以leader退出冒充全组退出。FD/stat/hash收尾尽力保留receipt，失败UNKNOWN。首末源码/测试输入/依赖hash绑定，工作期间根不再改代码，独审者不执行业务。

通过独审后只创建并消费一次grant；启动、构造、首拒绝或未知失败均不自动再次尝试。若启动前关键保护仍不成立，不运行此窗口，报告精确缺失，停止追加外围保护工程。事后封存所有原始日志、首拒绝/原条件/阶段差值和预算峰值，报告完整SHA、远端、未提交/未推送差异，正常开发分支提交推送。
