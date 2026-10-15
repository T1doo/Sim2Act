# 有限双应用完整复验与 P-A/P-B 准入工程

集成分支 `dev/project-complete-checks-admission-20261015`，基线 `52654f7610602b7afc8a2c44eee7abc23e5c2d5d`。本批冻结源码与测试为 `0b6a780c952fb6eeed5e545f0f6db5f8e64360e6`；交付提交仅追加文档与证据，src/tests/pyproject 与冻结源码字节相同。根代理为唯一集成写入者，隔离作者、回归和独审不修改 main/coredev。

## 实际修改

`pa_spec_apps.py` 将 SAVE 的 typed/AppRun/terminal 写入组成同一事务写组，去掉两次重复全项目审计。初始完整授权读段取得实例指针与版本，原 data_version/revision/release CAS、真实 artifact 写入及读回、末尾完整 scope/verify_job/typed/实例/模型审计仍保留。写组中重验精确 owner/principal/project/runtime/worker/fence/version/原 lease、取消/停止与新鲜执行预算，末尾重验完整绑定和未知效果。没有新增跨事务授权缓存、续租或重试。

`text_workflows.py` 只把已识别 SQLite BUSY/LOCKED 后台 heartbeat 异常转入现有 RESOURCE_UNAVAILABLE 处理；仍由原 owner/lease/fence/未知效果决定结算。fail_owned 再遇相同锁忙时保留原 Run 供有栅栏的恢复，不增加领取或退款。意外异常仍传播，迟到结果不能覆盖已完成终态。RESOURCE_UNAVAILABLE 的公开 effect_known 不是操作效果已知的证明。

独审反例已修复：SAVE 缺失 public owner 由 NoResultFound 改为受控 VERSION_CONFLICT；损坏的原试验合同 GET 由 ValidationError 穿透改为受控 409，拒绝前后的请求/Run 不变。修复前源码、输出、反例与修复后测试分别保留。

正常 `api.py` 挂载 `natural_trial_api.py` 八个鉴权入口：精确批准/撤回/阶段预检/阶段批准/准入，以及原批准 key 的批准、阶段与预算读取。精确身份、项目、trial key 与材料权限先检查，再读取原成对合同；未知结果只按原 key 读取，不创建 Run/reservation 或替换合同。请求不能提供 fee authority/free/live override，生产准入以 authority=None 调用新鲜 guard，保持 LIVE_BLOCKED/HTTP400；未注册 sender。

`PBTrialContract` 冻结 P-B 路径、独立抽取 key 和完整编辑 Recipe，旧 P-A 序列化不变。Generate/Source/Cold 同试验七槽仍为 3+2+2；cold 必须通过既有完整 pb.verify，同总账原 source Run 的两个 VERIFIED/MOCK/known/accepted Attempts、真实 wire/raw 哈希/字节/usage、原 extraction/metadata/source 和完整新 cold Goal/material 逐项绑定。未知或被拒成本不能取得资格。

P-B cold 去重只用于可证明的同一只读段：普通 spec_task 的 bound→verify_origin 已以精确 conn/draft/limits 执行 pb.verify；snapshot 含 human_correction/logic_check/pb_use/pa_use 或 release 含 natural_logic_source 的其他分支仍执行原额外验证。同 trial/key/Recipe/source Attempts/原证据检查保留，不跨写边界复用证明，不宣称任意负载的性能或容量保证。

恢复测试仅将已有单次 Run SELECT 从 pause/cancel 前移到取消提交后，检查同 worker、cancel 和 RECONCILING，再等待真实 lease 自然过期。原恢复矩阵、回滚、撤权、双 Store、版本竞争、旧 owner 拒绝等断言不变；没有新读取、测试续租、时钟注入或预算扩大。生产82模块与 bb287 完全相同。

## 同一冻结源码的完整结果

单一原进程完整终态 **199 PASS / 0 FAIL / 0 ERROR / 0 SKIP / 0 deselected**，RC0；collection↔XML 精确一一对应199 unique/0 duplicate。pytest耗时4588.65秒，runner墙钟4591.070秒；488个src/tests/pyproject执行前后、executed-source、根工作树与冻结Git字节闭合。XML SHA256 `8a6e3af4d49cb26b52d05674a5ec054489fc51c596a1a6c9de62a37eb3214b4a`；RESULT SHA256 `5cd6b96c9c01d37ad965c20009ce344991495bf816212869b3203706e6d3936a`。两个Pydantic warning保留在原stdout，不计为失败。

范围：项目重验6、取消10、恢复4、历史UI8、准入34、预算28、精确资格22、租约4、心跳33、普通P-B failures7、新P-B trial1、HTTP8、受控phase1、typed27、原事务6。probe/作者/独审单测不与199合计。

原双应用保留 Run300 秒、lease30 秒、最多三次领取与全部原断言。三组七槽没有 deselect：P-A 与 P-B 各是实际合成 MOCK Worker 的 Generate3/Source2/Cold2 完整链；另一组是实际 Store submit/claim/heartbeat/reserve/settle 七槽，不能称为第三条模型 Worker 链。

