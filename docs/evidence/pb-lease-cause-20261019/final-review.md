完整 P-B 最终独审结论：NOT_ACCEPTED。产品源码基准9fbcb6a4e682a09f916b4561795f000c609aea10；实际测试修正/接续版本84fde1b6a5724c57ce0fa68b868ff82e445ed1d8。二者src、scripts、配置/lock文件逐字相同，84f只修Cold测试的实际draft指纹绑定。没有通过延长lease/Run/总合同、写Grant或改资格/账本锚点取得通过。本轮封存截至实际失败，不再以新链或旧失败重跑补签。

最终original-cold-continuation-command实际exit1，外230.645065s，15:01:50.868181→15:05:41.512885UTC，2113选中输入before/after逐项相同（714tracked+1399依赖）。它是9fb原五槽成功前缀的只读backup接续，不是单次完整pytest。外部harness SHA256=d5dce1203e8295760e79e8288cafe884399805f8dc6a6e0a707a2b3e2d882a4f，与预启动记录/实际脚本一致；原Cold尾部只有三处跨进程计数修改，实际执行尾字节等于此前独审版本。

实际结果及剩余阻塞：Cold run_4ed4f78b22df49edbf752dac24b40b3d=RUNNING，version/fence均1，error=null、result=null、public steps=[]；context requests/tools均0，Cold无Attempt/无新增Mock日志。原failure-observations明确为natural_spec_runtime:733进入首个本地读取路径 → pa_spec_apps._advance_local:1371最终commit_guard → production policy → gate._run_context:934原身份/版本/取消/finite-lease复合守卫拒绝。具体未关闭工程点是Cold首个本地read提交未能通过原租约证明，Cold执行/结果与同Run人工验收未贯通；不是需要放开访问审批。

结束行Cold.created_at=1792422212.237031、lease_until=1792422319.9024134；原Run300截止=1792422512.237031，总合同及Approval原expiry=1792422750.2994251。命令结束在1792422341.512885，已过结束行lease，尚未到后两截止。内部guard精确比较时刻、最后真实heartbeat返回、事务持有时长、SQL/CPU量均未采集，不能由墙钟差代替或借用旧链span。该standalone harness没有pytest autouse内部租约观察fixture、没有外部计时plugin或closed线程快照；不能补称观察闭合或性能因果。这里只报告原trace及实际结束行，不重构其未记录细节。

有限已确认功能事实要单列保留：

| 路径 | 实际证据与边界 |
| --- | --- |
| 9fb Generate→Source | Generate PARTIAL/3RECEIVED；Source SUCCEEDED/2VERIFIED，实际5Mock=3+2、0真实模型；citation PASS，semantic UNKNOWN/NOT_RUN |
| Source提取与目录 | 原实际提取/同key精确重放无新增发送，两个原始包/规范哈希及provenance核验、四项拒绝、Release/Instance与目录NATURAL_PB原断言通过 |
| 84f Cold输入与防重复 | 新client真实draft GET200/指纹等于原candidate_fingerprint；显式新材料+Goal review/submit，cachedFalse→True且同一Run余响应完全相同；原Cold阶段审批和真实Worker.once已执行 |
| Cold使用结果 | 首本地read最终guard拒绝，无步骤/结果/Attempt；Cold SUCCEEDED、owner-review PENDING合同、两Cold请求/readReport、最终7accepted/1RPM与22归档断言未到达 |

原9fb完整测试仍1FAIL（Cold前测试KeyError），上述前缀不能被改写为整项PASS。84f已修正确字段并实际走过Cold提交，消除了该测试字段错误，但没有消除本次产品执行阻塞。新的公共结果视图owner_acceptance=PENDING只是失败视图字段，不等于已完成owner-review入口合同或人工验收。

接续的来源与保全核对：verified-prefix要求原typed合同/Approval/key/account/quota、当前软件和权限、expiry、5槽全accepted且不halt，stage为3Generate+2Source；Source ID等于原ended导出唯一SUCCEEDED且两Attempt VERIFIED，原提取缓存重放前后snapshot不变，旧Source两包与原五条Mock日志后两条逐字相同。当前原DB hash与ended导出先匹配后RO backup；result确认原DB SHA308b97701279efe071ab44d49db695a747f0fd47f517ada97be43efe8cfd0a39始终未变。接续副本的结束导出SHA918af2e72437f861812fc8239e473abf4536190e15f1f05fe22a166f9194e809声明只读导出前后不变。本独审核JSON，不连接或查询DB。

