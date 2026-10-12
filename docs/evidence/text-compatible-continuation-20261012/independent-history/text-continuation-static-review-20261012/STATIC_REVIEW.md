# 静态独审：显式文本软件兼容接续

结论：**静态审查完成，当前 snapshot-5 仍有一项高优先级普通 approval GET 授权顺序缺口；尚未最终冻结，不能称运行通过或旧库升级验收。**

仅 root 写仓库。独审者只在本 /tmp 目录创建报告与五份审阅快照；未编辑仓库 src/tests/docs，未创建 SQLite fixture，未 import/执行产品代码，未启动 pytest/Worker/HTTP/JS/浏览器，不访问网络、不重试 CI/取消安装竞态。HEAD 读取为 df5f422174c4eeea96e5dd16c141dc0a4b36b3e6；正在开发 dev/text-compatible-continuation-20261012，审阅树有 root 的未提交实现。没有适用 AGENTS.md；/workspace/.agents 文件扫描为空。

按 docs/F2/TextCompatibleContinuation20261012.md 核对 finite 233/a747 literal 软件接续。已独立保留 snapshot-1 至 snapshot-5 的源码原字节和 sha256.json；后续修改不能替换这些审阅证据。最新 snapshot-5 包含 17 个实际阅读文件。主文件 text_continuations.py SHA256 为 **56e28fab1d12268af7d88819c2101f6ed15315958a4acba2e881f91bd6e6e591**；所有其它确切散列见 snapshot-5/sha256.json。snapshot-1 至 snapshot-4 保留最初发现与修正前后顺序。

1. **R1，源码已修，未动态验**：新 PREPARE/COMMIT/GET 缓存原先可在当前 target 撤权后先读私有 AUTH/BIND/approval/seal；现新 controller 先 owner/project，scalar RID/runtime/project，再双主体 authorize；STOP metadata 保持独立。
2. **R2，源码已修，未动态验**：现所有实例 AppRun 必须有本人的同项目实际 Run，终态一致且无 UNKNOWN；保留 typed 行调用原 text_run_checks.verify。其原验证 body 仍核 accepted binding/frozen contract/old release/Goal version、实际 operation + intent + receipt 与当前目标独立复算。archival_software 仅内部 keyword，不作为 HTTP 可传参数；正常 load 仍 current 软件 strict。
3. **R3，部分已修但仍开放**：普通 load_draft/validate_frozen_candidate/verify_candidate/read_release 已加前置 target 门，read_release 已 owner-filter 完整行。**internal_api.py:134–145 inspect_approval 仍先读整个 internal_approvals.payload 再 owner/kind 检查，最后才核 target**。新兼容 release 的 approval 也经过该普通 GET；因此 controller 门未覆盖此路由。需元数据 scope/owner/kind 与当前 literal target 授权先行，再私有 payload。未复现为动态 FAIL。
4. **R4，源码已修，未动态验**：新提交先构造 historical response，再末尾独立 execution / precise approval expiry / all-project Grant CAS / current_permission fail closed，避免 public_commit 吞 live error 后仍提交；Store.tx 捕获 BaseException 回滚全事务。缓存或历史 GET 允许权限过期时 current_permission=false，与新提交分开。
5. **R5，单标记问题源码已加回退，仍需组合负例**：origin kind 和 canonical proof.kind 任一保留会先过授权门；execute 的旧 authority 检测与当前 canonical 重建又要求 exact marker/permit，缺标记不得降级普通执行。联合 stripping/claimed draft-id 变更后的 privacy 路径需 SQL 屏障，不静态宣称覆盖。

执行范围检查：known 锚 JSON 原 SHA256 被硬编码固定；只两个批准的旧 all-Python exact map，未白名单改动文件仍 exact；literal 工具/recipe/schema/ABI 源文件未改。新 target implementation 绑定全当前 top-level Python map（config 除外），并进入批准 payload。候选/old AUTH/BIND/task extraction/logicfp/Goal anchor 不重签；新 COMMIT/APP INDEX/Release INDEX 双seal由完整 approved preflight 重建。instance 更新只获批 iid 的 release/revision/history，data_version CAS 不写 typed 或 schema；正常 current-source load 与 public bind 路径不改旧 canonical authority。

明确执行门：apps.preview、lifecycle.execute/new instance/generic switch 拒旧 literal 无具体上下文；literal synchronous run_instance 本来即要求 durable Worker。app_jobs.enqueue/resume/prepare_dispatch/commit_result 和 owner_acceptance.base 核 exact compat Release+iid+revision/current software+AUTH TTL/revoke+target Grants/budget。app 范围 archival index 只帮助正常读，不授其它 instance/old queued Run 执行。owner context 要当前新 Release/revision 的成功独立新输入 Run，原声明 evidence 不匹配会 STALE，不能自动继承 ACCEPTED。

停止/恢复：CANCEL 可以 metadata tombstone 阻挡未到 PREPARE；REVOKE 验具体 COMMIT pair fingerprint 后追加停止双seal，不改原 Grant/AUTH 或 owner 声明。late CANCEL 若已经提交，现写 durable stopped=false 的 STOP_RECEIPT。GET STOP key 不读原私有批准，unknown key 只返回 OUTCOME_UNKNOWN；PREPARED GET 已核未消费精确批准/expiry。是否在真正撤权、任务迟到、版本竞争或写入故障下零部分提交，仍必须实际测试；此轮未运行竞态或被禁止旧 probe。

后续最少动态集合：授权撤回与 foreign identity 对 PREPARE/COMMIT/cold app/release/approval/instance/owner GET 的 SQL 私有读取屏障；单/双 origin stripping 与 release marker/instance revision/receipt 篡改；保留旧 typed proof 缺 binding/contract/operation/intent/receipt 的拒绝；批准过期、目标撤权/取消/末尾校验失败的单事务零写；其它旧实例/queued Run 不复活；冷 NoModel Worker 新输入与旧 owner STALE；正常原键未知/停止/提交恢复。未知实现/ABI/真实旧生产库范围仍拒绝，不能用当前脚本改成旧源码升级结论。

计数：本轮 **动态 PASS=0、FAIL=0、SKIP=0；全部动态 NOT RUN**。表内“源码已修”只说明在对应快照上独立读取了代码变化，未假充 root 的测试、正式 freeze、独立通过。SQLite 实际旧库/Worker、HTTP/offline UI 本轮均 NOT RUN；PG/Windows/native/真实模型/付费 API/真实用户旧库/人工语义/完整 P-A/P-B/远端 CI 均 NOT RUN。未扩大网络/安全权限，没有新的工具授权拒绝。

剩余 blocker：R3 普通 approval GET 授权前私有 payload 读取；root 最终源码冻结与必要动态证据。root 若另行修复，须在新快照与 addendum 标明，不改本原字节。
