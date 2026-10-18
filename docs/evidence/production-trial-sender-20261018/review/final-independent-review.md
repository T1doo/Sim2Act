# 未安装 sender 控制器有限独立审查

结论：对冻结 `c6f946d4d5c90652dbc6ad9945499dc529cc8e4d`，未发现剩余确定 P1/P2；本次未安装、严格离线 sender 切片可按当前限定范围交付。独审执行的只有源码/Git/AST及原件解析，没有运行产品、pytest、Worker、HTTP、网络、SQL或打开数据库，也不背书未来推送。

## 冻结与修复

相对 `94fa765de11e1e3cc42dac9070a28ec9c2b47647`，仅 journal 私有同事务/历史锚提取、新 sender、新8节点测试三路径改变。旧135个非journal生产 Git blob 一致；137生产文件中没有其它模块导入 sender。原 journal 校验表达式、事务体、read scalar 锚与其它原函数 AST 桥通过。精确差异是原参数校验现在在事务内，前加 `c.in_transaction()` 断言。

四项独审 WIP P2 均在第一次资格执行前修正：capture 与 journal Outcome/attempted 跨链约束、EMPTY 从真实空 bytes 重派生、private capture 前 Run owner/project/runtime 标量门、跨IO固定原 Store/engine/settings/transport/worker 绑定。原发现与修复记录保留，没有把静态发现冒称动态产品失败。EMPTY 负例同时改 capture 与 journal 为同一 e64 SHA 并重算双seal，因此跨链一致后独立检验空体派生拒绝。

## 闭合原件

作者目录 `/workspace/production-trial-sender-20261018` 已封存。其 `sealed-manifest.json` SHA256 为 `86837696b72c0b460154f7d6a467a45b371c88d9671ce87728cdf02edf741c06`；独立逐字核验61非DB文件、388974B，清单自身另10244B。8物理 fixture DB 仅核 stat，未读取或重算其SHA。

原命令只执行 `tests/test_production_trial_sender.py`，240秒有界；JUnit、stdout与 execution 一致为8唯一节点、8执行、8 PASS、0失败，JUnit41.715秒、外层46.022090623秒。旧19/12节点没有重跑或计入分母。

705输入/137生产 before/after 映射完全一致，runner/guard 前后相同，3变更文件等于冻结 Git blob。当前699个非DB输入独立SHA匹配；另6个既有 `.db.gz` 资产仅stat与基线/冻结Git blob标识比对，未解压或读其内容，不能把这部分说成独立当前字节重哈希。

## 实际覆盖

- 正常路径确实调用既有 InternModel 到 exact MockTransport，原wire不重建；保存的264B原响应SHA与209B canonical ASCII几何独立复算一致。协议接受不等于业务语义接受，公开receipt无正文且 LIVE/dispatch/real_source/business_accepted 均false。
- marker提交后、guard前实际取消：handler为0，UNKNOWN/halt与null usage保留。guard后实际取消：原trace按guard结束→handler可能已发→取消提交排列，handler为1，usage8保留，但accepted=false/halt。数据库guard到IO之间的窗口没有被宣称原子消除。
- partial prefix 保存已知prompt5，completion/total保持null，UNKNOWN/halt，原key不重发。
- capture写入后 journal quota CAS 冲突回滚到已提交marker；原件保存了严格55表相等断言及pending回执，不留下已提交孤立capture。
- 两个真实退出窗口各运行一次发送子进程及一次全新恢复子进程，共4进程。命令原文均为venv Python `-c` 调用 `child_main`；计划退出17/23，恢复均0。marker前adapter窗口handler0；接收后归档前窗口handler1。恢复均adapter/handler/IO记录为空，原槽revision2、attempted=true、settlement=null、accepted=false，不退款、不猜费用0、不继承发送权。
- 原日志复算合计合成adapter6次（parent5+child1），Mock handler5次（parent4+child1），真实provider0。没有Worker.once业务执行或真实模型/费用请求。parent有HTTP/env/Intern及socket哨兵；child覆盖HTTP/env/五个Intern路径，**没有socket哨兵**。

严格全行保护/恢复相等由实际执行的测试断言、回执和镜像FP支持，本独审没有独立重算数据库全行。普通fixture保护明确排除受控Run/events，并允许本片新journal/capture元数据。正常与EMPTY节点在保存有效回执后故意损坏新pair来证明fail-closed；不声称所有最终DB处于全有效状态。

## 限制与审计工具记录

这是 strict test_only SQLite 的未安装控制器，没有API/Worker注册、生产来源producer、有效LIVE许可、真实sender安装或真实账户免费事实。旧生产默认拒绝保持。未验完整generation/source/cold/UI业务链、真实网络/模型/语义/费用、PG、Windows/native、远端CI或旧取消窗口。

纯文件审计首版因705输入包含6个旧 `.db.gz` 资产触发保守后缀断言；停在读该资产前，未打开DB。原脚本及实际重定向stdout/stderr保留为 `final-artifact-audit-first.*`，`audit-correction.json` 说明修正。修正版纯文件审计通过，无产品或测试变更。详细机器读复核见 `final-verification.json`，冻结AST桥见 `freeze-static-review.json`。

本目录以 `sealed-manifest.json` 封存全部其它普通文件；封存后停止写入。
