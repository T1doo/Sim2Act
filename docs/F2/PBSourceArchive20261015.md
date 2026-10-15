# 原 trial 来源请求/响应归档与独立冷 Store 读取（有限离线交付）

**完整回归失败：388 PASS / 1 FAIL / 0 ERROR / 0 SKIP，389项全部执行，RC1。整体 NOT_ACCEPTED。** 本文交付有限离线实现与真实证据，剩余集成阻塞见下文。

基线 `fd0ac2198986f201e05924104e7f7a7bb0908769`；开发分支 `dev/pb-source-archive-20261015`。原来源归档代码提交 `8737ee41d025af542a2664b867288db476a8c019`；追加有限P-B Cold复核候选 `259d666da7a230da1749efb9a1d63d8a16271d65`；最终冻结源码/测试 `056fb5a4796ba91cd5c2bcd12628bd06d2eae9ca`。本轮继续原 F1-T06/F2-T03/F3-T05 与 V5/DeliveryRemainingChecklist 的实际来源归档缺口；前批项目局部列修改、受影响应用重验、取消和原 key 恢复已完成，不重复实现。

## 具体合同

新增 `natural_source_archives.py`，只对 test_only SQLite 与显式 MockTransport 的既有自然应用 Worker 生效。实际原请求序列化 bytes 在原 reservation/Attempt 事务内归档；响应归档的是 HTTPX 实际解码的 body bytes，区分完整 body 与已接收 prefix，不是 TLS/HTTP 原始网络包，也不归档 header、连接 URL、配置或凭据。旧 canonical ASCII response 与新解码 body 分别计算 hash，不以 canonical 重建冒充收到的原 body。

复用既有 `delivery_graph_requests` paired seal 命名空间，两个 family 为 `natural_source_request_body.v1` / `natural_source_response_body.v1`；以实际 Run、Attempt、principal、project、runtime 为作用域，固定 provenance=OFFLINE_MOCKTRANSPORT。private body 保存上限32768 bytes，过大/空体明确标记；网络中断只记录已收 prefix 的长度/hash，不声称完整响应长度/hash。缺失、不完整或过大归档不能通过来源解析。

写入前先从实际 Run/Attempt/reservation 读取标量证明归属与原 wire hash/size；响应还检查原 request paired seal。相同内容/完整性重放只读，冲突拒绝。新请求只允许原 STARTED 且 MODEL_RESERVED 事件前；新响应只允许 STARTED/RECEIVED；历史完成对象不补造归档。paired rows 与只含服务器 Attempt ID/归档摘要的事件同事务写入；事务失败不产生部分配对。

正常接收时，新响应归档与原 Attempt.RECEIVED/canonical response/NS_RECEIVED 在同一原事务中完成，不改变原 response 字段形状。解析失败、空体、超限与网络中断保留可证明的已接收事实，不把 UNKNOWN 升级为成功；取消/撤权的已知响应保留 REJECTED_KNOWN/usage，但仍拒绝业务提交。只在旧 asyncio TimeoutError 的既有分支恢复原 parsed response；网络异常不新增恢复成功路径。请求归档写失败则预约、Attempt、配对、上下文和事件全回滚，未发送；响应事务写失败则整个响应事务回滚，原预约/请求归档/STARTED UNKNOWN 保留。该故障下收到的 raw 未持久化，明确 `NOT_PERSISTED_IN_EXPLICIT_WRITE_FAILURE`，不称所有收到事实均可保留。

## 原 key 来源解析与 HTTP

`resolve_trial_source` 仅接受精确 PBTrialContract/原批准 key。一个只读事务内重新检查身份、项目、完整 trial、当前软件资格、材料/完整 Goal 授权、原批准输入/撤回/期限、原预算和 stage keys、成功且未取消的 source Run、完整 source 证据、实际抽取实例与原 extraction key/编辑 Recipe、不同 cold 材料和完整 Goal、两个 VERIFIED MOCK Attempts/原已接受 known source 槽。读取 body 前完成 scope/权限检查；返回前重新检查收集的 authority、原批准和真实期限，不跨事务缓存授权。

归档必须刚好对应两个原 source Attempts，request/response paired seal、事件锚、wire hash/size/字符长度、原预算 reservation、解码 JSON、旧 canonical archive/usage/settlement 全部一致，拒绝缺项、跨 Run/身份/runtime、篡改和模式翻转。成功私有结果才含2对 body；HTTP GET `/api/projects/{pid}/natural-trials/{key}/approvals/{approval_key}/source-archive` 仅从原 trial/批准读取摘要，返回 `ACTUAL_MOCK_ARCHIVE_NOT_LIVE_VERIFIED`，零新模型请求/预约/项目写入，live_allowed/dispatch_authorized/formal_publication_enabled 恒 false。没有请求方输入的 resolver、Run/Attempt、证据或授权覆盖。

