# 作者范围复核（不是独立验收）

冻结源码 `645e49479974fa033a19028e195304108afd51b8`，基线 `0ec1f291d51356d3968c6761d7d80b803e97a65b`。DAG P2 的原独立候选 `3b3534ca76fe05eea4525a1e960c430817310dd9` 不修改、不合并 dev；在本分支显式取入其源码059/4c为 bd4c549/e8c3678。唯一冲突处将已有 wire_proof 保留，并采用整回执 fingerprint 校验。独立审查仍由原第二审查者进行。

核对原 V5 §9.1–9.4、ColumnBindingPatchPlan、DeliveryGraphIndependentContract 和 IntegrationContract：原 PLANNING_ONLY 断言属于原计划 API；用户后续显式授权本受限执行扩展，没有发现禁止本次实现的合同条款。人工锁、PROJECT/SEMANTIC不确定性阻断、当前权限/来源/图锚仍通过现有 build/load_plan/binding 路径消费，不由客户端接线自授可信上下文。不存在新增表、身份、Grant、公开锁写入口、业务权限或并行运行器。

输入只接受三个固定语义端口、各两个服务端允许来源。JSON允许列表同时检查 source/ref/field；同为string的hash/resource_id不可互换。客户端不能改节点、循环、executor/schema或depends_on。aggregate→preview验证屏障固定；report从编译出的实际输入自动生成预览/聚合前驱集合。只支持该固定工程能力，不声称通用增量规划或任意DAG。

默认无wiring_patch的请求dump省略该字段，compile出的旧manifest/receipt结构保持；显式空列表形成带wiring的默认新计划。原计划/运行接口继续保留。读取新允许列表采用 `/options/wiring` 两段路径，避免占用旧合法 `wiring-options` request_key。专属回归确认旧键仍可读。

接线进入不可变definition、wiring快照及plan_fingerprint，exact confirmation链接该指纹，实际intent和receipt保存input_sources及实际父回执指纹。恢复逐步重新验schema、source hash、授权、图锚、整份intent/receipt/final证明；合法已提交步骤不会重执行。既有P2 commit_guard/严格类型防护均保留，另以接线计划重测真实wall deadline及count=true/1.0。

界面在原区域加载server允许列表、核options摘要与closed ports；提交计划前再读当前图锚。未决接受保持原键/选择/指纹并锁住控件。新方案清除旧确认，已保存计划/实际回执读回复核来源和前驱。项目导航generation/ABA、源撤权清除证明、冷历史读回原驱动继续覆盖。Node/jsdom只发自有loopbackHTTP，不是原生Edge证据。

阶段错误透明保留：最早37项阶段中surrogate由httpx发送器拒绝，后改为escaped JSON到达服务器；本轮阶段67 PASS。新旧键回归初次1FAIL2PASS因作者误把POST的cached:false元数据纳入GET比较，修正后3PASS。首次PG最终269项67PASS202ERROR、0测试断言FAIL：pytest basetemp误用自有PGsocket父目录导致socket被清空；原始日志/来源哈希保留。停止自有服务器并确认其匿名卷清理后，另建私有socket根与不同测试目录；在同一冻结源码重新定向验证。这些历史结果不冒作最终通过。

最终双数据库/JUnit/加载源码与清理终态见本目录README与summary。独立审查、Windows/Edge、真实gold、完整P-B、人工签收、正式发布未完成；保持LIVE=0、semantic UNKNOWN、owner PENDING、publishable=false，原Windows900/Edge240/Node150不改，无新CI、强推、dev/main合并或部署。
