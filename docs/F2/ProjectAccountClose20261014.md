# F2-T09：未启动项目清单的精确关闭与显式接续

接续已接受的 `0bc90d9f8d4ab1093be079be3dae3d5f45ffb05d`。本片只处理既有 `project-natural-check.v1` 清单安全放弃入口：用户明确关闭未接受任何 CHECK、尚无消费/派生的精确清单，再自行新建另一 key。不是活动 CHECK 的取消，不改变 Run/Operation 状态机，也不宣称产品 §8.2/8.3 全部完成。

## 合同与保护

`POST /api/projects/{pid}/natural-revalidation/plans/{key}/close` 要求当前身份、精确原清单指纹和 `CLOSE_EXACT_UNSTARTED_PROJECT_ACCOUNT_RELEASE_OWN_RESERVATIONS` 确认。初次提交在既有事务和项目锁下重验完整冻结清单，核对全部独立消费索引后写 CLOSE 双封印回执。它不删除或改写 PLAN/SOURCE 历史，不修改应用、来源实例、Release、图或人工锁。

消费发现包括 START 双索引（精确阶段前缀或公开回复 plan_key）、JOB 双索引、实际接受的 project_check binding、PROOF 双索引、项目/局部版本审批、源实例局部 CHECK/JOB/logic_check binding 以及不可变派生 Release 的 origin。任何已接受 CHECK 都拒绝关闭，包括未领取、已取消、失败或成功的运行；本片没有主动取消活动 CHECK。

回执状态为 `CLOSED_UNSTARTED`、`check_execution_status=NOT_STARTED`，明确该清单未创建隔离 CHECK 实例或发起模型请求。不是 Run `CANCELLED`，也不把未知写回复称作无影响取消。关闭发生的本地效果是持久化回执并解除此原 key 自身来源预留。

来源解锁必须验证 CLOSE 双封印、完整成员集合与 PLAN 双公开标识，以及全部 SOURCE 双 Reference。任一成员的关闭引用、来源封印、原清单标识损坏，或存在矛盾消费，都不得释放任何成员。其他清单、独立 CHECK、派生版本及人工锁保护继续保留。

历史正文回读先用 PLAN 双公开请求/上下文标识、项目/身份/key、数组类型与精确成员数进行校验，再授权每个历史应用、实例和 Release，最后读取完整旧 PLAN 双封印。它不要求来源的当前 revision 等于旧快照，允许合法内部版本切换后读取旧关闭回执。历史列表只取公开 key/指纹，不读取私人 Goal/材料正文。

初次关闭仍采用完整 live 冻结校验；已漂移或撤权的未启动清单会保守拒绝关闭。这一限制保持，不能称任意遗留预留都已解决。原 16 份历史清单总额度不退款、不扩额；达到 16 份后即使关闭其中清单，也不能创建第 17 份。

CLOSE 与 START 共用既有事务/项目锁。一方先接受后，另一方拒绝；关闭后的原 key 永不重开。SQLite 精确事务入口 BUSY/LOCKED 异常沿用保守 409、safe_retry=false，仅要求 GET 原 key。没有自动重写、延长预算、修改租约/时钟或新增权限。

## 普通页面

逐应用 CHECK 区域增加独立关闭确认和“显式新建另一清单”。原清单接受后禁止以读取按钮悄悄放弃；未启动且未消费的精确关闭接受后，才允许显式新建。新建动作仅重新 GET 当前完整成员与 options，使用新 key 和新确认；保存时重新冻结当前全部来源、版本及范围，不沿用旧批准。

写回复未知时原 key/意图保持锁定；冷启动只 GET 原 key，验证关闭回执后才开放显式新建。打开旧关闭回执不会影响新清单，也不执行 CHECK、批准、提交或发布。

## 实际证据与边界

本片使用 SQLite、实际普通 Worker、mock 模型、公开进程内 HTTP 与离线 JSDOM。测试保留取消后已接受 CHECK 的拒绝、双独立 Store 的 CLOSE/START 竞争、合法公开版本切换后旧历史读取、新 key 使用当前 revision、另一清单继续保护、人工锁保留、原 16 份总量，以及重封另一成员引用/不一致上下文/多余成员/非数组/封印损坏的反例。

静态独审先后发现并修复历史正文读取前授权、完整关闭集合、公开上下文身份、数组精确数量和历史列表不必要正文读取的问题。原报告与修复后的复审都保存。没有改无关执行器或质量基线来规避这些发现。

