# F2-T05 模型响应结算：有界实现与唯一完整链结果

状态：**FAIL_NOT_ACCEPTED**。新 continuation 的定向边界与独审通过，但唯一一次全新合成合同原完整 P-B 仍在 Cold 首次模型结算时超出原 30 秒 lease。完整 Cold 结果及专用同 Run 人工验收入口未通过；不将已有可见入口或单位门当作完整交付认证。

执行源码为 `2b67733eaefb8e67e3a083a5575261b52f2d4cdf`，分支 `dev/production-trial-stages-20261018`；基线远端 `9f7213d934081b860991332359d2b5c883d9577d`。最初指定 `8fc70cc43a6ac81cd522249e8a3d367cd66c9238` 和该远端均为实际 HEAD 祖先，当前检查记录见 `current-preflight-record.json`。本轮四个实现/定向测试提交为 `1c76318e`、`58c348ad`、`1dd3b353`、`2b67733e`，只有三个批准产品文件及一个必要定向测试文件改变。

## 实现与不变量

在同一个模型响应、同一写后 epoch 内，完成实际完整 commit guard、平台 bound、receipts、当前 Attempt 的 owner/journal/响应配对和实际 Operation 核对后，才创建 READY 连续性对象。固定 Store、连接、SQLAlchemy transaction、SQLite driver、线程、token/epoch/total_changes、Worker/Settings/stop/transport、完整绑定/输入及分角色 Limits。实际 RowMapping 的全部嵌套字段均进入指纹，不丢字段或使用 default=str。

完整 admission 当次原固定来源的身份和截止时间立即固定；每个消费者仍实际重核来源、批准/撤销、当前权限并集、完整 Run/version/fence/cancel/owner 和各有限期限。来源截止只能收紧，observed_at 继续走原新鲜性门。原五写保留同一外层事务，失败全部回滚；原 nontrial 尾守卫保留。重入、回调写入/漂移、错误及退出都失效，无失败后 fallback。没有复用 local-readback stamp、跨写携带旧证明、提前提交或增加续租。

只对既有精确 Production/P-B/cold/test-only SQLite、当前 SourceReads 段且无 qualified association 生效。PG 和其他路径继续原完整检查。不新增 executor、Grant、合同、费用或凭据；不放宽原固定来源/软件资格、30 秒 lease、300 秒 Run、quota/1RPM。真实模型和账号 IO 为 0。

## 实际门与失败保留

| 冻结候选/阶段 | 实际结果 |
| --- | --- |
| `2b67733e` 定向门 | 标准 pytest **15 PASS / 0 SKIP**，JUnit 97.695 秒，外层 102.710961 秒；真实 advance_model 五写、归档/配对、回滚及拒绝归属；夹具中 ancestry、sender、journal ledger、nontrial guard、parse、renew、资格及 trial reject accounting 为明确 unit stub。原 `_admission` 和实际固定 source 门执行。 |
| `2b67733e` 质量门 | Ruff 4 文件 PASS / 外层 1.112865 秒；mypy 113 源 PASS / 外层 42.076454 秒。 |
| `2b67733e` 唯一原完整 P-B | 标准 pytest **1 FAIL / 0 SKIP**，JUnit 610.650 秒，外层 622.734943 秒；2026-10-19 20:25:32.370656 至 20:35:55.105553 UTC。6 次有限 Mock（Generate3 + Source2 + Cold1），真实模型/账号 IO 0。 |
| 历史失败，不改签 | `1c` 11 FAIL；`58` 正例因末断言误计 BEGIN 为第六写而 FAIL；`1dd` 正例 1 PASS、负批 1 PASS / 1 FAIL / 10 未执行（-x）。其中过期夹具批准后改 Grant expiry 破坏原授权指纹，v4 已改为批准前建立原合成合同。初始非冻结开发 Ruff/mypy 记录单列，不作为冻结质量门。 |

