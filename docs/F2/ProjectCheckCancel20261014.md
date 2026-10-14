# F2-T09：已接受项目 CHECK 的明确取消与在途只读恢复

接续父审有限接受的 `2858226b9a68c943476d112af511e54581a0bf93`。此前 67 个唯一用例覆盖、68 次执行 67 PASS / 1 FAIL 仍按原证据保留，原夹具租约失败未称已修。本片属于原 F2-T09 与产品设计 §8.2–8.3，只有至多两个既有自然规范应用的已接受隔离 CHECK 控制，不扩展通用编排。

## 合同

项目页面显示精确项目、原 key、清单指纹、应用、CHECK 实例、Run、Release 和 Run 版本；独立明确确认后调用已有 `/api/internal/instances/{iid}/runs/{rid}/commands`，正文只有 `command=cancel` 与已展示的精确版本。取消竞争由原事务及版本条件决定，不自动刷新后再次 POST，不创建新 Run 或 key。

`project_natural_revalidation.py` 增加只读 `run-status`（完整当前授权）与 `run-control`/`run-controls`（所有者已接受公开控制标识）入口。`pb_natural_uses.control_scope` 增加同事务 PROJECT 的 PLAN 公开元数据、START/JOB/SOURCE 双封印与完整独立索引绑定。还按原 _start/create_instance_tx 公式重建隔离 CHECK 实例 ID，与独立接受的原 RUN_META 标识核对，阻止相同来源/Release 的旧 Run 被重封项目标识换绑到另一 key；不读取新的私有字段或引入签名、权限扩张。停止元数据不读取私人 PLAN/Goal/材料/模型正文，也不要求被撤销的资源权限；完整用量、效果和结果仍必须通过原 live 清单、`spec.verify_job` 及项目 guard。撤权后元数据 `content_access=false`，不返回或零填效果与用量，不据此断言无影响。

模型在途时取消保持意图且阻止后续派发。已返回回复保存原始证据与真实用量，取消后不得接受模型结果或迟到 SAVE；仍有不明操作时保持 RECONCILING，不能显示“已取消且无影响”。取消先于 SAVE 接受则不得写成果；原 SAVE 已提交则其用量、效果和成果保留，迟到旧版本取消拒绝。已消费 SOURCE、CHECK 证据和人工锁持续保护，不写 CLOSED_UNSTARTED，不释放清单或预算，不自动新建或重试。

取消回执丢失时保留原 key、精确 Run 与意图，仅 GET 恢复。完整读取 403 后可回读公开控制元数据；任何其他失败、损坏指纹或恢复失败都清除旧显示与按钮，保留未决意图。旧响应必须通过原身份、连接代、项目及页面 epoch 条件；新 Run 的未决意图不能被旧取消回执清除。

## 本片实际发现与修复

首轮冻结 `150064da5b41fe11cdf94c01f0082332fdc8a81f` 的 core-first 完整终态为 29 PASS / 2 FAIL / 0 ERROR / 0 SKIP，477 源文件前后无变化；XML SHA256 `fd6c5297a822daa641e5041bad28c5d774cb06314d92deb3e0c458ea03505b5b`。原源码、日志、XML 与失败公开元数据保留。

两项均为真实产品集成错误：`pa_spec_apps._advance_local` 在取消后的本地停止分支传入 `limits=None`，项目校验触发 None.model_dump；现传原 worker 的实际 Limits。另一个在途取消已经将 Run/AppRun 改为 RECONCILING，模型返回已 REJECTED_KNOWN、用量 known、操作已拒绝，但 `natural_spec_runtime.fail_owned` 排除该状态，未完成停止；现只额外接受带取消意图的 RECONCILING，并让已接受 AppRun 匹配该精确原状态，保持原 fence/worker/lease/身份守卫，未知仍 RECONCILING，不删除用量、效果或锁。

设计与首轮静态独审还发现撤权停止必须独立于完整内容授权，以及控制恢复异常必须进入统一清理。两点均已按上述合同补齐；原报告和修复复审均保留。

原环境断连提示后，实际原命令服务响应、原 runner PID 945554/pytest PID 945559 仍运行，HEAD 和 477 源文件完全匹配、工作区干净；未换环境、创建写入者或重复启动在途测试。原 suite 随后正常产生上述终态，连接检查回执保存于新证据根。

