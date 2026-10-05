# F1 子进程环境隔离修复：本地证据

2026-10-05；基线8f7bbbed9d8b4d202a1fd14f7cf7f66fb3eba594。6145bb8及8f7bbbe保留为祖先。实际修复源码由承载本报告的本地Git提交及[source-hashes](source-hashes.json)固定；未推送，未做修复后的Windows复跑。

独立审计发现：旧WindowsCI把测试owner URL写入GITHUB_ENV，smoke及manage.py子进程默认继承，应用API/worker可见管理员URL。没有证据表明实际误用；这是实质配置隔离缺陷，不因旧CI绿色而放行。审计者独立确认远端df31fe9与公开run成功；日志需登录，旧111计数仍为开发方读取/归档证据，不称独立复跑。

修复：

- owner URL从GITHUB_ENV移除，仅job临时test-owner.env存储；Test阶段才加载SIM2ACT_TEST_DATABASE_URL，finally清除变量并删除临时配置。migration.env仅用于显式Setup/迁移并在Setup结束删除；runtime.env始终指向无DDL应用角色。
- smoke先保留报告路径等必要元数据，再重建自身环境，只载入job明确runtime配置；PowerShell subprocess.run使用显式application_environment。
- manage.py的API/worker Popen使用相同白名单：验证后的应用数据库/数据目录/模式/配额/预算；仅明确LIVE启用时传规范化应用token；系统/编码/必要TLS及代理配置单独保留。不透传任意SIM2ACT_*、测试owner URL、PGPASSWORD、CI凭据、PYTHONPATH或任意环境项。
- 环境边界不是OS沙箱：应用进程和job仍使用同一OS账户；本轮不新增用户/ACL隔离或声称防御该账户的任意宿主代码。本产品R0仍不执行任意生成代码或任意路径工具。

| 实际检查 | 结果/范围 |
| --- | --- |
| PostgreSQL专项test_process_environment + test_lifecycle | 4 PASS、1已有警告，6.09s；包含两个配置子进程、权限子进程、真实API/worker生命周期 |
| Linux完整SQLite夹具 | 112 PASS、2 SKIP、1已有警告，5.57s；[JUnit](sqlite.xml)，两跳过均需显式PG |
| Linux完整PostgreSQL17.9隔离schema | 114 PASS、0 FAIL、0 SKIP、1已有警告，16.66s；[JUnit](postgres.xml) |
| Ruff / mypy / diff | PASS；13源码模块 |
| 测试角色清理 | 新建test_app_*角色计数0；生命周期finally停止自有API/worker |
| 修复后Windows Server CI | NOT_RUN：Git认证阻塞，未重试push或换身份/地址/通道 |
| Win11原生、移动端、F1整体 | NOT_RUN/未签收；F2继续PLANNED |

真实子进程检查只输出/断言环境变量名和权限布尔值，不输出URL/password/token值。生命周期测试给父launcher注入合成owner/CI哨兵变量，psutil只将API/worker环境取为键集合，断言哨兵名称不可见；API/worker改用临时NOSUPERUSER/NOCREATEDB/NOCREATEROLE应用角色，验证实际幂等/停启/读回。另一个实际Python子进程查询自身角色权限、schema CREATE为false，并尝试CREATE TABLE得到42501；仅该用例的隔离schema受影响。迁移/test fixture owner没有当作应用角色。

配置回归为合成值，LIVE分支只构造Settings并检查子进程配置，不导入模型调用路径、不连接provider；确保合法应用配额/预算/模式、选定token与TLS/代理配置保留。所有外部模型调用0；只进行了被授权的本机PG及API回归。没有读取用户真实凭据或新增远端API请求。

恢复既有Git认证后的待执行步骤：

1. 保留本地文档及修复提交，核对原origin/身份/dev/f1-foundation；在原授权下正常同步，不force-push。认证未恢复时不重复失败操作。
2. 本次源码涉及scripts/src/tests，窄push触发既有windows-2025单job、15分钟、contents:read、无cache/artifact上传的MOCK CI。记录精确修复提交和run URL，监测到终态。
3. 核对Setup首次py-launcher/完整锁、smoke实际API/worker环境名称断言与运行角色DDL拒绝、工程114项（零PG跳过预期）、mypy13模块及always清理。数字只在实际结果出现后填写，不预写Windows PASS。
4. 把新版本结果交独立审计者；区分公开run/commit检查、开发方登录后日志计数、独立复跑三种证据。失败保留原始非敏感错误；不把Server成功当Win11或F1发布准入。