定向门覆盖 source 写撤销、无写到期、原响应配对、首个完整证明失败、拒绝 owner 竞争、独立平台/节点 Limits 漂移、尾部重入、输出/RowMapping 嵌套漂移、失败 SQL、尾部独有 CSV Grant 到期、首证来源身份/较短期限漂移。reject_owner 竞争时实际保留 RECEIVED/DISPATCHED，未承诺所有失败必有 REJECTED_KNOWN。实际详细原件为 `phase-results.json` 及每阶段命令/stdout/stderr/JUnit/前后输入和 15 份 proof。

全部四个最终门均为同一 `2b67733e`，2,119 个 selected 输入 before==after；720 个 tracked 文件逐一与 Git blob 相等，另 1,399 个未跟踪 JS 依赖只有哈希，不冒称提交或密封主机环境。原完整测试字节 SHA `eee8394578c643989c3858826fa2f15ec41fe02436be574e3f6bbfea2c764146` 未改。

## 完整链的真实进展与终态

Source `run_0dd61f0012c74494badac36aea4f52e3` 为 SUCCEEDED，两自然 Attempt VERIFIED、六步 VERIFIED。原提取及同 key 重放、完整 Source bytes 与 controller 归档连接、四种既有归档拒绝、Release/Instance、目录 NATURAL_PB、显式 Cold 材料+Goal review/提交与 cached 去重断言均已越过。

Cold `run_2d23252a4aaf4359bcf13cf5b28524dc` 最终 RUNNING、version1、result null；只有 read_pick VERIFIED，首次模型 Attempt `attempt_0ff737bed5e74545ba5a1512b26b886f` 与模型 Operation REJECTED_KNOWN。原始响应接收/归档保留，失败五写回滚，随后原独立拒绝事务成功；没有补结算、重发或恢复该 Run。Generate Run 的原终态是 PARTIAL/已确认候选，不误称 SUCCEEDED。

专用 `spec-owner-review` 调用在失败的 Cold SUCCEEDED 断言之后，实际未执行。公共失败 inspect 的 owner_acceptance=PENDING、semantic_status=UNKNOWN 不等于该专用入口通过，更不等于真实人工/语义接受。最终七槽、22 正文及完整 owner 断言未到达。

## 事务、遍历与实际余量

| 模型结算事务 | wall / thread CPU（秒） | SQL / 业务写 | TX 入口 lease 余量 | TX body_end lease 余量 | 终态 |
| --- | --- | --- | --- | --- | --- |
| Source 第一次 | 8.603074 / 8.593357 | 10,843 / 5 | 29.992923 秒 | 21.389849 秒 | COMMITTED |
| Source 第二次 | 8.726968 / 8.725916 | 10,917 / 5 | 29.991105 秒 | 21.264137 秒 | COMMITTED |
| Cold 第一次 | **30.308420 / 30.273717** | **28,235 / 5** | **29.984939 秒** | **-0.323481 秒** | ROLLBACK |

Cold postwrite 段入口还余 12.315095 秒；实际首次完整 proof 后到达 READY 时只余 **0.332998 秒**。settle 的新 live 重核进入时余 0.273597 秒，完整 Run 谓词实际比较 `at=1792442137.9234967` 对 `lease_until=1792442137.6049478`，晚 **0.318549 秒**。本次精确失败比较时刻有原观察事件，不借用旧运行推定。TX body_end 的节点/合同 Run 余量仍约 148.458551 秒，首因是 lease。

Cold 整个结算 TX 的原 span 次数为 bound9、commit_guard3、_pb_source3；postwrite scope 观察到 check_commit1、全部 _journal_chain15、_journal_source5。**15 包含 Source/Generate 祖先证明，观察器未保存每次实际调用 aid，不能称当前 Attempt 重跑15次。** READY 后 check_commit0、_journal_chain0，只有 _journal_source1；新消费者确已减少后续完整遍历，但 fresh live 仍按原门因到期拒绝，tail 未进入。两个 live enter 分别是构建末重核与 settle 重核，不能称两个成功消费者。

