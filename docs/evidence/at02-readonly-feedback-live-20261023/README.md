# 当前基线 AT-02 只读工具反馈：一次有限真实诊断

执行源码 **893a3de421dde9de6af82e42121058c709bffef6**，普通开发分支。
父级依据用户2026-10-23确认现有模型无消费、要求使用的决定，授权这一段新的最多两次请求。
旧探针已结束，其剩余额度不复用；本段两次均已消费，不能自动重跑。
费用依据仍为 **USER_CONFIRMED_NO_COST_NOT_OFFICIAL_VERIFICATION**。

## 实际链与结果

真实执行使用原 `InternModel.request_serialized_captured`，固定原Intern端点及 `intern-s2`；
未注入测试时钟。第一次模型自行产生唯一 `resource.read` 调用；原
`tools.authorized_read → Store.authorize → read_data` 在只读SQLite上检查原项目/资源及
user/runtime授权交集，实际读取一次固定合成材料。原assistant调用、同call id和实际工具
完整结果进入第二次请求，第二次答案为 `S2A-RO-2947`，与原材料严格oracle一致。
首请求不含该材料正文或预期答案；没有用开发模型、常量反馈或伪VERIFIED Operation回执代替。

| 项目 | 实际观察 |
| --- | --- |
| 终态/进程 | PASS_BOUNDED_READONLY_FEEDBACK；退出0 |
| 请求/工具 | 2次HTTP 200；1次实际只读网关读取；0重试 |
| 模型 | 两次返回Intern-S2，按原别名规则ACCEPTED |
| 请求完整UTF8字节 | 720 / 997，均不超过1988 |
| 输出token | 136 / 54，均不超过512；合计190 |
| 输入token | 356 / 298，合计654 |
| 总reported token | 492 + 352 = 844，known |
| 字节+输出预约 | 1232 + 1509 = 2741，不超过5000 |
| 总用时 | 19.113933098秒，600秒内 |
| SQL | 164条，仅SELECT及连接只读PRAGMA，0 DML/DDL |
| 清理 | 读engine已dispose；约0.000707秒；自有run进程无残留 |

预约是本地工程边界，不是provider tokenizer证明或输入token原生硬配额；没有根据用量推算金额。
代码要求首响应后至少6秒再发第二次；结果记录未单列第二次发送开始时间，不能独立重算精确间隔。
外层实际使用 `/usr/bin/timeout --signal=TERM --kill-after=10s 600s`，正常退出未触发强停；
cleanup十秒本身是观察门，外层监督提供总时限，不能把计时字段称为原生清理硬配额。

## 数据、门与持久边界

离线准备只在自有test_only SQLite创建当前55表schema及7条合成数据：principals2、project1、
resource1、read Grant2、synthetic quota1。Run/Attempt/Operation/App及其他业务表均为空。
初始化DDL及这7行DML单列为准备，不伪称整个过程零写。没有创建真实账户或数据库角色/权限。
`Store.resource`未使用，未授予aggregate_csv再撤回。

网络阶段mode=ro、query_only、SQLite authorizer与SQL拒绝器共同防写；检查后关闭读连接才HTTP。
完整DB文件、材料及sidecar存在性/摘要前后相同；独审已独立重算55表向量全部匹配。
独占claim绑定prepared/runner及原截止时间，file和父目录在adapter前fsync；预约先持久化，
失败/STARTED/UNKNOWN不释放，不通过换输出目录复用本case。技术ledger及报告独立写入，
不称全进程零文件写入。源DB原件仍保留，压缩副本解压与原摘要一致。

原生产resolver、admission、所有生产来源/授权门未改变；没有创建业务Run/Operation、运行G0、
P-A/P-B、Cold2、W5、Edge或PG。账号来源仍未验证，没有从用户确认伪造官方免费权益。
历史AT-02双主体真实链已认账；本次只复核当前基线窄子链，不签收完整AT-02、F2/R0或生产任务。

## 实现与必要离线测试

新增独立诊断脚本及针对测试，未改src产品模块。最终 **21 pytest节点PASS，1.15秒**，
Ruff与diff检查通过。覆盖两轮反馈关联/严格oracle、错资源/多工具/直接答案/错模型/截断、
未知与超额usage、第二body超额不发送、数据变更、原授权撤销及runtime关联、SQL/底层DBAPI写拒绝、
JSON转义凭据反射不保存/不hash、上游403不重试、全局期限、原claim及目录fsync失败零发送。
离线使用MockTransport；测试虚拟等待不冒充真实执行时钟。未重跑旧大套件或CI。

首轮14PASS/0.65秒及中间18PASS/0.82秒保留，不累计为53项覆盖。首轮Ruff1个未使用导入已修，
没有真实失败请求。源码独审阻断的claim父目录fsync已修并反例验证后才冻结运行。

## 证据与隐私

`result.json`保存最小安全请求/assistant/实际工具反馈及原usage；不保存header、凭据、
Settings、异常repr或私有reasoning。原始body和解码后JSON键/字符串在投影前检查凭据反射；
非法/部分/反射body不保存且不hash。归档和解压DB已检查不含现有真实凭据。
安全结果中的响应摘要由运行程序生成；原始响应未落盘，独审没有独立重算该摘要。
请求摘要、反馈、材料、源码和SQLite摘要可以独立复核。

执行前冻结、原claim/prepared、首请求精确bytes、stdout/stderr、三份JUnit、原fixture压缩、
独审和清理观察均在本目录。MANIFEST对应原字节。原case目录
`/workspace/at02-authorized-feedback-20261023` 与运行日志目录
`/workspace/at02-feedback-review-20261023`保留。源码冻结后未在执行中修改；本段没有重跑。
