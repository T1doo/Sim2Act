# Run通用入口：所有权前置修复

独审报告候选0325fc2 /执行041cf8ec有1项P2，SQLite/PG各51例48P3F；未发现响应正文泄漏或写入，但inspect/command/reconcile_operation在所有权检查前经csv_dag.is_job读取他人context/接受事件。原候选/证据冻结不改，独立dev/run-dispatch-owner-fix-20261008，基线0325fc2aa3429ed2f9df42e0b241390b182aabf8。

最小改动只在Store三个公共方法增加共用只读前置门：以run_id+principal谓词只取Run.project_id（不读context/result/contract/事件）；不存在/不属当前主体拒绝，再验证该项目owner。成功后保持CSV DAG→protocol→internal AppRun→ordinary原分派顺序、marker/账本检查、当前授权/源码/源数据/版本及恢复规则，不将前置门当作后续校验替代，不改变worker内部已租约授权的分派。无新锁顺序/Grant/角色/表/DDL/业务写/发布/真实模型。返回类型与授权用户语义保持。

先以真实SQL游标追踪复现三个失败，修复后要求未授权零关联账本/context读取及全表零写，包括foreign/missing及Run主体匹配但项目不属当前主体。HTTP及直接Store都测。真实四种已接受job验证inspect/command/reconcile分派、旧版本/重复命令和恢复；不伪造业务运行代替来源。必要双后端及最低CRUD角色验证，保留旧测试与900/240/150，不机械重复已通过条件算术/DOM/整套756。条件候选独审通过子项由父线程报告，本任务不冒认本地重跑。源码变化遵循旧证明失效政策，历史不改签。仅自有隔离临时资源，最终清理。普通push新候选交复审，不入dev/main，不强推/部署/凭据/安全策略变化，LIVE0，无新CI。
