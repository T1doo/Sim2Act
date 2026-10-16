# 新 P-A V2 审阅、执行与阶段交接期限（2026-10-16）

基线 `a8d30e253c11ed84180328c623efeb2af580e352`；冻结并实测代码 `7a5434ca7c969053d35c4e5ae5b8306cc82ae6b3`；正常独立开发分支 `dev/pa-trial-deadlines-20261016`。

原准备合同的300秒期限不足以完成RPM1下七槽：第七预留最早首槽后360秒，还不包含完整模型延迟、工具、排队或人工交接。因此本轮新增明确同意的P-A V2；不是延长V1或给361秒就宣称完成。原方案的有限预算/Run/人工确认边界见 `../sources/V5/平台产品设计.md` 与 `DeliveryRemainingChecklist.md`；完整P-A/P-B和资格门仍保留。

## 精确合同与执行语义

|字段|新V2固定规则|
|---|---|
|prepared_at|服务器完成授权材料读取后一次冻结|
|review_expires_at|prepared_at + 300秒，写前和写后均须严格在窗口内；迟批准、过期重复批准均拒绝|
|execution_expires_at|prepared_at + 3600秒，总窗口包含审阅、排队、模型/工具与人工交接；不从批准时重新计时|
|expires_at|必须精确等于execution_expires_at，供原admission、每槽reserve、dispatch等待、账户/permit和Run守卫使用|
|stage_handoff_seconds|900秒：后继阶段须在精确前序Run受理起900秒内明确批准，且早于执行截止|
|阶段精确截止|min(前序受理时间+900,execution_expires_at)，与前序ID/受理时间一起进入StageAuthorityV2指纹|

交接窗口包含前序Run最多300秒、排队与人工交接，不能解释为完成后另给900秒，也不保证固定600秒人工时间。实际剩余交接时间随已用运行/排队时间扣减。60分钟是硬失败关闭的上限，不保证七槽或全部阶段完成；每Run300秒仍包含配额等待、模型延迟与工具工作。原七槽3/2/2、输出7168、每Run预留64000、总192000、wire32768、RPM1、paid0全部保持。

Source前序是本trial已完成且来源完整核验的Generate候选（原工程状态可为PARTIAL，不是语义签收）；Cold前序必须是本trial配对精确批准且SUCCEEDED的Source。核对原批准键、Generate前序、受理时间和阶段截止。阶段时钟只限制审阅/批准，已及时批准的Run可以在交接批准截止后，继续受原Run、租约、执行截止、撤权/取消/版本约束运行。

两项绝对截止及交接上限都进入精确合同指纹并在实际页面展示。显式V2解析/序列化避免被V1类型截掉字段。原key GET、重启、重放和重复操作不重新计算期限；到期原预留重放仅返回不可派发的原账目，不续期或退款。CLOSED、撤回、权限、版本与原键恢复规则保持。

## 实测与独审

最终 **100 PASS / 0 FAIL / 0 ERROR / 0 SKIP**，进程墙钟363.117583秒。主进程99PASS、1个明确deselected；同一冻结源码的另一隔离进程完整执行该原真实60秒节奏节点1PASS（361.58秒），合计100个唯一节点，无遗漏或叠加计数。两个时钟域/SQLite夹具完全隔离。509份src/tests/pyproject清单前后与Git相同，源码未漂移，原拒绝模块导入/加载为空。

- 最终实际既有mock Worker + 测试adapter调用原admit/reserve/settle：七槽3/2/2全结算、已知用量；相对准备时间约0、60、120、880、940、1000、1060秒，每槽至少60秒间隔，每Run仍少于300秒。Source批准在原交接截止前，随后第二个请求已跨该批准截止而合法执行；迟阶段/执行截止、迟同意和跨截止回滚均拒绝。
- 合成时钟用线程锁串行微步读取（1微秒）及最多10秒显式步进。观察原process参数与原Worker/共享state，调用原runtime.renew实际续租并更新原共享状态，18次此类续租；未改guard、锁、lease行或失败flag。它不是生产PATrialBinding发送器运行、真实墙钟性能或锁争用修复证明。
- 20个实际交付页面JSDOM情景、508项检查、25次启动×21资产、117条trial HTTP；明确显示两个截止及非完成保证，保留B丢同意/撤回回执、原key重载、Goal变版关闭和CLOSED/批准竞争。
- 新代码重新读取修改前的同一个V1 SQLite：原8行（含1个UNKNOWN不可退还槽）、合同、批准与300秒期限未变；数据库前后SHA256均为 `3b45551185fc0579f927f0b244aefdc353ff0b623727ab31f776b02d8cb781b6`。V1/PB/Approval/StageAuthority原类AST与基线一致。原key不能换成V2覆盖旧批准。此为合成旧库保留证据，不是全面真实旧用户库升级验收。

全部历史保留：红轮3FAIL/1PASS；修改前V1加账目1PASS；首批28PASS；新增七槽首轮10PASS/1FAIL（首槽前读取不存在账目之测试错误）；静止时钟Source WAITING_RESOURCE/heartbeat锁错误；后续时钟驱动未同步共享心跳state导致BUDGET_EXHAUSTED；seven4临时Worker-context PASS只作开发历史，最终冻结回归使用原实际Worker对象后重新完整通过。初期失败不是被改签成PASS，也不声称真实锁争用已解决。

独立冻结审查在归档 `review/FINAL_FROZEN.md`，仅签收V2期限及声明的离线证据。实际模型/付费请求0，软件资格anchor、账户费用资格和生产resolver/sender均未开启；LIVE关闭。原main/coredev及既有证据/WIP不改。不称远端CI绿。

Windows、PG、原生浏览器、真实模型/费用机制、真实墙钟七槽产品性能、人工语义、完整P-A/P-B/历史Cold、真实旧库全面升级及部署仍 **NOT RUN / NOT ACCEPTED**。

## 证据交付边界

工作区代码提交后仅余约308KiB；没有删除旧封存或修改旧工作区。Git随分支提交关键原JSON/回执、JUnit/命令、日志、独审与harness的审阅包 `../evidence/pa-trial-deadlines-20261016/review-evidence.tar.xz`，73672 bytes，SHA256 `f72c90d250c6bc44bda9882118ed7c16891310185ea076390ff110c7f703518d`。

完整SQLite/full HTTP及所有原始成员留在同一指定环境 `/tmp/pa-trial-deadlines-20261016-delivery/complete-evidence.tar.xz`，570188 bytes，SHA256 `6b8f236c429dc69b084cf62f9c04dd213841f7bcf9e727b688daed3527df1c05`；完整清单 `/tmp/pa-trial-deadlines-20261016-delivery/MANIFEST.json`，SHA256 `f42ae38600ff4a8d0f743385f6077bdd716a75cf182cf1e7b4e849ae115e6337`。完整原始归档没有提交进Git，不能把审阅包称为全量原始证据。完整归档467文件、147原夹具xz hash均保留；原压缩表示在总归档展开重压，所有原成员字节及两归档均逐字节回读核验，原B未删除/改写。

JUnit：main `a7f7969a6cd80f69e499ba4e40d201af670f1f65e65bee45e9fbe1405052c342`；独立原真实cadence `a103a28421e6b5dfeaa87d0548b2ef321c9798306260252a4321ef84dc7c1dec`。