下一最小工程待定位点是：同一个 Cold 结算事务中，写前完整检查、写后完整首证和祖先/来源血缘遍历已消耗近全部 lease，READY 后必需的当前权限/source/Run 重核仍需时间。本轮按单次完整链边界停止，不继续叠加优化、改期或重复完整链。SELECT/时长的单次差异不证明性能因果或其他主机余量。

## 证据与限制

`full-observer-metrics.json` 是 `analyze-full.py` 对原 `full-stage-probe.json` 的只读算术；保留所有阶段事务 wall/thread CPU 与原事件。观察器 SHA `b3ff9acb61bba576994285679457c90b7afb3b36570a2dd6c3e782084445ec04` 在启动前独审、结束后相同；没有新增 SQL、替换时钟/门或改合同。观察有调度开销，undo 不 join 已进入的后台 wrapper；tx_body_end 在 commit 调用之前，不能代替 commit 时间采样。节点/合同 Run 余量分列，不代表所有期限的通用最小值。

`ended-state.json` 通过 mode=ro 导出已结束的新合成 fixture；原 DB SHA `598d2dcaf9c1f582a897bfc2f705a5b41af31de67e684fb0db169d11fcd7fd85` 导出前后相同。它是诊断，不是重新准入或恢复任务。`outcome-summary.json` 保留缩略状态及事件计数。

v2设计、旧设计P2、实现独审v1/v2拒绝与v3有限ACK均按原 seal 复制于 `prior-design-and-reviews`，原封存目录未写入。上一轮原完整链 FAIL 与证据仍见既有 `docs/evidence/pb-cold-local-read-cause-20261019`；旧满盘未落盘最终独审没有补回。当前最终运行独审另附，有限源码 ACK 不升级成完整 P-B 接受。

相对9f，web字节未改；已有目录选择、账号/项目/实例导航、迟到回调隔离、防重复提交的有限 HTTP/JSDOM 证据仍按旧 SHA 归属，本轮未重跑。Windows、原生浏览器、PG、真实模型/账户、真实材料语义/人工签收、部署和远端 CI 均未执行或未核验；旧 Actions API403 未重试或绕过。没有 main、强推、部署或权限/费用变更。正常开发分支推送和最终远端差异另记交付回执，不伪装为同一源码 SHA 重跑。


## 本次交付包（作者封包后核验）

[原始包](pb-model-settlement-raw.tar.gz)：6,557,865 字节，SHA-256 `eeac4be38860f446d29e2c059ab57d5b98101447945d19c1912231bfa7ec7249`；418 个 regular 成员的名称、长度与逐件 SHA 全部验证。6 个 pytest 临时目录符号链接不封入包，其路径和目标已列入 manifest；真实文件全保留。原始根已封存不再写入。

- [封包回执](package-receipt.json)、[原始清单](RAW-MANIFEST.json)、[封印](RAW-SEAL.json)。
- [最终运行独审](final-review.md)、[独审结构回执](final-review.json)、[独审清单](review-manifest.json)。独审审查真实运行及原说明；封包后的 archive 核验由作者完成，未冒称独审已审未来包。
- [全部阶段结果](phase-results.json)、[最终输入身份](input-identity.json)、[结束状态缩略](outcome-summary.json)、[完整事务算术](full-observer-metrics.json)、[执行源快照索引](source-index.json)。

独审报告 SHA `289c5c8cec37729e238326c629f80769dbfc431e3527101ca784fca7cafc0f67`；独审 manifest SHA `437b7e40db7a40ba2908b8bf774bf342b5656f65d79d9817b310760beb448860`。原始 manifest SHA `205df905e684576509cd101b795b90ba298586968659d95a281d1843f083ac02`；seal SHA `246a93614f27c88309f2b433a29422b7f3191c45abe9ee56713b22e306cceac9`。

该证据提交仅新增文档和证据包；实际测试源仍为 `2b67733eaefb8e67e3a083a5575261b52f2d4cdf`，后续交付回执核对 src/tests 树一致。最终 push/ls-remote/未提交未推送差异在环境交付回执中单独核验，未当作同 SHA 重跑测试。