独立逐字段比较接续结束导出：原五个Attempt完整行和原两个Run完整行与9fb原导出完全相等，Source仍SUCCEEDED，五个known usage仍各100/900/1000；只新增Cold Run，无Cold Attempt。旧5与新增0分别计数，不能将原五槽当新发送、也没有完成7槽。原总expiry、原Grant、原Run时间/lease/状态及ledger没有为接续重置；只重建原测试三种合成standin与有限Mock，真实HTTP硬拒，真实模型0。LIVE模式行仍只是合成生产分支标记，不代表真实账号/许可/语义接受。

质量范围按准确执行SHA和字节桥归属，不能称84f全套重跑：

| 实际执行 | SHA | 结果 |
| --- | --- | --- |
| authority-query-focused | 9fbcb6a4 | 5PASS，外87.164974s；原始JUnit/输出/2113稳定 |
| mypy src | 9fbcb6a4 | 113源文件PASS，外74.872257s |
| 指定变更Ruff | 9fbcb6a4 | 11文件PASS，外1.922562s |
| cold-test-fix-ruff | 84fde1b6 | 修正的单个测试文件PASS，外0.745831s |
| completed-source-frozen-command | 84fde1b6 | 实际SUCCEEDED/2VERIFIED来源副本上0send结构helper PASS，外18.256091s、2113稳定；完整binding等价、真实matching Grant撤销被拒并rollback、Attempt/DB字节不变 |
| 最终Cold接续 | 84fde1b6 | exit1，0新增Mock，完整P-B NOT_ACCEPTED |

9fb→84f只测试主函数4个新GET/断言赋值和一个指纹表达式修改，所有产品/配置/脚本字节一致，其他focused用到的代码保持，前述源类型/Ruff证据仅按这些实际等值路径适用；不是84f又跑过113mypy或全部恢复矩阵。第一次completed-source-command@9fb虽然0send结构断言完成、exit0，但作者运行中改测试导致unchanged_inputs=false，只该测试after字节等于84f；原件和input-drift说明保留，明确不是冻结PASS，未用于最终门。

历史材料保留与计数：prior-review-seals-index.json列出21份既有独审manifest哈希，旧seal未改；所有历史fullchain FAIL、受控中断、未冻结编辑/序列化/setup/调度失败仍按原结果，不被本报告或短门升级为PASS。作者analysis中的44条direct transport记录已按阶段原JSONL逐条计数；另6条没有独立transport文件的已收前缀Attempt证据、1条queued支持脚本Mock证据分列，总51为混合证据来源的历史累计，不是同一条成功链51次。最终Cold新增为0，不能拿旧Source或旧ordinary请求填Cold。

所有相应源码静态意见都只针对窄差异；原权限、durable intent/owner/fence/版本/撤销到期/provenance保护未因验证失败放宽。本最终结论不覆盖真实模型/真实账户资格、真实语义/人工场景、PG、Windows、原生浏览器或远端CI；未执行的项目不能称通过。旧满盘未落盘的独审报告仍是已知缺口，本报告未补回或补签。发布/部署/费用/凭据/权限变更均不在本子任务；Git远端推送、最终文档commit及未提交/未推送差异由唯一主写者另核，本审查未网络访问或认证push。

本独审仅只读Git/source、stdlib AST/JSON/XML/字节哈希和复制到新的84fd-final-terminal，没有导入产品、运行DB/测试/模型/网络、修改产品/测试/Git或旧seal。final-runtime-audit.json、原命令/输出/输入、prefix证明、实际执行Cold尾/trace、结束行JSON、准确源码与历史质量原件均收录manifest；作者预封README/analysis/bytebridges/身份记录作为带哈希的当时快照收录，不冒充之后归档或推送已完成。完整P-B仍NOT_ACCEPTED，有限Source/提取/目录与Cold提交防重复事实已确认，剩余工程阻塞必须如实交付。
