# OPEN 记录内容更正：有限工程交付

产品/测试/合同提交 `fa244834efe50358459340b30f5a988a39089164`，父提交 `441fdaa251fd2797857f557a16590946b22756ec`。合同及原 V5/F2 条款见 [交付说明](../../F2/LocalRecordContentEdit20261020.md)。仅两产品文件；无新工具/表/写授权，旧默认定义字节独审比对相同。显式新合同允许 OPEN 内容更正，原 ID/状态/历史保持，新事件与回执同事务追加；恢复旧内容是新显式事件。

## 实际执行

| 范围（分批实跑，不是完整回归） | 唯一 pytest 节点 | 结果/秒 |
| --- | ---: | --- |
| 新 API/普通 NoModel Worker/冷读/取消/真实保存后故障/旧 fence/私有试写 | 6 | 6 PASS / 9.73 |
| 新完整 actual HTTP/JSDOM 页面链 | 1 | 1 PASS / 4.19 |
| 原 v1 真实保存 helper 后故障回滚 | 1 | 1 PASS / 0.89 |
| 原 v1 A/B/DONE、派生读撤权私有正文屏障、原页面 flow-recovery | 3 | 3 PASS / 5.51 |

作者共 **11 唯一节点，11 PASS，0 FAIL/ERROR/SKIP**；每批有一个原 Starlette/httpx 弃用 warning。没有重新运行已通过的新节点凑分母。命令分别使用 `.venv/bin/python -m pytest tests/test_local_record_content_edits.py`、页面参数 `[content-edit]`、原 helper 单节点及三项精确回归；完整节点与原执行时刻在各批 JUnit。原 stdout/JUnit 均以原字节 gzip 保存在 `new-backend/`、`new-page/`、`v1-helper-fault/`、`v1-regression/`，不是重新生成报告。

新页面实际 **79 检查、72 HTTP（12 POST）、81 资产读取、3 次冷启动、4 次冷 Store 普通 Worker**。完整保存应用/内部版本/实例→A/B→更正 A→原 key 丢接受回执 GET 恢复→冷页 EDIT 恢复/输入 ABA 迟到保护→A DONE；两原事件与 B 保持。143 输入前后零差异，见 `new-page/` 的 source-before/after/changes、info、page-result、完整 HTTP/IPC、Worker 原件。JSDOM 不是原生视觉。

新后端从真实 JSON 事件独立折叠，固定 oracle 不调用产品 fold；另核同库新 Store GET 全表零写、显式还原内容追加事件、DONE 拒绝、空/无变化/三层 CAS/旧 key 异参/旧合同拒绝。取消、真实 helper 已保存后注入故障、失效 fence 均保持原集合和旧资源/回执；私有更正不改变业务实例。测试数据与凭据均显式 synthetic/NoModel，无真实模型请求。

## 独审及边界

非作者设计独审后实施；最终 **LIMITED_ENGINEERING_PASS，无 P1/P2**。独立实际 API 补充跨实例409、同 owner 跨项目409、另 owner403，每例全表零变化、0 接受 EDIT，完整 trace/raw stdout/脚本/result 与最终报告在 `independent/`。另独立比较旧 HEAD 默认 definition/request dump 原字节不变，10 种畸形 EDIT 均拒。后者脚本为执行后保存副本、stdout 为工具记录转录；三次前置 setup 错误仅工具记录，没有伪造原始文件或补跑。API 初探针因 reviewer 将正确 POST201 误期望200，在 fixture 阶段停止；原脚本与原始错误保留，修正测试期望后 fresh fixture 一次完成。详见 `independent/PROVENANCE.md.gz`，不把 setup 错误归产品，也不宣称全程没有错误。

作者首次单文件 mypy 有1条新类型推断错误，补显式模型类型后通过；没有产品 pytest 红轮。npm 首次安装因默认 cache 不可写失败，指定 `/tmp` cache 后使用原 lock 安装成功，两原始日志保留；未改权限或锁文件。最终 Ruff、单文件 mypy、两 Node syntax、pip check、git diff --check 通过。`source-sha256.json` 核最终产品与实际页面输入、独审产品 hash 相同；`MANIFEST.json` 列62份封存原件的压缩前后 hash。

旧 v1 合同仅指本次软件下仍按原命令运行，**不证明旧软件 Release 的迁移兼容**；原软件实现指纹、批准/权限/租约/fence/取消门未放宽。没有 PB/G0、paired/validator、真实模型、PG、Windows/native、CI、真实语义/owner 或正式发布验收。原完整 PB FAIL_NOT_ACCEPTED、W5/G1/finalguard NOT_REACHED、永久取消的旧窗口等状态保持。
