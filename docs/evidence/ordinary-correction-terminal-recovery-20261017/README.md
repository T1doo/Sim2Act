# 已知保存后撤回父拒绝：终态补充验收

基线 `d4c02072a40ac98075cfebaf22d23cb8cd24cbc4`；测试冻结 `9f7d881789ce07e2b5868919e5a3f9a794c6ff3b`；普通分支 `dev/ordinary-correction-terminal-recovery-20261017`。本片仅加强一个既有测试及使用说明，**生产源码、schema和pyproject共127个输入与d4c逐字相同**：[逐件证明](raw/author-meta/production-identity.json)。没有生产修复，也没有伪造“生产红→修复绿”。

父线程指出原测试只要求child非PARTIAL，未证明lease恢复后收敛。作者先在原d4c运行原断言，1PASS/RC0；[原始观察](raw/baseline-data/test_final_commit_rechecks_rej0/known-save-rejected-final.json)确为RUNNING、result/error均null、首次save VERIFIED，不能称为已经FAILED。[命令及退出码](raw/author-meta/baseline-execution.json)、[原XML](raw/author-meta/baseline-junit.xml)。旧证据保留，本片补足后续阶段，不改写旧报告结论。

## 本次实际终态

加强同一测试，待首次Worker返回且其heartbeat已join后，只替换db/worker模块的时钟代理，从读出的实际lease之前推进到之后；不改写Run、lease、合同、上下文或操作状态，不sleep。使用现有Store.claim和Worker.process/once：

`RUNNING → WORKER_LOST → RECONCILED(QUEUED) → CLAIMED → FAILED / VERSION_CONFLICT`

child的lease归零，fence由1到3，result仍null。最终错误为“最新声明必须是明确拒绝”；恢复在模型循环前的冻结合同检查处停止。[完整初始/终态、事件与保全快照](raw/author-data/test_final_commit_rechecks_rej0/lease-recovery.json)。

父Run和child上下文不变；attempts、reservations、operations、operation_intents、local_effects、resources、grants、run_contracts、goal_card_versions、ordinary_correction_links、ordinary_owner_records、ordinary_owner_seals共12张表所有行前后相同。child原合成模型请求3，恢复模型请求0；既有VERIFIED保存、156字节MD及两条读取Grant保留，未新增保存记录或效果。文件SHA256仍为 `61e476dd4066650cc64f7a78b0b9a5f66861f9b827d36a7e17bebb739422db46`。[摘要](raw/author-meta/author-recovery-summary.json)。

项目metadata历史GET200显示FAILED；失效合同的完整Run详情仍GET409；已有授权的resource GET200返回原内容/hash。[实际HTTP回读](raw/author-data/test_final_commit_rechecks_rej0/terminal-http.json)。这份内容回读不是浏览器下载Blob。原Worker旧fence再收尾被拒绝；再推进两轮lease后，现有Worker.once无任务，终态和证据不变：[稳定性](raw/author-data/test_final_commit_rechecks_rej0/terminal-stability.json)。

动态证明范围是恢复模型0、全部保存相关记录和效果原样；没有额外dispatch spy。零工具dispatch属于生产代码在process初始合同检查即失败的控制流推断，不冒充新增动态计数。

## 精确执行范围

| 批次 | 节点 | 结果 | JUnit秒 / 墙钟秒 | 输入 |
| --- | --- | --- | --- | --- |
| 作者冻结9f7 | 加强终态1 + 正常MD/只读修正2 | 3PASS，RC0，无失败/错误/跳过 | 41.901 / 44.025 | 590个，前后相同、测试结束工作树干净 |
| 独立Git快照9f7 | 同3节点，未重试 | 3PASS，RC0，无失败/错误/跳过 | 43.463 / 45.492 | 591个，Gitblob及前后相同；额外一项是明确导出的既有goldfixture |

[作者原命令/RC](raw/author-meta/author-first-execution.json)、[作者XML](raw/author-meta/author-first-junit.xml)、[独立命令](raw/independent/commands.json)、[独立XML](raw/independent/junit.xml)、[独审结论](raw/independent/review.json)、[独立证明](raw/independent/proof.json)。独审为 `FINITE_REVIEW_PASS_NO_PRODUCTION_FIX_REQUIRED`。Ruff和diff检查通过：[检查](raw/author-meta/checks.json)。两轮是同3个unique节点，不计6；原断言基线不是新增第4个最终节点。

此前37项不在本轮重跑；此前作者额外SQLite增量迁移探针也没有重做，不扩大其独审或PG迁移结论。没有执行其他故障矩阵、P-B应用化、真实模型、真人/真实语义、PG、Windows、原生浏览器、独立worker进程重启、远端CI或部署。这里的新Worker仍共享原Store；收敛依赖Worker继续轮询并超过原lease，不承诺关机后继续执行。

## 原件与交付核对

本目录封存49份资料，含命令/日志/XML、原JSON、7个SQLite夹具、输入指纹、独审及复现辅助脚本，共52个文件、51条SHA256SUMS。[artifact-map.json](artifact-map.json)记录原路径、长度、原SHA及编码；SQLite采用mtime0 gzip，其余原字节保留，逐件解码核对。资料包含原始输出、派生审查和辅助源码，未混称全部为运行输出。

独审封存manifest20项，加manifest/sums共22件；原件逐件长度及SHA核对通过：[封印核对](raw/author-meta/independent-seal-verification.json)、[原manifest](raw/independent/raw-manifest.json)、[原SHA清单](raw/independent/raw-sha256sums.txt)。其清单中的SQLite路径指原未压缩文件，仓库压缩映射见artifact-map，解码后校验。

[开工核对](raw/author-meta/preflight.json)记录实际远端d4c、原8fc祖先、单一写入者、容量、default Git网络及22条保护引用。未访问旧满盘实例/旧bundle；旧独审报告未落盘的已知缺口未声称补回。最终交付SHA、远端及工作树状态另按实际推送后核验。
