# E19 内部认证 API/UI 集成证据

基线b7895ea/925e560，事前ab02473；正确/workspace/Sim2Act-pb，原work/V5/历史AT02/AT05不改。仅既有只读Release→Instance→持久AppRun原服务接入认证API和页面，[接口与边界](../../F2/InternalEntry.md)。明确INTERNAL_ENGINEERING_ONLY/formal_publication_enabled=false，不开正式发布/部署，0LIVE，无新增Grant/表/业务writer/任意代码/外发/恢复包。

第一轮HTTP测试16PASS/1FAIL：新测试误把原f1.csv期望4.00写成另一合成样例40；实际工具已SUCCEEDED4.00，修独立断言，不改产品求和语义。随后18SQLitePASS/1旧warning3.94秒；真PG18PASS10.84秒。补必要最小CRUD角色完整认证API→审批→实例幂等→enqueue/pause/resume→原worker→结果读取，最终PG专项19PASS/1warning11.17秒；全量结果另记。

独立审查Node VM/minimalDOM实际复现同app迟到create抢回另一instance选择，也指出refresh旧id风险；补捕获instanceGeneration与各await后重验，独立两交错复验保持B/C，新真实HTTP/jsdom两负例通过。初轮主开发20DOM/HTTP PASS；追加跨instance run迟到/撤权控制23PASS；修create/refresh后25PASS，最终包含另一进程实际revision提升/旧页面POST409/显式读回历史结束旧重试的结果另记。每次用本轮owned合成DB重置初态，不动业务数据。

[浏览器阻塞](browser-block.json)：按agent-browser技能正常受保护CLI；默认socket目录只读，改用工具官方可写SOCKET_DIR后SUID helper错误，Chrome在DevTools URL前abort。不--no-sandbox，不改代理/身份/系统策略；无可用受保护浏览器connector/CDP，历史正规升权限同helper路径也阻塞。真实浏览器完成0，DOM不冒充视觉/Win11签收。

`ui-fixture.py`仅为回归初始化合成数据并启动实际production API，无新测试HTTP端点/生产fixture/工具能力。`dom-http.cjs`读取实际UI/HTTP，独立worker子进程执行已接受任务，另进程调用既有switch service产生真实版本CAS冲突；它仍是Node/jsdom，不是Chromium/手机视觉。没有把前端文本或缓存假作新求和；新输入40、真实FAILED与独立结果版本在API回归另覆盖。最终源码/aggregate/独立hash/ServerCI终态另记。

最终actualHTTP/jsdom [27项](dom-results.json)PASS，独立[18PASS/1PGSKIP及UI交错](independent-review.md)；4源码/test hash与最终审查一致。SQLite完整[350PASS/22PG平台SKIP/2旧警告75.53秒](sqlite.xml)。首轮LinuxPG[370PASS/1FAIL/1WindowsSKIP/3旧warnings202.56秒](linux-pg-first-failure.xml)：原AT05真实进程start报API/worker exited，两个日志0字节，未找到异常栈，cgroup oom/kill计数0；配置已抑制。未改原AT05或manage源码，不能断言根因；相同源码[AT05单独重跑](at05-recheck.xml)1PASS/1warning10.72秒。完整PG重跑中，精确ServerCI另核，不删除失败或借skip替代。
