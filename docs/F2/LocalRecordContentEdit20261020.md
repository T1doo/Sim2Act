# F2-T06：显式更正 OPEN 记录内容

本片接续 `441fdaa251fd2797857f557a16590946b22756ec`，属于原 [V5 产品 §3.2、§8.3](../平台产品设计.md) 的应用实例本地结构化记录读写，以及 [F2-T06](../分阶段开发计划.md) 的真实成果与本地数据。原 `local_record_apps.py` 仅接受 CREATE 与 SET_STATE；后者强制标题/正文不变，因此保存后的录入错误无法更正。没有新增模型家族、执行器、表、身份或写权限。

设计由非作者独审后实施：只更正 OPEN 记录的完整标题与正文，记录 ID/状态保持、修订加一、不可变历史追加。DONE 不能编辑或重开。至少一项内容必须改变；标题和依据不可空白。恢复原内容也是另一次明确更正，不能删除或覆盖旧事件。

## 用户输入与结果

新建本地记录应用时，用户可明确选择“允许有依据地更正 OPEN 记录标题和正文”。API 对应 `content_edits: "OPEN_RECORD_CONTENT_V1"`；省略时仍生成原 v1 合同与命令集合。选中后精确 definition 使用 `local-record-input.v2`，新增 EDIT_CONTENT schema，另行沿用原内部 Release 预览/确认和实例创建。

在已有实例选择“更正 OPEN 记录内容”，明确选择原记录及修订，填写新完整标题、正文和依据。原 `/api/internal/record-instances/{iid}/previews` 接受：

```json
{
  "command": "EDIT_CONTENT",
  "record_id": "record_<server-id>",
  "expected_record_revision": 1,
  "title": "更正后的标题",
  "details": "更正后的完整正文",
  "reason": "明确的录入更正依据",
  "expected_revision": 1,
  "expected_data_version": 2,
  "expected_release_fingerprint": "<exact-release-fingerprint>",
  "request_key": "<original-key>"
}
```

这是字段说明，示例 ID/fingerprint 不可执行。预览仅封存意图；再次明确确认才接受原 durable Run。普通 NoModel Worker 经既有 `artifact.save_text` 保存规范 JSON，与原 Operation/Receipt、typed 数据、集合 CAS 和终态同事务提交。新 EDIT 使用 `local-record-event.v2`，原 CREATE/SET_STATE 事件格式保持 v1；两种事件的冷读均重新验证完整历史与授权。每次保存仍产生原工具的两条成果读取 Grant，不新增写授权。

## 拒绝、取消与回退

旧 v1 definition/Release 不接受 EDIT；不把新能力注入已冻结旧合同。原软件实现指纹与审批门保持，未实现或声称旧软件实例自动升级兼容。

旧实例/集合/记录修订、错误作用域、DONE、空标题/依据、无实际变化、未知字段均拒绝；旧 key 异参冲突，同 key 恢复原 Run。未知接受结果仅原 GET；冷页按原数据版本历史找原记录，不能拿最新修订伪造预览前置。页面每次编辑（含改后撤回）、选择、身份、项目和导航守卫继续生效。

排队取消不产生事件；保存后故障或失效 fence 使本事务业务效果回滚，保留原失败/控制账本，不擦除以前成果。已提交成功事件不能取消掉；用户需要恢复旧内容时，以当前修订另行预览并确认一次 EDIT。私有试写沿用独立存储，不能自动晋升业务结果。

## 独立 oracle 与实际资格

确定性 oracle 从实际 JSON 历史独立折叠：CREATE A/B → EDIT A，期望 A 为新标题/正文、OPEN@2，B 的每个字段与原始事件/资源/回执保持；同库新 Store 冷读只读不写。再明确恢复 A 原内容并 SET_STATE，历史均保留。另测严格输入/三层 CAS、原 key、防重复、旧合同、新事件版本、取消、真实保存 helper 后故障、旧 fence 和私有试写隔离。

实际页面使用原 HTTP/脚本、普通冷 Store Worker，完整创建应用/版本/实例、A/B、更正 A、丢接受回执原 GET、三次冷启动、EDIT 恢复编辑 ABA 保护与更正后 DONE。工程结果见 [证据](../evidence/local-record-content-edit-20261020/README.md)。JSDOM 不是原生视觉；没有真实模型/业务语义、PG、Windows、CI、正式发布或 PB/G0 完整链验收。
