# P-A 合成规范引用清单 — 实际证据

合同及限制见 [PASpecChecklist20261012](../../F2/PASpecChecklist20261012.md)。

本目录保存实际作者/独审日志、JUnit、合成传输、SQLite、逐表回滚/权限求值证据与完整源码散列。完整 archive 的文件级 SHA 清单与最终 SHA 在全部进程结束后封存。

## 原失败与修复链

- 作者 r1：家族检查工具未经过旧全局 parser；r2：嵌套 Pydantic schema 不适合原简化 validator；均拒绝无制品。
- r3：重复完整合同导致三轮 wire reservation 超出原 64000 总封顶；压缩重复声明，预算不扩大。
- r4：终态 lease 清零后错误调用运行态 guard，按规则回滚；修复终态投影与原 lease 检查。
- r5：新制品只对用户/app runtime 有 read，普通项目 reader 无授权，GET 403；采用精确完整验证后的 app-job 制品 GET，不扩大项目 read。
- r6：4 场景 PASS。r7：4 PASS 后测试自身缺 Store import，已修。r8：21 PASS 后篡改内容实际正确拒绝 400、断言仅期待 409，已修断言；这不是允许篡改通过。
- UI r1：冷 worker 三步后重复完整来源验证超过 30 秒 lease，末保存回滚；保留日志，减少同一事务内的重复完整重放，保持 lease/预算。原 profile 98 次嵌套 origin 验证、16 次 bound、12 次 commit_guard 均保留，不宣称稳定平台提速。
- UI r2：所有实际 22 检查 PASS，但 Python 自设 ≥23 断言错，改为与实际合同一致的检查门；r3 三场景 PASS。
- literal-r1：93 PASS、35 FAIL，其中 34 缺 NODE_PATH/JSDOM，1 在核心源码仍变化时 scope-late 来源指纹失效；不据此签最终，冻结后正确环境重跑。
- qualification-r1：20 PASS、2 FAIL；清单错误多计 config.py，与既有排 config.py 的 implementation inventory 不同，保守拒绝两旧锚；按原算法 70→71 精确列单修正，不改算法/旧锚/CHANGED。
- 独审首轮 S1–S7 是静态发现，不能记作动态 FAIL；实现修复和静态原快照保留。两次因发现实际问题主动中断的 selected 轮不能计完整验收，XML 无名占位不能加 PASS。
- 独审 66d7 extra15 实际 **13 PASS / 2 FAIL**：末 SPEC_COMMITTED 回调给原 Attempt.parameters 或 STATE event.data 增添未用于语义检查的字段，保存仍提交。已补入口 b.audit_fingerprint 与 final_binding.audit_fingerprint 精确比较；两个作者定向回归实际 PASS，独审重新执行原探针。
- 作者 final-r1 主动中断，已完成 288 PASS / 1 PG 前提 SKIP；final-r2 主动中断，实际 exit 2，完成 234 PASS / 1 PG 前提 SKIP、429 源码项前后零差异。两轮整体均 INTERRUPTED，未加总为最终验收。
- 独审 30fe capacity 实际 1 FAIL：合法 16 条人工 unresolved 被附加一条元数据后触发 GoalSpec 17>16 验证异常，不能 enqueue。原异常/DB/逐表见证保留；card 身份、版本与指纹已在独立 spec_goal 封存，修复移除冗余元数据、不丢人工条目、不扩 16 条上限。作者定向实际 Worker 1 PASS，资格 r4 22 PASS。
- 独审 66d7 selected 主动中断：完成 58 PASS，exit 2；其 extra15 的 13 PASS/2 FAIL 为单独完整失败轮。最终另跑 fresh 集合，记录真实退出码、完整 source map 与唯一节点，不累计中间轮。

作者 final-r3 及独审 a396 selected 遇本机 /tmp 临时盘 ENOSPC；作者 runner exit 1、pytest/XML/after-map 写入不完整，独审 selected exit 120，均 NOT_COMPLETE，不补造通过分母。原 stdout 包含 F/E，但明细未成功写出，不凭进度字符追认逐节点 PASS/FAIL 或每个失败的根因。独审 extra16 已在该故障前实际完整 exit 0/16 PASS。只迁移本任务两处证据到同环境 /workspace 空闲盘，逐文件与 pytest symlink 完整比较 4061/4923 项零差异后，以原 /tmp 路径链接恢复；不删其他旧项目、不改安全或网络设置。原盘错与恢复回执入档，恢复时 429 项源码零差异，HEAD 未变。最终作者另跑 fresh r4；独审 selected 另跑 fresh r2，原 extra16 用相同冻结源码桥复用并单独记录，不能声称 79 是一次单进程执行。

早期作者 pytest 默认临时目录会被后续 pytest 自动清理，因此不声称所有早期红轮 SQLite/页面 JSON 仍可读取；持久日志、实际 Git 修复链、控制台观察和独审原红例逐表完整记录仍保留。最终作者与独审使用固定 basetemp，完整原始证据随 archive 封存。

## 验收界限

全部 provider 是合成 MockTransport；私有手工 gold 不进入 prompt/工具反馈，引用与显式标记检查与自然语义分开。真实模型/费用/用户技术规范/人工语义及完整 P-A/P-B、PG、Windows、native、真实旧用户库升级、wheel 安装、部署/CI 均 NOT_RUN。原取消精确安装窗口资格永久 NOT_VERIFIED，不重试受拒路径。