补充独审发现多份项目标识若被同时重封，仍需独立锚定原 key；采用既有确定性 CHECK 实例 ID 公式作为最窄守卫，并新增“另一真实 PLAN、重封 JOB/START 与公开 binding，但原 RUN_META/AppRun/Event 未改变”的拒绝反例。58a898fd 修复源码已有 core-fixed 31 PASS 与 ui-first 7 PASS，均完整保留，但该旧源码成功历史不冒充后来增加实例锚后的最终验收。增加守卫发生在两个原 suite 都终态之后，未改在途源码或重复启动未知测试。

## 验证状态

冻结 `ce6a0595c47dde0c5561265c3dbfa2ccc9b8721d` 的 core-anchor 已实际 32 PASS，ui-anchor 已实际 7 PASS，均 0 FAIL / ERROR / SKIP；两组各 477 源文件前后及当前完全一致。core XML SHA256 `5ed643f9de7899f8ce3e5bb02c400f0ac6dbc147e83d4a6fcd8ad09384a26782`；UI XML `f515f9e51c9e0142bfcd329dd3c8daa51d43736352570c6115b2ce4a8915146d`。原预算 SQLite/普通 Worker/mock、取消版本竞争、取消/SAVE 两先后赢家、未知响应、撤权控制与冷读、实际 HTTP/离线 JSDOM、控制恢复失败及旧取消回执迟到时另一明确 Run 未决意图隔离均已覆盖。UI 为 7 pytest 场景、76 内部断言、113 动作、744 API 请求、168 资产载入、8 次启动；不是 76 独立用例，也不是原生浏览器。

环境重启后原 session17264 不再可轮询，实际原 result/XML 已正常终态 7 PASS / exit0，原前后源码闭包一致且无在途 owned 测试进程；只读取原文件核实，未重复启动。完整错误与终态检查见 connection-check-1791995920.json。当前源码 ruff 和两个 node --check 均 PASS；mypy 实际 FAIL，仍为既有 status_report.py 三项与 tools.py 两项，原五项未修改。此前旧58源码 quality-final 与本次 quality-anchor 均保留。

必要补充回归同冻结源码实际终态 12 PASS / 1 FAIL / 0 ERROR / SKIP；13 例、896.599 秒，477 源文件前后 0 diff；XML SHA256 `1ffff6802819a3ffc1db6933e3b69e1cf3d45b6bdc0bcd22200b2c893e62cb16`。最终共有 52 个唯一用例，51 PASS / 1 FAIL。失败为原双应用完整重验：第二应用的原 300 秒 deadline 内三次原 30 秒租约领取后仍 RUNNING，fence 1→3→5；不是新取消用例失败，不能据此称双应用回归全绿。原 worker-claims 日志、DB 和 XML 原样保留，未加 claim 次数、改租约/时钟或删断言。当前失败未修，仍作为容量/进度门待解，不妨碍独立允许工程继续。最终独审逐项核实 52 唯一用例 / 51 PASS / 1 FAIL，477 文件闭包和当前质量原始输出一致；报告 SHA256 `090dbc60a005122505bbfec1b8575a2e78088d0d54f1e18a474a6cf0375bb6f6`、封印 `844e05e51603c7f945e5c707466635a7299a6a233740d99d5bf85dad911733e4`。这仅封有限取消实现和事实证据，明确不豁免原双应用失败，不签整体通过。

PG、Windows、原生浏览器、真实或付费模型、人工语义/完整 P-A/P-B、旧源码真实升级、部署与远端 CI 均 NOT RUN。页面身份/连接代切换没有可见重连入口，除既有静态 guard 与 owner B 拒绝外不称实跑；迟到回执页面反例使用原可见项目选择器及另一明确接受 Run。整体项目仍 BLOCKED_UNKNOWN / NOT_ACCEPTED，owner PENDING，semantic UNKNOWN，发布关闭。

证据归档：`docs/evidence/project-check-cancel-20261014/project-check-cancel-evidence-20261014.tar.gz`，SHA256 `6c270b2ec60a6e56d9e1f639375291c27de89c6a2d67f66f7612e52e551ff2e8`，44852788 bytes；全部 8441 regular members 逐个读回 size/hash 与完整名称集合一致。FINAL_INDEX、FINAL_SUMMARY、独审与 MANIFEST 同目录可读；归档含全部失败及实际源码快照。后续正常 push 的独立完整 SHA / 七保护引用 / 源码 diff / 未提交未推差异证据见外部 `/workspace/project-check-cancel-final-git-20261014.json`，不预称 push 成功或 CI 绿。
