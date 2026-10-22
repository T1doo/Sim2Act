# 独立只读审查回执

审查者 `/root/next_scope_review`，与主写入者分离；只读源码审查，未执行测试/数据库/网络/服务，未写入。

初审找到确定 P2：URL authority 验为回环后仍保留 caller query，psycopg 的 query host/service/options 可覆盖实际连接参数；不得在修正前连接。主线离线复现并保留 DBAPI 反例，无连接尝试。

最终源码限定 ACK：

- 拒绝用户 query 与 PG 环境覆盖，内部 hostaddr 固定回环；离线测试核最终 DBAPI host/hostaddr/options。需要已有密码，不因测试创建新凭据。
- 完整 55 表/全部列及 SQL NULL 见证、单事务导入和 typed digest 收口、只读 role/schema 资格、双独立连接实际等待见证、新 Store 同键重放与写故障回滚结构未见确定阻断。不调用原角色创建夹具或发 DDL/GRANT。
- 最后微差增加 service query 拒绝反例，两并发回执与新 Store 回执均用规范 fingerprint 比较，避免 Python bool/int 相等；未见新增确定问题。

限定：类型资格为类型家族，不是精确 DDL 等价；实际导入 digest 仍是门。pg_blocking_pids 只认事务等待，不单称 unique 竞争。实际 PG 始终 NOT_RUN/SKIP，离线 PASS 不能代签 PG 角色/并发/类型。冻结五文件哈希在最终运行前更新，主线已在最终运行后核不变。

本回执由主线按独立代理原消息归档，不把主线运行结果表述为代理亲自实测。

最终证据复核限定 ACK：代理只读确认最终 7 PASS / 1 PG SKIP / 0 FAIL、0.96 秒，五份源码哈希对应，55 表/96 行往返和回滚原件明确为离线 SQLite；未要求口径修正。代理未重跑测试或连接数据库。