## 复验方法与静态结果

冻结源码 `a396acb7fbfcb7393ae8cbcd4aa42a53b8d8e3a8`；资格 candidate 为原核心修复提交 `d91586745b543d4ff9f26c2ece5415b8279fc0bc`，manifest 71 实现文件（按既有规则排除 config.py），pin `5fa7b0bfd6a805436daaeda316b746d724e45bac7aebe8775c51e33f8d0ad159`。原 anchor 文件 SHA、两个旧源 fingerprint 及原 CHANGED 集合保持；未知来源、完整任意实现字节或 manifest/pin 变化仍拒绝，旧用户批准不自动迁移。

作者最终使用 `run_final_r4.py` 的 14 个相关模块、原 pytest 断言、固定 basetemp、真实退出码及 429 个 Git 跟踪源码/测试/配置项前后 SHA；环境仅指定本分支 `src:tests` 与已装 JSDOM 的 NODE_PATH。独审另有原 15 个独立探针加容量边界，选集和重叠以实际 XML 为准。不是全仓工程测试，不把多轮或重复节点相加。

最终改动文件 Ruff PASS；全树 Ruff 实际 9 项既有问题，mypy 实际 5 项既有问题（status_report.py 3、tools.py 2，检查 72 实现文件），均保留原日志且不声称全树绿。未安装新依赖。

## 已完成的独立复验

[最终独审报告](independent-final/FINAL_REVIEW.md) 为 **LIMITED PASS**：fresh recovered selected63 为 63 PASS/0 FAIL/ERROR/SKIP，pytest 479.96s、runner 481.80s，exit0；原完整 extra16 为 16 PASS/0 FAIL/ERROR/SKIP，pytest 155.13s、exit0，外层墙钟 NOT_RECORDED。79 个唯一节点来自这两次完整执行，63 与作者模块重叠，16 另有部分行为重叠，不加总到作者分母。429 源码项 before/after 及两个运行之间完整桥均零差异；独审自身测试进程0。报告 SHA `11d8de712d699e0d24937d192056386ce722d1724e10d7360ad1d662807d2c28`，最终 [manifest](independent-final/manifest.json) SHA `363d591b86e5e236bdb7992e0dac613ff3db64423d856cf3ea7351bdf3b6dfe1`。

三个独审 HTTP/IPC/JSDOM 页面实际检查为 22/22/26（70 总检查），每场景两次开页、40 次资产 GET/20 种资产全部源码 SHA 匹配、3 次合成消息；不是 native 或真实 provider。报告脚本初次把 pytest 的 current 链接重复算作第四场景导致断言错误，原脚本/错误保留，仅修报告去重，不改产品、测试或轮询断言。空间恢复文字补正前的报告/manifest 原字节也保留在 archive 的 superseded 目录，精确区分 reviewer 无 escalation 与根代理三次自动获准的沙箱恢复动作。

## 最终作者轮与源码桥

作者 **final-r4 单次 379 selected：378 PASS / 1 SKIP / 0 FAIL/ERROR，真实 exit0**。pytest1705.19秒、runner1706.696秒。37新后端+3新页面均PASS；原两续用模块58+42=100节点、资格22、其余相关模块精确数量与全部节点见 [final-validation.json](author/final-validation.json) / [原JUnit](author/final-r4.xml) / [实际回执](author/final-r4-receipt.json)。唯一SKIP为 `tests.test_spec_checklists::test_application_crud_role_no_ddl`，原因为 Application-role subprocess regression requires explicit isolated PostgreSQL，未将它改成PASS。

作者规范页面也22/22/26=70检查，每场景20独立资产源码SHA匹配；原JSON/wire/SQLite在author archive里。作者429项before/after完全一致；与独审429项逐路径/散列桥也零差异，见 [source bridge](author-independent-source-bridge.json)。独审source JSON另含branch/head包装，文件自身SHA与作者纯映射JSON不同，不声称两种JSON字节相同。作者/独审进程结束，之后仅补文档/证据，不再修改冻结src/tests/UI/资格。

完整归档保留当前所有非缓存文件、目录和链接，包含SQLite及原始失败，不包含可重建__pycache__/.pytest_cache；[逐项归档校验](archive-verification.json) 从实际压缩包流再次核文件大小/SHA、目录/链接类型和目标。早期已自动清理的DB不在archive，不补造。

## 实际归档封存

- [author complete archive](author-complete.tar.gz)：7273项（5993文件/999目录/281链接），49298050字节；SHA256 `4ba46c20252c055af1df36e52a9b32d3324fb19ced463559a34def18e72e5fd1`，实际从包中复核7273项全部一致。
- [independent complete archive](independent-complete.tar.gz)：6950项（6599文件/294目录/57链接），32656054字节；SHA256 `41c0e5f45422edbba4a131cdc7aa6bc592867dbb60b1a5a33e8b223c9b9cbb3e`，实际从包中复核6950项全部一致。

[作者全清单](author-full-manifest.json)、[独审全清单](independent-full-manifest.json)和[交付文件清单](artifact-manifest.json)提供每个保留字节及链接的检查依据。源码冻结完成后最终提交只含文档/证据；正常独立开发分支推送和保护分支/原owner草案复核由交付回执记录。