保留的历史：boundary-first 为 19 PASS / 1 FAIL / 1 deselected（夹具误引用 grants.runtime_id）；extra-first 为 5 ERROR（外部目录未发现 env fixture，后将测试正式放入 tests）；visible-first 为 2 PASS / 1 FAIL（模拟已接受丢回复缺少既有页面生命周期的 controlledAcceptanceLoss 标记）；旧 final-core 因独审发现数组边界，精确识别本任务自己的 pytest 子进程并 SIGINT，实际 exit 2，XML 记录 1 PASS，未算完成验收。随后 core-final 因历史读取守卫检查错误参数位置而中断，XML 记录 8 PASS / 1 FAIL、实际 exit 2；该 FAIL 又实际暴露夹具误用 active 字段，按 grants.revoked 真定义修正。守卫现检查 kind 参数而非 key。随后 core-last 完整终态 52 PASS / 2 FAIL，暴露既有内部运行详情接口给 PROJECT guard 传 None 的真实集成错误，及人工锁夹具误读锁表列。前者只将该调用改为实际 mount Limits，保留 authorize=False 与完整 PROJECT guard；后者按真实 snapshot.locked 断言及同形 GET 图精确比对。旧 ui-final 3 PASS / regression-final 10 PASS 独立保留，均排除新源码最终验收。原日志/XML与两份中断记录均保留；未信号未知进程、切换环境或操作旧拒绝路径。

最终冻结源码 `3e863439200b48b2ef570701bf36bea930a46ef3`；实现核心 `bc8f850a44313397ff2f1d2bd9e73e75c9485881`，474 文件完整集合 SHA256 `70b65eff4988ae4de4b4335212c507322a0af92671c4ee52734fd44ae06666bb`，78 模块资格清单 SHA256 `201de1521313d7ab2b773efc348b12bff8f4482407e9a2f77d1d93b104da0c77`。四组执行前后及当前文件完整匹配，无源码改动。

| 实际终态组 | PASS | FAIL | ERROR | SKIP | XML SHA256 |
| --- | ---: | ---: | ---: | ---: | --- |
| core-complete | 53 | 1 | 0 | 0 | `7311444082386cf46e0c86686fdfeb18f1093db12c98089dff3b70f34f0f2bb2` |
| lease-recheck | 1 | 0 | 0 | 0 | `31a7cedb4b5b3daa6a222d565d4eb6c7e03df05e36e5a22535d2b8fd48e52d29` |
| ui-last | 3 | 0 | 0 | 0 | `d21843b5719c3e116b064daad3951c5958062102162adaea0d9e065c31686a44` |
| regression-last | 10 | 0 | 0 | 0 | `4c0b26cb88fe12608f23b1cdacb293c0e52ed748320092d616e1fe7b18508923` |

**67 个唯一用例具有实际 PASS 覆盖；68 次同源码执行为 67 PASS / 1 FAIL / 0 ERROR / 0 SKIP。** 原 core-complete 始终为 53 PASS / 1 FAIL。失败用例在 mock 应用生成夹具中因 `VERSION_CONFLICT: Stale worker lease` 未执行关闭反例断言；原失败公开回执和 XML 完整保留。之后无其他测试并行时，以新的独立夹具、同一源码重验同一唯一用例实际 PASS；未重试原失败 key、改预算/租约/时钟或权限。FINAL_INDEX 对每个唯一标识列出全部尝试。旧源码历史、中断 XML 和 focused-fix 的 2 个重复支持 PASS 不计入上述 68 次。

离线页面三场景实际 38 项检查、56 次可见动作、237 次 API fetch、126 次真实静态资源载入、6 次启动，静态字节哈希匹配冻结源码。双 Store 竞争实际 CLOSE=200、START=409，未新建 Run。Scoped Ruff 与两份 JS 语法检查 PASS；mypy 仍为已接受基线中 status_report.py/tools.py 共 5 个错误，未称全仓质量绿。

PostgreSQL、Windows、原生浏览器、真实付费模型、人工语义/完整 P-A/P-B、旧源码真实升级、部署与远端 CI 均 NOT RUN。项目依赖完整性仍 BLOCKED_UNKNOWN，总体 NOT_ACCEPTED，人工 PENDING，语义 UNKNOWN，未发布。

## 封存与交付

最终独审 [INDEPENDENT_FINAL.md](../evidence/project-account-close-20261014/INDEPENDENT_FINAL.md) 已确认本有限工程范围，无未解具体静态 finding；报告 SHA256 `d294a905d9b7947901023a3182de4e0982588cf3007e521f6d98ccf53319745a`。被审合同正文的精确副本保存在归档 author/ReviewedProjectAccountClose20261014.md。

[FINAL_INDEX.json](../evidence/project-account-close-20261014/FINAL_INDEX.json) 逐唯一用例保存尝试和原失败；[MANIFEST.json](../evidence/project-account-close-20261014/MANIFEST.json) 列完整文件字节数与 SHA256。[归档](../evidence/project-account-close-20261014/project-plan-close-evidence-20261014.tar.gz) 实际逐成员回读，9123 个成员名称集合、类型、大小与 SHA256 全部一致；53817699 字节，归档 SHA256 `7de5edf764a6f7a72adb3f3d68ff28a7aa15a6441434cac12d06d95ae9f9bceb`。此前失败、中断、执行源码与全部独审原记录保留。

本证据提交仅追加文档与归档。正常推送目标 `dev/project-account-close-20261014`；实际推送后的完整 SHA、远端 SHA、0/0 差异、工作区状态、六个保护分支与另一工作区原字节读核记录于外部 `/workspace/project-account-close-final-git-20261014.json`，以该实际回执为准。封存内 FINAL_SUMMARY 的待交付状态是封存时状态，未提前称推送完成；外部回执避免循环归档哈希。
