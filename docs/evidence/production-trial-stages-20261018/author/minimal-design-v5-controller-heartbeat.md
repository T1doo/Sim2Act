# 原controller心跳跨新journal事务的接线

run5在89d612fb冻结：gen3/Source批准claim和Core请求正常，Source首actual InternModel→MockTransport已收到完整body/known1000；接收后的lease过期，Attempt REJECTED_KNOWN、原Run未成功。275.93秒首节点ERROR保全，已知usage/body/capture均保留，不自动恢复/重发原key。

新增journal reserve/marker/receive为独立事务，原NS controller已有的同步renew只在原边界，尚未覆盖这些接线边界。最小补充仅把原NS _heartbeat_state沿已有request_captured私有调用传入new business continuation；固定模块调用原Store.heartbeat和原publish_sync_renewal（提交后才发布），非新callback注册/Grant。仅新模式NS执行，旧公开sender/default/PATrial及GA不调用此续租。

每次续租均same-binding原Store/engine/worker、原30秒（新_binding严格worker.lease_seconds==contract30）、原fence，running_only=True，deadline=min原node Run期限、contract Run300、原expiry)，停意图和时间在HB前后均重核。原Store.guard/CAS要求原lease仍有效，不能复活过期、忽略cancel/pause或扩大execution deadline。续租写入/发布不提供send权，之后原controller及journal/source guard全部照常；known receive先保存，后续续租失败携原body/usage拒业务。

边界为已确认没有原journal key之后reserve前、reserve后marker前、marker后原guard前/后、有效receive提交后返原parser前。已发现prior分支保持不续租、不返回可重放body；不宣称priorNone与并发reserve之间的CAS duplicate race绝对零heartbeat，任何duplicate仍无新IO/业务重放。

同片还把新P-A plain/pa_use路径刚完成bound的已验证Release复用既有_stage_instance_after_bound；只testSQLite/完整实际新gen3标记/精确P-A/无correction、logic、PB、extract，epoch无写、原owned current instance/release scalar和末端epoch一致。后续完整材料/Goal/recipe/phase/gen3/cold-source2照常核。旧PB分支和资格条件保持原路。

外session guard只观察原Store.heartbeat的成功返回，记录原请求lease_seconds<=30、deadline、owner和线程，既不模拟成功也不改返回值。仍4唯一资格，分两个独立fresh DB测试进程并行执行链A/B与单请求C/D，减少等待；每组有独立原件、JUnit、输入和guard日志，均冻结同SHA。真实模型0，原19/12/8/9不重跑，旧错误均保留。
