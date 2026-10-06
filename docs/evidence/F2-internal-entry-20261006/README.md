# E19 内部认证 API/UI 集成证据

基线b7895ea/925e560，事前ab02473；正确/workspace/Sim2Act-pb，原work/V5/历史AT02/AT05不改。仅既有只读Release→Instance→持久AppRun原服务接入认证API和页面，[接口与边界](../../F2/InternalEntry.md)。明确INTERNAL_ENGINEERING_ONLY/formal_publication_enabled=false，不开正式发布/部署，0LIVE，无新增Grant/表/业务writer/任意代码/外发/恢复包。

第一轮HTTP测试16PASS/1FAIL：新测试误把原f1.csv期望4.00写成另一合成样例40；实际工具已SUCCEEDED4.00，修独立断言，不改产品求和语义。随后18SQLitePASS/1旧warning3.94秒；真PG18PASS10.84秒。补必要最小CRUD角色完整认证API→审批→实例幂等→enqueue/pause/resume→原worker→结果读取，最终PG专项19PASS/1warning11.17秒；全量结果另记。

独立审查Node VM/minimalDOM实际复现同app迟到create抢回另一instance选择，也指出refresh旧id风险；补捕获instanceGeneration与各await后重验，独立两交错复验保持B/C，新真实HTTP/jsdom两负例通过。初轮主开发20DOM/HTTP PASS；追加跨instance run迟到/撤权控制23PASS；修create/refresh后25PASS，最终包含另一进程实际revision提升/旧页面POST409/显式读回历史结束旧重试的结果另记。每次用本轮owned合成DB重置初态，不动业务数据。

[浏览器阻塞](browser-block.json)：按agent-browser技能正常受保护CLI；默认socket目录只读，改用工具官方可写SOCKET_DIR后SUID helper错误，Chrome在DevTools URL前abort。不--no-sandbox，不改代理/身份/系统策略；无可用受保护浏览器connector/CDP，历史正规升权限同helper路径也阻塞。真实浏览器完成0，DOM不冒充视觉/Win11签收。

`ui-fixture.py`仅为回归初始化合成数据并启动实际production API，无新测试HTTP端点/生产fixture/工具能力。`dom-http.cjs`读取实际UI/HTTP，独立worker子进程执行已接受任务，另进程调用既有switch service产生真实版本CAS冲突；它仍是Node/jsdom，不是Chromium/手机视觉。没有把前端文本或缓存假作新求和；新输入40、真实FAILED与独立结果版本在API回归另覆盖。最终源码/aggregate/独立hash/ServerCI终态另记。

最终actualHTTP/jsdom [27项](dom-results.json)PASS，独立[18PASS/1PGSKIP及UI交错](independent-review.md)；4源码/test hash与最终审查一致。SQLite完整[350PASS/22PG平台SKIP/2旧警告75.53秒](sqlite.xml)。首轮LinuxPG[370PASS/1FAIL/1WindowsSKIP/3旧warnings202.56秒](linux-pg-first-failure.xml)：原AT05真实进程start报API/worker exited，两个日志0字节，未找到异常栈，cgroup oom/kill计数0；配置已抑制。未改原AT05或manage源码，不能断言根因；相同源码[AT05单独重跑](at05-recheck.xml)1PASS/1warning10.72秒。完整PG重跑中，精确ServerCI另核，不删除失败或借skip替代。

收尾发现项目页通用showRun会把内部AppRun的直接result误标“书生运行记录”；修为namespace明确内部只读/0模型/结果版本，并加task/project/token/请求generation迟到保护及命令返回保护。最终actualHTTP/jsdom29PASS，新增真实内部Run主项目页标签与迟到回读负例；原27项完整继续覆盖。因为源码JS变化，需新的精确commit/CI，5462b24只是先前候选源码而非最终视觉或集成签收。

相同Python/API/service源码完整[LinuxPG重跑](linux-pg.xml)371PASS/1WindowsSKIP/2旧warnings229.50秒；原AT05实际进程重新通过，首轮启动失败仍保留且根因未确认，不宣称修复启动器。最终source aaf07f49b3d32eeb360d8cd60a52a4fad22959fd包含项目页JS收尾修正，actualHTTP/jsdom29PASS对应最终JS；[103源码/test/config指纹](source-hashes.json)固定。旧5462b24候选CI37419044735由新push concurrency取消，不当成功证据；新精确CI37419363378进行中。

## E19 精确终态

最终源码[aaf07f49b3d32eeb360d8cd60a52a4fad22959fd](https://github.com/T1doo/Sim2Act/commit/aaf07f49b3d32eeb360d8cd60a52a4fad22959fd)普通push，[ServerCI37419363378](https://github.com/T1doo/Sim2Act/actions/runs/37419363378)/job112125096801 completed/success（2m39s），PG372PASS/0FAIL/0SKIP/1旧Starlette warning100.86秒。19新认证HTTP项含最低CRUD角色审批/实例幂等/队列/控制/worker/结果回读，原AT05全跑；Setup/原生smoke/ruff/mypy21/Report/Cleanup全成功，server stopped。[实际计数/边界](windows-results.json)、[步骤](windows-run.json)、[103文件hash](source-hashes.json)归档。Server2025/build26100/PS7.6.6/Python3.12.10/原生PG17.11，admin=true/EnableLUA1；Node20动作强制Node24注释保留，不替代Win11。

本地SQLite350PASS/22PG平台SKIP/2旧warnings75.53秒；最终LinuxPG371PASS/1WindowsSKIP/2旧warnings229.50秒。首次LinuxPG AT05启动失败保留，单独1PASS10.72秒及完整重跑通过，根因未确认、未修改原测试/启动器，不冒称已修。最终actualHTTP/jsdom29PASS，独立18PASS/1PGSKIP5.50秒及late create/refresh/旧intent复验，5文件hash/静态一致；未独立PG/aggregate/新增29DOM/CI/browser。桌面/手机CSS已实现，受保护ChromiumSUID helper阻塞，真实视觉0/BLOCKED；没有--no-sandbox或系统策略调整。

仅内部认证只读链可实际使用：精确快照确认、独立实例结果版本/历史、持久任务/控制/重开与幂等，不增生产Grant/表/任意writer/发布。内部兼容switch服务尚未接页面，本切片不扩大到通用数据/正式发布批准与部署。原阶段门仍保留；下一真正未完成规格见StageGateReview/接口文档。owned合成API server/PG已停止清理，原work6f688e4/V5/历史AT02/AT05不改，0LIVE/无额外导出。源码/test/config与精确CI一致，文档收尾普通push不重复CI。
