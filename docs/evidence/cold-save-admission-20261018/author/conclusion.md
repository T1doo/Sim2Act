# 本次一次fresh mock整链通过；范围限定于最小Cold SAVE修复

源码fd96df814e8c0fb6db6651ce77eb484951240ecc，基线f89f8f4431a63e22a9f067cd74e3bdd4051d84ea。
新源码1生产文件改变、137生产blob未变，另1测试文件仅解耦前缀依赖。

唯一fresh命令2026-10-18T17:30:51.046278+00:00开始，17:39:53.983473结束，
outer542.936816361秒/exit0，900秒timeout未触发。4个原节点全部PASS，顺序B→A→C→D。
B的9个原窗口全部在本轮实际gen3后执行，来源THIS_ROUND_ACTUAL_PREFIX_ONLY、clones=false；
A保留完整本轮generate3/Source2/Cold2及原同Run结果、artifact、PENDING owner入口断言。
C/D分别证明错误业务schema拒绝与同URL第二Store隔离/foreign SQL0/各handler1无重发。
本轮9次合成InternModel+MockTransport adapter入口=整链7+负向2，真实模型0，旧请求重放0。
652输入/138生产与runner/guard前后hash均无漂移，原19/12/8/9矩阵重跑0。

Cold Run run_f4b0367077c4438183b90460d173ea66的SAVE两个guard被明确记录到同一事务：
1220写前guard2.287506074秒/3681SQL/threadCPU2.28478，write epoch195；
1261写后guard2.779829540秒/3713SQL/threadCPU2.77929，write epoch201且新读段有效，
guard内epoch未变。写后guard完成仍余23.162010670秒lease。
Cold事务到commit事件11.315882687秒/16370SQL/threadCPU11.31160，
BEGIN IMMEDIATE driver等待0.000381509秒，commit事件时仍余18.678297281秒lease。
这个事件早于driver真正commit完成，不冒称测得完整driver commit时长；A的真实结果/owner
断言另证事务实际完成。所有controller check均无error。Source亦完成同样写后新读段及SAVE。

旧失败fixture的原31.750393177秒检查没有完整caller，不能事后认定唯一布尔原因或所有耗时。
本次两个只读诊断没有复现该完整31.750秒；它们显示主要CPU在bound/lineage，组合读段减少
104条SELECT。fresh新记录证实写后重新完整证明、原lease内保存成功；一次mock通过不是负载
或普遍性能保证。原f89未合格检查点及全部失败原件保持原样，不改写为通过。

定向组件先在明确标记的旧失败合成副本执行9窗口；首次脚本随后构造旧试验Worker时因软件
指纹改变而exit1，正确拒绝保留，旧合同未改。补充命令不重跑9窗口，用合法generic Worker
（未安装旧pa_trial）核旧SAVE入口及新_source_reads中的原guard均Stale worker lease拒绝，
每次55表不变；源封存DB哈希保持c234d6fd4134cb2e41c6483bfc21024fbeda2dea78940d45e09e09e2f4db21e9。
它们不是fresh资格替代物。暂时断连后的原命令状态先查明exit0/无在途进程再继续，未重复启动。

累计历史按原始JUnit计，旧14=5PASS/8ERROR/1fixtureFAIL，本次新增4PASS，共18=9PASS/8ERROR/1FAIL；
旧33次mock+本次9次=42次。诊断及组件脚本不冒充额外pytest PASS；首次组件脚本exit1单列保留。

真实API仍是独立条件：用户已有授权和配置key存在/非空事实，余额、强制零新增费及真实source/
controller受审安装未证实；本修复没有触发真实请求或新网络探测。Windows/native、PG、远端CI、
真实语义/人工验收、新PB/AT10与本片浏览器重验NOTRUN。旧满盘独审报告NOT_RECOVERED。
当前只交付普通开发分支上的最小修复及本轮mock资格，不签整体F2或LIVE。
