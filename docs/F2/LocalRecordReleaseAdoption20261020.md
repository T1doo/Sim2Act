# 本地记录实例显式兼容采纳（2026-10-20）

接续原 [F2-T08/AT-16](../分阶段开发计划.md)：业务数据独立于不可变 Release，新版本保留实例及历史。基线 `3312d0cd79f5d148351adc55314680d84fba1d2c` 的本地记录实例只能固定首个 Release；已有 A/B 的 v1 实例不能采用 [OPEN 内容更正](LocalRecordContentEdit20261020.md) 的 v2 能力。本轮补上这条用户闭环，不增加新执行器或通用版本迁移需求。

## 明确范围

只支持**本补丁软件新建**的业务 v1 实例，一次显式采纳同应用的精确 v2 Release（`OPEN_RECORD_CONTENT_V1`）。软件指纹仍对全部 Python 实现逐一精确核对，不能据此迁移基线3312或更旧安装创建的实例。私有试写空间、重复切换、降级、任意字段变更及未知能力均拒绝；没有放宽为任意 revision 或任意历史 Release。

页面操作：打开本地记录应用 → 勾选“此新版本明确增加 OPEN 内容更正能力” → 准备并另行确认新 Release → 只读刷新目录 → 明确选择原业务实例和目标 v2 → 准备采纳 → 核对源/目标版本、数据边界与集合指纹并另行确认 → 只读刷新目录及同一实例 → 更正 OPEN 记录，仍需逐次预览、确认及原 Worker 执行。

新版本创建不会自动采用；采纳也不会自动更正数据。采纳只更新原实例的 Release 指针和 revision=1→2、消耗精确批准并追加成对元数据回执。记录 ID、data_version、所有历史事件/typed/Run/Operation/资源/工具回执与 Grant 均不因采纳而改变。后续更正使用原 `artifact.save_text` 与正常 NoModel Worker，并正常新增一次不可变事件。

## 合同与保留

- 原应用定义和创建锚不改。Release 从其唯一成对 PREPARE 的原请求精确派生；v2 仅增加固定 EDIT_CONTENT 类型合同与固定硬条件，动作、Goal、权限和数据 schema 保持。
- 采纳准备/提交各重读完整投影与当前全部授权，拒绝所有未终态/未知 Run。批准冻结原实例 revision/data_version/源和目标指纹/完整历史前缀指纹；提交原项目锁内重推导、CAS、消耗批准与追加成对回执同事务。
- 历史源版本使用 revision1，目标使用 revision2；事件按精确数据边界选择二者，Run 前置 data_version 受相应边界约束。每次完整投影实际重算并比较批准冻结的原前缀指纹，未缓存可变身份或减少授权扫描。
- Worker 在任何保存前重新读取当前实例指针与 revision，历史只读上下文不能变为旧版本写入权；最终实例 CAS 也核同一指针。旧成功和零结果 Run、原创建 key 均继续按原版本验证，旧未受理预览不能在采纳后提交。
- 原 key GET 可只读恢复过期/已消耗批准。未知提交不自动重发或换 key；页面保留原请求并复用账户、项目、工作区、实例、读取及编辑代次隔离。客户端独立折叠混合版本历史并重算原前缀指纹。

事务沿用原 Store：SQLite `BEGIN IMMEDIATE`；其他数据库沿用原项目行锁与条件更新，不另造锁服务。核对了 [SQLite 事务说明](https://www.sqlite.org/lang_transaction.html)及 [SQLAlchemy FOR UPDATE 官方接口](https://docs.sqlalchemy.org/en/20/core/selectable.html#sqlalchemy.sql.expression.Select.with_for_update)；这不构成新 PostgreSQL 并发实测。

## 实际验证与独审

冻结产品字节及原件见 [证据目录](../evidence/record-release-adoption-20261020/README.md)。最终针对性 **10 后端 + 4 页面 PASS，0 FAIL/ERROR/SKIP**，分别17.629秒与21.346秒；四个页面不是原生浏览器，而是实际服务资产、ASGI HTTP、JSDOM、正常冷 Store NoModel Worker。

后端覆盖同 iid 的 A/B→v2→更正 A→冷读、独立折叠、B 与旧事件/制品/工具回执逐字节保留、采纳表差异仅批准/回执/实例指针；另核 stale/CAS、待执行、私有、他人、降级、旧预览、过期批准只读、历史 Release 篡改、重新封印的假前缀，以及特权夹具复活的旧 Run 不能产生业务写入。选择原 v1 动态授权/撤权与私有隔离回归，未重跑完整 PB 或全量矩阵。

新采纳页面73检查，实际53 GET/16 POST/3次 NoModel业务 Worker：两个相同指纹不同 ID 的 v1 Release（实例明确来自第二个）、v2 单独批准、采纳单独批准、提交丢回执原 key GET、原创建 key 冷恢复、旧 Run 原版本、独立混合历史、EDIT丢回执恢复、实例 ABA 晚响应拒绝。另三个页面回归更正、私有试写、导航；最终每例输入资产字节前后零变化。

源码独审发现并关闭两个 P2：按指纹误选重复 Release；原实例创建回执仍硬绑当前指针。均增加在同一实际页面用例中，未删原锚或放宽为任意 Release。最终源码无剩余 P1/P2；独审执行次数与原件核查范围在其报告单列，不代称独立重跑。

完整 PB 的既有 G0 首绑定37.279秒仍超过30秒租约，W5/G1/finalguard未到达；本轮不重跑、不调整门槛。旧软件迁移、此新采纳切片的 PG/真实并发、Windows/原生浏览器、真实模型与语义验收、完整 F2/R0及正式发布均未签收。前轮 PG 10/10 和整 job FAIL/缺失原件边界继续以其独立证据为准，本轮未开第三次 CI。