生产 `LivePBSourceContract`、account/fee/sender 注册路径不变，未接入此 MOCK reader，不能翻标签获得 LIVE 资格。本轮不是供应商数据库归档或真实付费/免费调用许可。

## 实际验证

历史7c冻结 SHA 独立定向批20 PASS/0 FAIL/ERROR/SKIP，实际 RC0、519.46秒；XML SHA256 `b60a99ba49916be9041db4fc8c0c2814eab663c02bc2b7f8f13c8b1ef740776f`。该定向批的498文件 before/after/复制源码/当时root/Git字节经独审闭合，不称最终056源码已跑过同批。11项 capture 边界与9项实际 Worker 用例。实际正链 Generate3+Source2 共5次 Mock dispatch，4个预约间隔均≥60秒，Run300/lease30保持。新独立 Store engine 在同 SQLite 上读取；不是独立 OS 进程，也没有 cold 模型派发。原 key GET重复只读、所有表字节/行 hash 不变。19项内部拒绝检查属于该1项 pytest 用例，不额外累加为测试数。

8项实际 Worker 故障为 invalid_json/empty/oversize/network_prefix/cancel/revoked/request_write_failure/response_write_failure。前6保留原预约/可证明收到事实，零 typed 业务结果；后2覆盖实际写后抛错的事务回滚。故障夹具走实际 Worker，但非原 trial 费用总账，不扩大到实际账号或真实费用保证。

056同SHA质量：fullsrc Ruff PASS，10 changed Python Ruff PASS，产品/夹具Node语法PASS。full mypy RC1/86源文件，仅status_report.py3条与tools.py2条原基线错误，逐行相同，新增0。85模块pin `eeb3d4445db81d648612d976d91605aca1f4205a5a6ee13d5aa5c9e35af7ec83`；原anchor/ANCHOR_HASH/CHANGED/config排除与唯一literal zero64归一化不变，独审已核。

056完整批 **388 PASS / 1 FAIL / 0 ERROR / 0 SKIP / 0 deselected**，389 unique，RC1，6149.81秒。新30+原359精确顺序、原359测试字节保持（内含20来源归档与原339）；collection/XML逐项双射，无unnamed条目。499文件before/after/执行副本/root/Git相等；PROCESS_EXIT/RESULT退出码一致。XML SHA256 `cd6c3e82483bba6c65bc39829ec1110b8dc099f90828de684ea6d0197cfb8d4e`，RESULT SHA256 `06aeb439d74151ac8759f06bd581ddbbca6cbdb00464151e9a22b790ee9194be`。本批新30结果 `{'pass': 30}`，新20结果 `{'pass': 20}`，不和旧探针累计。旧7c完整358PASS/1FAIL/0ERROR/SKIP、359项/RC1、6230.71秒的独立失败历史保留，不与本批拼接。

## P-B Cold同一只读段的有限复核优化

旧7c失败详情在FULL7C_FAILURE.md及原完整批/终态独审中保留：Cold首槽的reserve/fresh/settle三次完整准入持续9.57/7.13/7.34秒，结算重验时已跨最后已证实lease，正确拒绝并保留6槽KNOWN6000/HALTED；Cold第二槽未发送。不把全部耗时归因于锁或CPU。

局部变更仅在test_only SQLite、PBTrialContract的cold且ordinary spec_task（无human_correction/logic_check/pb_use/pa_use，Release无natural_logic_source）生效。先保留原完整bound→read_release/来源证明，在同一个真实SQLite事务的连续无写读段，锁定fresh当前Instance并检查身份/项目/source_app/runtime/release/revision；原owned_release_pointer先权限检查再读完整Release，immutable_release_pointer重验当前消耗的批准及snapshot/fingerprint，完整fresh row必须与刚验证过的row一致；bound前捕获write epoch，读段末尾再次相等。调用方Store.tx使用SQLite BEGIN IMMEDIATE，helper另外核driver真实transaction，不靠SQLAlchemy autobegin标记猜快照稳定；任意实际写入即拒绝复用。没有跨事务或跨预算阶段缓存授权。

其余路径仍走原lifecycle.instance完整证明，后续P-B原source/Generate/抽取key/完整Recipe/授权指纹门保留；admit全函数AST不变，含postfee _approved、当前Run/版本/fence/取消/真实lease与期限门，预算/300秒Run/30秒lease不改。不是通用执行器重写，也不保证任意负载下30秒容量。

新增30项仅边界证据：18实际SQLite metadata/approval/write/真实事务检查，11隔离sentinel分支选择（先完整bound，全部fallback保留），1真实metadata revision1→2交接原StageApproveInput拒绝。提供给helper的先前验证row及分支上游为明确合成，不能当完整P-B来源证明/PG证明。WIP先15PASS；扩展29PASS/1FAIL因新fixture合同缺身份字段、在entity读取处先失败，修正仅fixture后30PASS/RC0，499前后/复制源码封印保留。随后Ruff只合并import；完整056批覆盖最终字节。上述探针不累加389，原完整P-B七槽在新完整批重新执行。

