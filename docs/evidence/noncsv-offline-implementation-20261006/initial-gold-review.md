# 独立 gold 审查（离线，2026-10-06）

审核实际 V5 平台产品设计 §10.1 原450–458行及 NonCSVExecutionPlan、contract、oracle、prepare。无模型/网络/凭据/请求头访问，无仓库修改。

实际工具断言：全文 SHA e30251bda3f92a95728b79e002d75378669536aad1308304d73a3993dfbced78、选段 SHA 322cd3beba676156d2731c3953acdf53cf35f8c4d376113ad58c4a1c91804c3c、822 UTF8字节、四条 quote 对应452/454/456/458原行均通过。

四段逐字引用完整，因此原文未遗漏。义务标识不能单独证明全部细目：bind_validated_dependencies 应定义并核 Schema/动作/工具/提示/模型配置/检查版本全部六项；reject_breaking_delete_type_migration 应核删除/类型/不兼容迁移全部三项；compatible_upgrade_only 应保留 R0 限定；backup_migration_compensation_separate_evidence 应补独立操作，不只独立证据。回退三种对象彼此分离不能只靠两个概括标签推断。

oracle 是固定 gold 等值合同检查，不是独立语义验收。prepare 将自己生成的 gold 喂回 validate，正例是开发方合同自洽。纯内存实际复现：改变可信 contract.gold.quote 为原文不存在的合成句，同时改 candidate 并 render，validate=True。此为可信配置边界，不是未实现产品漏洞；当前 gold_owner_acceptance=PENDING 的措辞准确。

冻结建议：独立审查者先保存输入原始 bytes+SHA、source metadata、预期 span/quote 和原子义务 gold，gold artifact 和版本 hash 固定且与实施脚本生成路径分开。验证器必须读当前授权实际 source，重算 hash，按行独立核 quote，不能只拿候选与同一个可变 contract 比较。

后续合成任务若用 labeled Markdown，正式支持范围应表述为固定四标签规范段的确定性转换。标签驱动的义务映射不是从任意技术文档理解语义，不能标为模型提取或通用语义验收。

建议冻结两个独立合成正例：A 四已注册标签/规范段和新合成 source ID/version，输出逐字 quote/准确 span；B 使用相同允许标签但新段落 bytes、不同排布/行号和 source hash，确认没有回放 A，输出新 artifact hash。只有预先声明允许段落重排才把 B 重排设为正例，否则重排应拒绝。expected JSON 由审查者预写，禁止由待测 parser 自己生成。

否定条件：缺/重复/未知标签，标签位于代码围栏或引用块，重复段落多义，超长/段数越界，未支持的多行形态，quote/line/hash/version/document/resource 篡改，旧 gold/cached artifact，未知字段/重复JSON键/HTML或外链，跨owner/project/runtime，任一read/write交集撤销/过期，读后source变更/退休，save同call同body仅一artifact、不同body拒绝，失败/UNKNOWN/PARTIAL来源拒绝可信成功。安全解析失败要写入前拒绝、无artifact；负例应分别断言operation及结果账本，不仅异常文本。

existing artifact.save_text VERIFIED 仅证明权限与本地持久/readback。可信来源必须另外绑定当前 source、独立检查版本/结果、实际 artifact hash，并保存可复读证明；不能用generic F1 PARTIAL语义NOT_RUN做P-B成功来源。不新增Grant或任意工具，写入只有既有owner/runtime交集。
