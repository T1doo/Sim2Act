# F2-T07 单节点人工编辑保护合同（实现前冻结）

基线72563fa220c66dd142be5656c5468d177de8fede，独立dev/manual-edit-locks-20261008。依据V5产品§9.1—9.3、F2-T07/AT15；ColumnBindingPatchPlan“本增量不新增公开锁”是旧切片约束，不是本次用户新授权的禁止。仅当前用户自己的项目、固定data.aggregate_csv应用图既有单节点的编辑保护，不改变身份/Grant/角色/文件权限/安全设置，不添加管理员强制解锁/跨项目继承。

复用现有图锚、项目锁、delivery_graph_locks及requests账本；旧内部LockInput和记录兼容，公开严格模型另加graph_revision、lock_revision CAS、明确consent。图/节点/内容版本、当前授权/来源必须可信服务端核对；锁/解锁只是元数据提交，业务内容保持、候选未验收、发布关闭。单节点锁状态切换才写新revision，同状态新键拒绝；零记录lock revision0。公开意图与seal同事务保存；原键同参恢复先授权、核来源再读回，零新写；异参冲突。后来锁操作替代旧回执为SUPERSEDED，只作历史、不称当前证明。来源/授权/节点/源码变化旧回执失效。锁本身变化使原图失效，必须显式重派生才能新修改/解锁；图revision+lockrevision防ABA。原历史不覆盖、不重签。

API挂既有delivery-graph/manual-locks：GET状态/有限历史、POST严格显式单节点变更；GET/manual-locks/receipt?request_key用于原键恢复，键控制字符/代理码在SQL前拒绝。项目所有权/当前CSV能力/授权先于锁或请求账本读取。PG项目锁、SQLite现有BEGIN IMMEDIATE串行化；锁/修改/解锁实际并发只能提交有效基线，失败零写，无自动强制覆盖。已有Run不自动取消，遵循原版本失效处理。

原页面图节点区域展示锁revision，选一个节点、操作与未预选明确确认；切换节点/操作/身份/项目/版本清确认，延迟响应不得落另一上下文；丢响应保留原body/key，原键恢复绕开已失效旧图预读，新请求不得绕过。整页刷新通过有限持久历史查回执，不声称自动存储原意图。

必要双后端/实际HTTP DOM：锁定→重派生→原列绑定修改LOCK_CONFLICT且原文保持→解锁→重派生→新计划精确检查quantity15、oldamount30；同键、异参、UNKNOWN恢复、ABA、真实并发锁/修改/解锁、来源撤权转移/非CSV/旧内部记录与seal篡改零写。全表保护，原断言/依赖/900/240/150保留、LIVE0，无真实模型/部署/新CI。冻结精确源码、定向回归/作者检查、清理自有隔离资源，普通push独立候选交独审，未审不入dev，不冒认人工验收或真实gold。
