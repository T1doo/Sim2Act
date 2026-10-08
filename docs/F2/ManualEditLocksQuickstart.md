# 单节点人工编辑保护候选：复现指南

仅自己的项目中已有固定CSV应用图；编辑保护不改变身份/Grant/系统权限，不是业务验收。已整合 dev/f1-foundation，独审限定通过，原候选分支保留；范围与未覆盖项见[整合记录](ManualEditLockIntegrationLog.md)。LIVE=0/mock，正式发布关闭。

1. 打开已有CSV应用，在原交付图区域显式保存/读取图，再点“读取锁状态与历史”。
2. 在“单节点编辑保护”选 action:aggregate，选“锁定”，核对图与节点版本、锁修订，手动勾选确认，再提交。确认不会自动勾选。
3. 读回持久回执后旧图证据清除。显式重新派生图，再用原列绑定入口提交amount→quantity；应收到LOCK_CONFLICT且内容保持。
4. 再读取图和锁状态，选同节点“解锁”，重新明确确认后提交。显式重派生图，再以新键提交列绑定草案，核对精确patch指纹并执行原有限检查，合成病例old amount=30、quantity=15。它仍是未验收候选，语义UNKNOWN/用户PENDING/发布关闭。
5. 接受响应丢失时保留原冻结body/key，使用“原键恢复未知锁回执”；不会先读已失效旧图而阻断恢复，也不新建锁修订。切换节点/操作/图/项目/身份清确认，延迟响应不能写入另一上下文。整页刷新后读取有限持久历史；不声称自动持久化原意图。
6. 历史SUPERSEDED只说明过去提交被后续锁变更替代，不代表当前锁；SOURCE/权限/源码变化不能复用旧证明。撤权/项目转移不允许用解锁改变权限，不提供管理员强制解锁或跨项目继承。

公开接口沿用 `/api/projects/{pid}/apps/{aid}/delivery-graph/manual-locks`：GET状态/最多50条按键排序历史、POST严格锁操作；GET `/receipt?request_key=...`读回原键。无任意图/代码/权限参数。锁/解锁必须提供当前graph fingerprint+revision、节点id/revision/content fingerprint、expected_lock_revision（不存在为整数0）、locked严格bool、request_key及consent=CONFIRM_EXACT_PROJECT_EDIT_LOCK；锁变化后须显式新派生。客户端提供的哈希不是权限证明。状态相同的新键拒绝，不额外递增锁修订。

开发者采用既有锁定Python依赖，可在自有临时目录运行：

```bash
LIVE=0 SIM2ACT_LIVE_ENABLED=false .venv/bin/python -m pytest -q tests/test_manual_locks.py --basetemp=/tmp/my-owned-manual-locks
```

页面专项需developer Node与自有jsdom30.1.2（不是产品新增依赖）：设置NODE_PATH到自有node_modules，再运行tests/test_manual_locks_ui.py。PG只使用本人隔离SIM2ACT_TEST_DATABASE_URL；角色fixture会创建/删除自有test schema/最低CRUD角色，禁止业务库。原Node150/Edge240/Windows900标准不变，HTTP/JSDOM不等于原生Edge或布局验证。完整冻结范围见scope.json及ManualEditLocksLog.md。
