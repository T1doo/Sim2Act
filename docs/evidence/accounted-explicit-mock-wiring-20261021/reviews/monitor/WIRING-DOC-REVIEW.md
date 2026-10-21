# 最终接线 README：独立只读口径复核

结论：**ACK_DOCUMENT_SCOPE_ONLY**。未发现与既有路线／设计／代码闭合报告不一致的实质表述。

本次只读 `docs/evidence/accounted-explicit-mock-wiring-20261021/README.md` 及其 SHA256、当前 HEAD；没有重新审源、运行代码／测试／DB／Mock／G0、发信号或修改仓库。HEAD 为 `a0fbd16e7d917ca00ab55aed81519d454bb35998`；README SHA256 为 `0260012019889cf6f67d370f822b1644db4879192085291956aec01c1c9eb24c`。仅写此 `/tmp` 审查记录。

已核口径：

- 默认 None、普通调用／post 不选 candidate；精确目标核验、计数关闭与 arm 后才进入显式分支。历史三项合成替换不被写成真实账户或软件资格。
- 6 次交换／8 次入口限定 Generate3 + Source2 + Cold首1，以及同一已收 Cold 响应的两次原 commit、W5 前停。完整 PB 3+2+2 在固定 handler 下为 7 次交换／9 次入口，至少六个 60 秒 reservation 间隔、跨度 360 秒，明确超出现有 6/8 合同；不扩限、执行或申请新窗口。
- 首 G0 前六次 reservation 跨度至少 300 秒，不是额外纯等待或成功时长保证。原 TTL1800／各 Run 最多300／lease30／每60秒一reservation 与外层480／120／600+10秒分别保留，未用外层预算延租约。
- 64 MiB 被明确称为监测预算而非硬配额，含真实采样间隔与清理证据要求。native 有限配置、完整输入资格／实际 OWNED 见证及整进程 RSS 保证仍缺失；大 fixture allowance 和旧磁盘峰值没有被当作这些证据。
- selected DomainError 保守 UNKNOWN、来源未定，默认原分类保留；UNKNOWN 不被父 launcher 认作成功。完整返回仍不等于选中了 OWNED。
- 最终12 passed、guard 27 passed + 4旧依赖跳过，与先前只读原件核验一致；192 passed 明确属于分类修订前，不重标最终四 SHA、不累计重叠验收数量。stand-in 局部测试未冒充完整 prepare／两次实际 commit／G0。
- account 输入／内部输出／固定服务端信任根三层分清；requirements 与 DTO 不提供权威；身份／权益／收费控制／撤权事实可来自同一受审来源，不制造四个外部接口要求。业务归档 Source 与账户 source 被明确区分。真实 resolver 仍 SOURCE_MISSING，既有 check_source 无统一30秒观测年龄门，候选诊断30秒与 lease30秒未混淆。

本复核只确认该 README 与已完成独审的边界和证据表述一致，不新增执行授权、生产资格、配置数值、性能结果或任何测试结论。代码闭合 ACK 及其限制仍以 `WIRING-CLOSURE-REVIEW.md/json` 为准。
