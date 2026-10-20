# G0保护程序：实现前策略独审

结论：可以实现标准库独立保护模块及纯单元验证；**目前不能据“4个SQLite文件+RLIMIT_FSIZE+Python文件白名单”证明64MiB硬总量。缺少原生文件路径闭合时，具体启动入口应在产品/夹具导入、运行目录分配及子进程启动前BLOCKED。** 这是用户允许的fail-closed交付，不要求新增权限、服务或改变原SQLite语义来强行可跑。

## 同连接SQL拒写

精确绑定原SQLAlchemy连接及原SQLite driver对象，不换Connection子类、不改五个semantic函数。G0进入时（包含原__enter__首binding）安装authorizer。固定允许SELECT/READ和已核纯函数，其他动作默认DENY；写入/DDL/ATTACH/DETACH/PRAGMA/未知opcode、load_extension或有副作用函数必须拒绝。仅对原事务ROLLBACK开放必要TRANSACTION动作，避免把Store.tx的原回滚也拒掉。callback只返回SQLITE_OK/DENY并记有界标量，不做SQL、I/O、业务callback或异常替换；不能用SQLITE_IGNORE改变返回值后让原业务继续。

SQLite官方 [authorizer文档](https://www.sqlite.org/c3ref/set_authorizer.html) 说明它在语句编译时调用，且连接上只有一个authorizer；执行中的VM不保证重新授权。[官方仓库auth.c当前实现](https://raw.githubusercontent.com/sqlite/sqlite/master/src/auth.c) 在set_authorizer时使prepared statements失效。因此需入G0时重新安装callback，不能只改变旧callback的phase布尔。必须用实际标准库纯SQLite单元验证已缓存UPDATE重用会被拒，不能由master源码推定已安装库的具体行为。

authorizer保持至原Store.tx回滚完成，再由顶层生命周期恢复已知由harness拥有的callback；未知既有callback不能无证覆盖。原Store.tx在db.py:726捕获BaseException并rollback；Store.proof_write_boundary仅在SQLAlchemy执行事件中更新epoch，不能当原生driver写的预防门。

不要把authorizer称为通用SQLite只读沙箱：已处于执行中的写VM/RETURNING、先前打开的可写Blob、backup destination、deserialize、扩展及副作用UDF等需单独排除。指定产品路径静态搜索未见blobopen/create_function/load_extension等使用，旧refused_archive_copies中的backup被本设计排除。[BLOB写接口](https://www.sqlite.org/c3ref/blob_write.html) 可写已打开句柄；[backup接口](https://www.sqlite.org/backup.html) 可替换目标库内容，不能只根据SQL文本事件作保证。有限静态闭包+合成单元可以支持“当前固定路径直接DBAPI SQL被拒”，不支持任意恶意原生代码的隔离承诺。

## 文件总量是当前启动阻塞

[SQLite临时文件文档](https://www.sqlite.org/tempfiles.html) 列出事务日志、语句日志、TEMP库和查询临时文件；随机文件可能位于其他临时目录，且行为可能随版本变化。原Store没有固定这些额外路径，artifact.save_text本身写resources表，但fixture额外JSONL及退出资料仍需有界writer。四个固定DB文件列表不能覆盖原生VFS文件创建；Python open猴补丁/audit不截获全部原生open。[Python审计文档](https://docs.python.org/3.12/library/sys.html#sys.addaudithook) 也不把Python audit hooks定义为安全沙箱。[RLIMIT_FSIZE](https://docs.python.org/3.12/library/resource.html#resource.RLIMIT_FSIZE) 只限单个文件，不能限制文件数量、合计字节或父进程输出。

最小诚实实现：保护模块明示native_io_closure/aggregate_quota证据未实现，启动前直接返回BLOCKED，运行预算0。仍可交付可独立审的文件预算算术、有界writer、有限路径/文件数检查、拒链接和escape、停止shim及独立单元。它们可以被验证，但不能冒充SQLite原生IO硬边界。无须请求新增mount/配额/安全权限，也不擅自改journal_mode/temp_store或用轮询、事后目录总量、删原件腾空间取代硬限。即使未来找到已批准资源，仍需针对其真实硬界限另审；当前不做环境权限探测或分配。

## 停止及心跳

wrapper仅作用于确切第一次Cold原context。成功必须等原enter/body/完整exit及最后期限检查后，立即抛唯一专用BaseException，W5第一句不得进入；原DomainError先完成原展开，再以同一异常对象为cause。其他BaseException、authorizer拒写、资源/observer/cleanup错误均UNKNOWN，不能冒充原业务拒绝。观察器保存最多一个真实diagnostic引用，不重读或补造finite。

当前自然任务由Worker→app_jobs→pa_spec_apps→text_workflows.process_job，实际finally stopped.set()+join2。根据 [Python3.12 join](https://docs.python.org/3.12/library/threading.html#threading.Thread.join)，需另核线程存活；进程组清理不是线程已在父进程收到receipt前退出的替代证据。顶层结束原client/Store，检查所有自有线程/连接和PGID；任一不确定均UNKNOWN。父收尾使用一次共同5秒TERM+5秒KILL截止，重入不重开预算，不因缺证重跑。

建议根执行的验证仅限标准库独立合成：直接SQL写矩阵、缓存语句、rollback、第二连接不受影响；纯fake-context的enter/body/exit成功/原拒绝/异常和W5计数0；fake时钟和自有进程模型共享预算；有界writer边界；缺磁盘证明时导入/数据库/子进程tripwire全部0。不能用这些单元冒称真实G0路径已验证。

本独审只读源码和官方资料；没有产品导入、fixture/数据库/测试/Worker/Mock/PB/G0/真实模型/服务/launcher执行，没有修改仓库。具体代码仍由根唯一writer实施，后续需按冻结字节独审。
