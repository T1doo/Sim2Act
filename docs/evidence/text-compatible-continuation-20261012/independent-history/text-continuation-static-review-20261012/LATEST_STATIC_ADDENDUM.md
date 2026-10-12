# 最新静态追加结论（snapshot-6，源码仍 mutable）

本追加覆盖 root 后续普通 approval GET 修复与新增显式接续 UI。原 STATIC_REVIEW.md / findings.json / manifest.json、snapshot-1 至 snapshot-5 全部原字节保留，原报告 snapshot-5 的 R3 开放状态只代表那个确切快照。当前动态仍 **PASS 0 / FAIL 0 / SKIP 0；全部 NOT RUN**，未启动任何测试或 fixture；root 所报测试不计入本独审。

**R3 静态闭合**：internal_api.py:134–144 先 owner+kind=release 的 scalar draft ID，draft_gate，才取完整 approval.payload；foreign/非release先拒。新 read_release 的完整 owner filter 与 scalar target门保留。app_jobs 的正常 inspect_job 与 authorize=True load_binding新增job_gate，然后读本人的Run或私有binding。controller cached PREPARE/COMMIT/GET先 target门；STOP metadata不需要目标内容授权。R1/R2/R4源码修复保持，R5至少单origin discriminator剥除有proof.kind回退，组合负例仍待动态。

**UI 现有有限正确结构**：textContinuationIntents保存精确首次 body与随机原key，未知不重发POST；恢复只走GET。按identity/connection/project/workspace/edit/epoch冻结context；PREPARED重建完整批准 payload 的 SHA256，与选定 app/candidate/software/revision/data_version以及语义UNKNOWN/0model/保留data标志核对，要求手动ack和未过期。COMMITTED再只读真实Release+instance，并核snapshot hash、continuation marker与获批关系。STOP与STOP_RECEIPT分开，不把提交后的晚CANCEL误称执行停止。handoff tc.open 使用独立身份/connection/project/workspace/edit guard，避免正常 showApp/clearInternal 消去旧context后永远不能打开；showApp自身 app generation 与 showInternalInstance工程view/instance generation仍保证实际对象选择。

**仍有两项 UI 静态修正要求**（已经送root，未执行动态）：

- R6，text-logic.js:69：await POST 后立刻 api(intent.read)，下一GET之前缺 tcCurrent(c)。换身份/连接/项目的晚POST结果会用全局当前token发旧iid/key GET；即使backend拒绝，此链也违反原请求/身份fence。POST返回后须先检查current再进行GET。
- R7，text-logic.js:66/44/50：cold输入原key的intent未保存该key，tcAccept不统一比较value.request_key；PREPARED无本地body时也未核p.source_release_fingerprint等于selected.release_fingerprint。完整hash自一致不能代替与原key和已选择旧Release的绑定；需明确intent.key、所有返回统一key绑定、selected旧ReleaseFP及finite expiry/hash shape/owner/runtime metadata。服务器commit仍核实际批准，不宣称UI问题导致已绕过交易。

结果分类：R1/R2/R3/R4为 STATIC_FIX_OBSERVED；R5为单标记修复源码已见、组合/privacy负例需动态；R6/R7为 STATIC_OPEN（非实际FAIL）。没有产品动态签收、source freeze或旧源码升级结论。PG/Windows/native/真实模型/付费API/真实用户旧库/人工语义/P-A/P-B/远端CI全部NOT RUN，不重试已取消安装竞态或Forbidden路径。

确切最新审閱源码散列：text_continuations.py **d35747645542484405183428c43456fc63d4730ff6dec8cfc3f08eb6fe31443a**；internal_api.py **5e62d681d8d1802df171ad021e65afd44c4e2669afdbe87ce0717ab8652ccec4**；web/text-logic.js **a607540f3a76697550369c22a6964f8874b5bb00e400dd831d494f47a06cdeb1**。完整21个文件具体清单见 snapshot-6/sha256.json。下一修复须新快照/新addendum保留以上实际字节。本轮根仍为唯一仓库写入者。
