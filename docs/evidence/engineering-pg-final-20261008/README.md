# 最终修复源码完整 PG Engineering — 2026-10-08

本轮冻结 `d85f6f5ceb05972171a84f5aa72f821b39fcb226`，仅执行一次完整回归，
没有更改产品源码、原测试、网页、脚本、工作流、断言或预算。新实例继续使用已推送成果；
原实例及其未提交计划/阻塞日志未接触或复制。

实际 **1591项=原1586项逐项保留+新增5项**。collection、执行集合、JUnit多重集一致：
**1564 PASS / 0 FAIL / 27个原SKIP**，跳过节点及原因与前次全量完全相同。
原七个失败用例及新增五项均在完整集合中。Ruff PASS，mypy47源码文件PASS。
源码、测试、脚本、锁与工作流共284文件，与冻结提交前后及当前字节相同。
[核验](run/verification.json)、[完整JUnit](run/engineering.xml)、[原始pytest日志](run/pytest.log)。

|阶段|实际进程墙钟秒|退出码|
|---|---:|---:|
|collection|1.318|0|
|Ruff|0.032|0|
|mypy|0.215|0|
|完整pytest|1089.253|0|

pytest报告1086.70秒；Ruff+mypy+pytest合计1089.500秒，不含collection、准备、PG启动和清理。
setup221.214秒（20.309%）、call847.252秒（77.783%）、teardown16.810秒（1.543%），
其余框架时间约3.977秒。1200次Store.initialize累计79.756秒，其中env1139次78.621秒。
初始化PG DDL47029次/53.990秒；非初始化PG SELECT1159314次/304.790秒。
指标COMPLETE、pendingSQL0；这些嵌套跨度互相重叠，cursor不含fetch/commit/pool，
不测子进程内部。mypy、依赖与工具缓存已热，观察器开销未单独量化。
[阶段与排名](run/rankings.json)、[SQL与初始化指标](run/pg-metrics.json)。

两个热点仍居前：报告清单DOM call36.030秒、REPORT图DOM28.157秒，
随后整包实际PG双表单16.331秒。当前完整成本包含新增五项及异常观察器；
与前次完整运行的差值不能当作因果提速或回退结论。本轮只复验修复，不进行新的性能优化。

PG17.11使用相同已缓存固定镜像，在唯一自有localhost容器中一次启动。两个输出流均在
docker start -a之前打开，TCP就绪后首次认证连接成功（0.012604秒），没有重启或业务重试。
完整启动/运行/清理日志、镜像、容器状态、命令时间与源码散列均保留。
[启动日志](run/server-attached.stdout.log)、[PG完整错误日志](run/server-attached.stderr.log)、
[时间线](run/timeline.jsonl.gz)、[启动与执行意图](run/intent.json)。

完整PG日志中 **deadlock0**；pytest进程SQLAlchemy异常清单 **40P01=0**。
被动FastAPI观察记录10775次调用，**HTTP500=0、非预期HTTP5xx=0**。
唯一503来自原 `test_source_bound_product_actual_http_dom` 明确注入的
AUTH_LIST_UNAVAILABLE：原Python middleware66–78行与原JS50–52行要求刷新拒绝并清空旧证据。
此处分类仅核对原断言，没有抑制、重试或改写响应。
[完整异常清单](run/exception-audit.json.gz)保留该503和全部其它SQL错误。
其余SQL错误为原角色DDL拒绝42501六次，以及原回滚/绑定负例与SQLite指标负例九次；
没有新的授权行死锁。

子进程并未安装同一FastAPI观察器。全部59个保留夹具日志另行扫描，无ASGI异常、
HTTP500或Internal Server Error特征；原子进程/DOM断言也通过。该扫描不是逐响应状态的
完整捕获，不能把未观察范围写成全局HTTP状态证明。
[日志扫描清单](run/fixture-exception-scan.json)及全部夹具log已归档。

24个实际使用runtime_role夹具的JUnit节点全部通过；另保留原角色负例。
实际激活角色回执证明superuser/createdb/createrole均false、DDL拒绝、业务CRUD路径与撤权验证、
CRUD DDL语句0。四组新增并发回执再次证明不同物理backend、项目先等待、无SQL错误、
200/201响应。[角色与并发核验](run/verification.json)列出精确节点与回执。

前后test schema/role/public表均0；清理前PG Running=true、OOMKilled=false、Error空。
仅在验证owner标签后移除本轮容器及匿名卷，二者均确认不存在；attached退出137来自
明确的rm -f -v清理。104个导出文件逐字节或解压后核对，保存原始与压缩散列，
原log/XML空白保留。原始PG流及阶段日志仍在自有/tmp目录，夹具清理另有记录。
[清理](run/cleanup.json)、[导出散列](run/export-manifest.json)。

只读复算：`.venv/bin/python docs/evidence/engineering-pg-final-20261008/verify.py`。
控制器/异常观察器在启动前已保存散列；其运行会创建新的自有PG，仅供另行获授权的诊断使用。

接回开发分支的最小核心提交是：

1. `2315fea1f803ca45e0cbd5ff3da6a329a40d1a1d`：冷Store继承自有PG schema、保留预检原断言、
   确认完成后租约释放为既定0值。
2. `d85f6f5ceb05972171a84f5aa72f821b39fcb226`：材料列表项目先锁，以及五项回归和热点证据。

祖先关系为 `5c06520 → 2315fea → f904423 → f701159 → 1932200 → 0f11dcd → d85f6f5`。
中间四笔仅为证据提交。最小核心清单不是无冲突双cherry-pick保证，d85文档补丁依赖前面的
证据内容。保持全部已发布SHA的普通快进，追加本轮仅证据提交，可接入精确已测运行源码。
[完整提交/整合计划](integration-plan.json)保存SHA、父提交与文件范围。
完成全量后再次默认读取远端：dev/f1-foundation仍为5c06520，诊断分支仍为d85f6f5，main仍为
6f688e4；实际推送结果以最终Git回执为准。发现他人变更/冲突/拒绝时停止，不force、不main。

现有工作流仅监听dev/f1-foundation的push。证据提交保留[skip ci]，按
[GitHub官方push跳过规则](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/skip-workflow-runs)
进行普通开发分支整合，不派发新CI，不修改工作流或安全设置。

LIVE0/MOCK，无真实模型、Windows/native/Edge或新CI执行。Windows900、Edge240、Node150
源码预算未改；当前Linux完整诊断已超过900秒，不能关闭Windows容量缺口，**NO_GO保持**。
当前原生完整阶段、受保护Edge尾段与Win11首次使用证据仍缺，F1/F3/R0或owner验收不因此签收。
