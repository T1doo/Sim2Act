# E17 内部持久 AppRun 工程证据

范围及接口：[PersistentAppRuns.md](../../F2/PersistentAppRuns.md)。基线1149816，事前范围7e122c7，内部固定声明式纯计算与原子类型化结果账本，正式发布/实际部署关闭，模型0。

初版接入现严格 FrozenRunContract 的 acceptance_version/runtime_id Literal/格式不符，实际 enqueue 被 Pydantic 拒绝且无写入；已使用现F1调度envelope字段并最小支持已有appruntime身份格式，不增加grant，内部验收证据独立保存。不是放宽授权或修改旧历史。

独立合成实际复现：不同call_id未知操作仍误SUCCEEDED；可改plan.source生成另一份CSV结果；输出resource_id/column/source_hash可伪造；failure rawbinding引用可把另一instance正常同步AppRun历史SUCCEEDED改为FAILED。均在未提交开发树，非已发布事故。主开发初轮22PASS/4FAIL（3未知状态、1plan篡改）记录真实负例失败，后修全Run未知门、当前冻结source/完整plan与output身份校验、独立accepted快照锚点下的失败写入；新持久负例保留。绑定已损坏无法安全定位原AppRun时不猜测修复，残留历史仍不可回读，主Run记录拒绝。

定向真PG/真实子进程、完整SQLite/PG、独立修复复验、精确ServerCI结果待各自完成记录，不预写成功。原AT05保留，AT17 OPEN（只读sum不证明preview写隔离），F1/Win11/完整P-A/P-B/AT10/protected browser和正式发布门不提升。

[定向真实PG JUnit](target-pg.xml)：35PASS/1旧警告31.11秒，含4真实独立worker子进程；随后加2个lease/budget负例由完整aggregate覆盖。测试账户为临时最小CRUD角色，无DDL/新Grant；before_commit实际os._exit73后lease失效，另一全新worker恢复且一次result/VERIFIED receipt；after_commit实际os._exit74后重开SUCCEEDED且无重排/追加；hold窗口独立heartbeat>初始lease、competitor不领取，parent control事务可提交、最后pause/cancel无结果。不是外部副作用或通用写动作恢复证明。

[独立只读复验](independent-review.md)：最终33PASS/4PG专用SKIP/1警告12.29秒，源码/test hash已核对；未知门/plan+source metadata/失败绑定三组关闭，原AT05逐字保留。主开发全SQLite [JUnit](sqlite.xml)319PASS/20PG或平台SKIP/3旧Starlette/Pydantic警告59.52秒；ruff/mypy20源模块/JS syntax/diff通过。完整真PG与精确ServerCI待各自終态记录。

首轮完整LinuxPG338PASS/1WindowsSKIP/3旧警告150.41秒，包含全部37新项；随后加最小PG角色enqueue binding/控制/resume/worker业务CRUD必要检查，验证新表INSERT也由实际最低角色完成。该额外检查和最终完整aggregate另记录，原35target-PG只是先前定向子集，不冒充完整最终用例集。

[新绑定表最低角色enqueue/控制/worker CRUD](enqueue-role.xml)1PASS/1旧警告0.95秒，无DDL/newGrant/模型attempt。源码/service hash仍与独立审查一致；最终全用例集38项，完整aggregate及精确ServerCI下一步。