## 当前完整批失败与具体阻塞

- `tests/test_project_natural_revalidation.py::test_late_project_change_no_partial_save[peer_version]`：failure。

项目peer_version用例实际在发送前失败，sent=0，版本修改callback未执行，因此预期竞争未得到本批验证。零typed结果/既有两Release保持的前置断言通过，不称完整用例通过。既有公开观测：目标Run最后成功同步heartbeat续租后，下一次主heartbeat持续68.57454565004446秒并报Stale worker lease，目标后台3次SQLite code5。BEGIN等待时间、source_scope分段时间、失败Run最初deadline均NOT_RECORDED；不能把68秒归因于纯锁等待或CPU。相关流程源码虽与旧7c相同，旧批同例PASS不能替代本批FAIL，也不能据此排除本次变更的性能影响。

现有project.load_plan已有同连接/事务/write epoch范围缓存及授权重验；独立只读检查尚未找到可安全省略的完整项目权限/依赖证明。该心跳/租约集成失败仍未修复，具体瓶颈未知。未延长lease、跳过保护、跨写缓存或重启测试掩盖失败。精确公开日志时间线及缺失测量见integration/fix-pb-cold/PEER_VERSION_EXISTING_LOG_TIMELINE.json。

本批PA实际MOCK七槽用例PASS且回执完整：Generate3/Source2/Cold2，7预约、全accepted/KNOWN、7000 tokens、envelope 48354、六gap最小60.093159秒。仅该链的工程验证通过，完整389仍FAIL。
本批PB实际MOCK七槽用例PASS且回执完整：Generate3/Source2/Cold2，7预约、全accepted/KNOWN、7000 tokens、envelope 48354、六gap最小60.067355秒。仅该链的工程验证通过，完整389仍FAIL。

本批两次CHECK各1次领取并SUCCEEDED/fence1，Run300/lease30/maxclaims3保持。HTTP/JSDOM8例PASS：119检查、143操作、871请求、189资源、9启动，资源全200。第三个七槽用例仅原Store工程测试，节点状态 `pass`。

本批来源正链再次5次Mock派发、19内部检查通过，四gap=[60.08040952682495, 60.07639837265015, 64.20308589935303, 63.8285870552063]；独立新Store只读且全表hash不变，8项实际Worker故障回执逐一映射本批PASS节点。response事务写失败仍明确raw未持久化。全部指标取本批真实文件，无新probe。

独立审查与原始失败日志见[证据索引](../evidence/pb-source-archive-20261015/README.md)。真实书生/Intern及其他真实模型API调用 **0**。

## 失败历史与边界

终态独审曾将056输出误写至旧FINAL_7C_TERMINAL_CHECKS.json，覆盖前原hash未记录，不能证明原字节恢复。误写056副本单独保留；7c审查JSON依据封存7c结果/先前审查输出重建，显式RECONSTRUCTED_REVIEW_RECEIPT，非原件。纠正说明/实hash与重建副本均封存于review；原7c RESULT/XML/父audit/原审查MD、产品源码和测试未改。新056审查另存正确文件。

原始失败均单列保留：系统python缺pytest为setup NOT_RUN；初始 capture 7PASS/1FAIL 因测试错误期待 MODEL_OUTPUT_INVALID，而原 strict JSON 行为为 INVALID_INPUT，修正测试不改产品错误语义；后续8PASS只代表当时探针。独审发现并修复4项P2：实际归属标量验证、返回前真实期限、网络异常保持旧UNKNOWN、空体事实留存。最终11项capture与20项Worker组合另列，旧FAIL不被覆盖。最初mypy2新增Literal类型错误与Ruff zip/import错误的输出保留，均已修复。进度辅助脚本错误假设pytest截断目录名导致AssertionError，属于观察脚本setup，未重启测试、不是访问拒绝。

本批曾有exec-server transport disconnected并丢失旧会话；恢复后普通ps确认原runner1072700/pytest1072746继续，未重启，两个树7c/clean/498字节相同，最终PROCESS_EXIT记录pytestRC1，旧runner退出码NOT_OBSERVED。完整错误/恢复/终态封印保存在TRANSPORT_RECOVERY_7C.json，不是权限拒绝。当前未新增工具授权拒绝。前批已拒绝的 `/proc/.../cwd`、原生浏览器、私有SQL/UDF/barrier路径未重试、未替代访问或扩大权限。普通只读进程存活、公开heartbeat观测与日志不会证明进程cwd；该项仍NOT_VERIFIED。

真实账号权益/强制不可收费解析、受审网络sender、真实供应商请求响应ID和实际LIVE来源resolver未实现/未注册。真实模型/费用、PostgreSQL、Windows、原生浏览器、旧源码升级、人工语义、完整真实P-A/P-B、远端CI、部署NOT_RUN。原完整MOCK链仅工程验证。整体NOT_ACCEPTED，dependency BLOCKED_UNKNOWN、owner PENDING、semantic UNKNOWN、formal publication false。
