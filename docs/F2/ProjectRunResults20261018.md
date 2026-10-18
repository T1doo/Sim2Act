# 项目任务历史接回原应用成果与人工验收

基线 `2c21d278dbe0d46e05c4ba4cccd473a8edfa4716`，普通开发分支 `dev/project-run-results-20261018`。root为唯一仓库写入者；开工工作区干净、HEAD与远端一致，约23GB可用。保持旧实例、旧证据和已取消门不变。

原V5 F2-T05/F2-T06要求统一使用入口和真实成果可回读。项目任务历史会列出自然应用的内部Run，但详情一律按CSV拼接，出现undefined摘要和没有调用量依据的“0模型请求”；已有规范成果和人工验收只能自行另找应用/实例。本轮修复这一条真实入口，复用现有控制器，不新造executor、Grant、API或成果渲染器。

内部摘要仅对CSV既有精确字符串合同显示数值；其它结构化成果显示诚实提示，不推定模型次数。用户显式打开后，重新GET实例，核项目、来源应用、machineRun/appRun/Release绑定，经现有showApp/showInternalInstance/showInternalRun回到原Run。临时开页围栏覆盖连接代次、项目、工作区、应用和原Run的用户选择；子实例/Run代次仅阻止旧链接续，不使用户的新选择自失效。导航只读，不创建实例/Run、不提交人工验收、不自动下载。

定向资格计划只运行一条正常生成的合成P-A实例结果：3次生成Mock、1次真实Worker驱动的Mock业务执行；全页面真实loopback HTTP/JSDOM，从可见项目历史进入原Run，再明确打开成果、读取既有清单和同Run人工PENDING入口。唯一延迟场景使用真实实例GET响应延迟交付，用户换项目后不得导航或覆盖新范围。另作独立标注的合成CSV摘要精度断言，不计作CSV/P-B后端动态资格。页面全程GET、无新Worker/模型/业务写入；严格比较完整55表before/after。

实际执行冻结 `c3aa1e4fa569e6ea08174e30811f216392b7ccd2`，生产初始提交 `49e0e7b026126ba031141944b15f20e28b4358a7`；两者生产/CJS字节相同，仅补异步Mock响应记录器。1唯一pytest共2次执行：最终1PASS，JUnit104.383s/外层107.198s，29页内检查、9可见操作、33实际API GET与27实际静态资源（60HTTP）。原应用/实例/machineRun/appRun/Release/结果v1与owner sequence0/PENDING精确相符，明确读取清单后核原文、JSON内容与指纹。双击仅一条导航链；一条真实完整实例200响应在换项目后迟到，无后续HTTP或新paint。55表完整before==after，页面POST/下载/Worker/模型均0；所有695执行输入（133生产）零漂移。

首轮在页面启动前因测试观察器FAIL：同步MockTransport钩子捕获0，而实际已走异步完成3次生成+1次业务Mock并读得SUCCEEDED。保留原JUnit51.244s/外54.219s、完整pytest/fixtureHTTP、空mock-wire与原文件清单，不假称首轮原模型线已捕获。仅补原异步handler的透明记录包装，未改生产、预算、业务状态或既有计数断言；第二轮完整记录4次原Mock请求与响应。两轮共8Mock、业务Worker2次、真实模型0。初期静态独审发现的CSV字符串精度与子选择围栏问题在首次冻结前修正，未声称动态复现。

[所选原始证据与独审范围](../evidence/project-run-results-20261018/README.md)。全表相等有实际执行断言与持久每表行数/指纹，未导出全行快照，独审不另开数据库或冒称重算全部行。数据库和重复HTTP JSONL在本轮外部原路径保全，不复制数据库或整树bundle。CSV精度是单独标注的合成renderer断言；本次动态为P-A，P-B及账号重连、同view实例/Run supersession、后台刷新围栏仅源码核查，不冒充实际动态重跑。

Windows/native、PG、真实模型/语义与远端CI未执行；不提升完整F2/R0资格，旧满盘未落盘独审报告缺口未补回。