原双应用两个 CHECK Run 均一次领取 SUCCEEDED/fence1。P-A/P-B 两实际MOCK链各7个唯一槽，全部accepted/KNOWN7000 tokens，reserved envelope48354，六次间隔均≥60秒；所有permit为SYNTHETIC_ONLY/live_allowed=false。Store七槽原断言KNOWN14/envelope7868通过，原测试不导出JSON。P-B公开事件35条=7 dispatch context+21 permit+7 accepted结算，0拒绝/错误事件。UI8实际119个内部检查、143 actions、888 API requests、189 assets全部200、9 boots；这是进程内HTTP/JSDOM。

同 SHA 质量：fullsrc Ruff PASS、12个 changed Python 文件 Ruff PASS、产品与夹具 Node 语法 PASS；full mypy FAIL，仅 status_report.py 三条/tools.py 两条原有错误，逐行与基线一致，新增0。mypy检查83源文件；精确软件资格完整82模块，config 按原规则排除。pin `bcf48da5c3141eeaa35ad32543d34a48b14519b7e4f5f0e1772c701b61f41041`，review_candidate `cadd1864e9f4da8209936edcf8b8e299a537a2e4`；ANCHOR/CHANGED/来源/排除不扩，仅唯一 AST literal 归一化 zero64。

独立审查报告与源码/pin/质量/终态逐项核验随证据提供。此前发现的具体反例已修复；最终是否存在新P1/P2以最终独立报告为准。

## 历史失败与原因边界

| 实际历史 | 结果及可证明范围 |
| --- | --- |
| 旧 ce6 双应用 | peer 三次 RUNNING/fence1→3→5；完整原失败保留，确切首因 UNKNOWN。 |
| 原526自然/计时运行 | 各1 PASS，487.17/506.88秒，不计入新199。计时 peer SAVE writer35.468639秒，进入余lease29.991211秒，末尾过期5.477428秒，同窗口三次后台锁忙；证明同类长事务/租约机制，未自然重现原三次全失败。 |
| 受控SAVE phase | 明确 FAULT_INJECTION，实际 Store/Worker/spec.advance 原300/30/3，每完整scope后推进8秒；旧4次32秒→三次RUNNING，新2次16秒→首次成功。不是完整 Worker.once 自然复现或耗时节省证据。旧另一注入在SAVE前锁异常、segments为空，失败保留。 |
| 作者/独审反例 | heartbeat修复前7 FAIL；HTTP最初3P/2F为400/409断言错误；P-B cold原来源guard误期望RECEIVED、真实状态VERIFIED；损坏scope GET与缺owner反例独立保留。 |
| 2dda完整199 | 198P/1F/0E/0S，4721.077秒；唯一P-B cold settle accepted=false，确切历史拒因UNKNOWN。XML193c5cd1b48467b8554a11069799624110536eaa9c4287c5f1655e116559f919。 |
| 9b公开诊断probe | 1P，477.525秒；未重现2dda，不作为旧失败精确原因或产品修复证明。 |
| bb287完整199 | 198P/1F/0E/0S，4749.329秒；三组七槽通过。恢复matrix前expired_return准备返回CANCELLED而非RECONCILING；取消前lease读取存在续租窗口，但历史实际renew NOT_RECORDED，matrix未进入，不能推断恢复算法失败。XML6c1ff17443cb28f95e05bc0618fede902b77c52dfebb4237f103e0dad0558937。 |
| 0b恢复probe | 完整4P/0F/E/S，237.704秒；单列，不加到新199。XML49172d9aa791ef0d2427829f377fbacbeebb33b684b91128b0f879cb7f1681a9。 |

## 证据与未验收范围

[证据索引](../evidence/project-complete-checks-20261015/README.md)提供原始失败、修复、collection/XML、stdout/stderr、完整源码封印、公开回执、质量和独审档案。六组归档逐成员大小/SHA与原文件回读相等，manifest集合精确闭合。源仓库无未提交产品/测试差异；普通独立分支推送的最终 SHA/远端/9条保护分支/其他 WIP 与 ahead-behind 回执另行提供，不能据此称远端CI绿。

PG、干净 Win11、原生浏览器、真实模型/费用、独立人工语义、完整真实 P-A/P-B、真实旧源码升级、远端 CI 与部署均 NOT RUN。已知私有 SQL/UDF barrier 与原生浏览器拒绝路径未调用；仅执行允许的 SQLite/实际MOCK Worker/公开API/进程内HTTP/JSDOM。当前范围是所列199项，不是全部软件测试通过。

可信 account→quota resolver、合法免费权益与强制不可收费 authority、经审 sender 尚未注册。caller quota label、用户确认或 SYNTHETIC_ONLY 不能证明真实零收费。有限工程交付不关闭 F1/F3/R0/C0：整体 NOT_ACCEPTED，dependency BLOCKED_UNKNOWN、owner PENDING、semantic UNKNOWN、formal publication false。

用户硬目标北京时间2026-10-22 00:08（UTC2026-10-21 16:08），不是已核实赛事截止。首版为F1→F2→F3→R0→C0，F4–F7不是前置；P-A/P-B为两条路径。外部账户/设备/授权材料/人工语义/官方规则与另一参赛项目身份仍由父级收集。
