# F2-T06：本地记录收集与版本化状态更新

基线 `5322dfd7f8c6686be29c9989d2f02fb6f54cfc28`，普通开发分支 `dev/local-record-state-20261018`。原方案要求本地结构化记录写入、唯一操作约束，以及业务变更和操作回执同事务提交。本切片提供固定表单应用作为合成工程任务族，不声称模型生成、自然语义验收、正式发布或完整 F2-T06 完成。

用户在应用工作区保存本地记录应用，从统一应用/使用目录打开；明确准备、确认内部 Release，再明确创建并选择实例。创建只接受标题与正文，服务端分配稳定 `record_id`，初始 `OPEN@1`。更新只支持明确选择原记录、原修订、DONE 和变更依据的 `OPEN → DONE`，结果为同 ID 的 `DONE@2`。当前集合与不可变历史分别回读，DONE 只代表业务状态。

每次写入有类型命令、原 key、实例修订、集合数据版本及 Release 指纹。预览只保存双份封存意图，不创建 Run、成果、Grant 或业务数据；再次明确确认才创建原有 durable Run。未知只通过原 key GET 核对；不自动轮询或重发 POST，未找到不代表安全重试。最多 32 条记录、64 个事件，同实例仅一条未结束写入。

复用 `artifact.save_text@1`、项目所有者与项目运行身份权限交集、`write_text_artifact(..., artifact_format="json")`、正常 Worker、Operation/Intent/Receipt 和实例 typed 数据/CAS。没有新 executor、写 Grant、Principal 或数据库表。每次保存仍由原工具产生两条成果 `resource.read` Grant；不将“没有新增写授权”写成“Grant 行数不变”。工具输出仍仅为 `{resource_id, hash}`，typed 数据仍为 `{result, release_ref}`。本版本适配器负责固定命令到规范 JSON 事件的映射和独立折叠，不将工具输出伪装成业务记录。

规范 JSON、派生读取授权、local effect、真实保存回执、typed 追加、集合 CAS、最终 Run/AppRun 状态同事务提交。发布/执行按当前软件与工具定义冻结；接受与保存都核验命令、版本及期限，最终提交前检查权限、fence、租约及停止状态。读历史私有正文前，先对独立索引所引用的全部成果做当前授权。旧共享 API 在私有正文前拒绝此家族；单个标记删除或污染不能降级进入旧路径。

最小验收使用合成 A/B：三次原 Worker 写入 A、B、A→DONE，从实际 JSON 历史独立折叠出 A DONE@2/B OPEN@1，首事件与三组回执保留。另测严格类型、预览零业务效果、冷 GET/精确重放、防重复、双 CAS、账号/项目/实例/旧家族隔离、SQL 读取屏障、撤权后元数据取消、真实保存 helper 后故障整体回滚。页面通过实际 ASGI HTTP、实际脚本与 JSDOM 执行完整创建及三次运行；导航与撤权分别计量。

资格和失败历史以最终证据为准：SQLite/mock/NoModel，真实模型零请求。Windows、原生浏览器/设备、PG、远端 CI、真实语义和场景未执行。旧满盘环境最终独审缺失与取消窗口 NOT_VERIFIED 保留。本文件为实施合同，最终提交及实际分批结果另附证据。
