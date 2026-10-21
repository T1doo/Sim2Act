# 按 V5 校正 G0 新鲜性边界：已独审的设计，尚未实施

基线 `c20b8b6baf2c023b5dc7c89f7e8282bad112f350`。本轮按用户最新约束回到原 V5，形成[具体设计](DESIGN.md)，[终稿独审](REVIEW/DRAFT-REVIEW.md)结论为 **ACK_DESIGN_ONLY / NOT_READY_IMPLEMENTATION**。不是运行代码修改、删除现有防线、租约调整或新执行窗口的批准。

V5 §5.5/8/9.2/10.2 要求当前授权与撤回、owner/fence/期限/取消、规范化业务定义与相关版本、含集合的实际读取范围、原子提交及可信注册工具。原文没有要求每个 helper 全图 pickle、Python alias 身份或任意模块猴补丁的相同错误顺序；此前严格实现等价否决不能自动升格为产品安全不变量。可信回调造成的意外 mutation 仍须防御。历史审查与失败原件不改写。

最小设计是先保留原事务，只迁移一个封闭 G0 prewrite 区间：原 gate 授权并实际读取完整事实，入口深复制/严格校验为服务端拥有的递归不可变领域值；所有纯消费者只能用该值，不能回读原 RowMapping/Pydantic/dict。内容指纹可一次计算；动态授权、停止、租约/fence 与原业务准入继续在动作、非纯边界和提交处当前读取。原两次 commit 语义门、关闭后的 stop/期限、W5 及 postwrite live/tail 不删。

这改变的是“每个 helper 重扫可变图”的实现合同，不是减少授权门。完整字段、隐藏行值及回调后的保守重查在初片保留；frozen model/MappingProxyType 或旧摘要不能替代真正拥有且不可变的输入。规范化定义指纹与已有业务签名仍保持原算法和覆盖；新局部协议的 domain/version、software/audit anchors 及 post_graph/源 origin 桥必须先审清。不能全局替换当前 pickle V2。

同事务第一片仍持 SQLite 写锁，不能宣称解决 heartbeat 写入阻塞或保证原 30 秒通过。后续短读→锁外纯算→短写仅是受阻设计：完整字段、关联、存在性、集合/新增删除与未知范围都须在提交事务重新核验，不能只比较 Run CAS 或本地 epoch；原期限更严格 cap 不放宽。PG 需独立隔离/谓词证明。当前特殊 Cold 图明确为 `test_only && SQLite`，不等于所有 Cold 或真实 PG 生产路径。

实施前尚待闭合：逐 producer/consumer 字段与回调清单、无可变引用逃逸的所有权证明、所有动态门与最终授权覆盖、局部指纹/现有 proof 和持久签名的兼容分类。新的测试按数据变更、撤权、TOCTOU、提交与未知状态等实质性质迁移；不能按是否使用 monkeypatch 来删除安全用例。原始 pickle bytes/私有调用次数本身不再作为所有架构的产品验收判据。尚未满足实施条件，所以本轮没有运行代码改动或新测试。

本轮实际检查是原 V5 manifest 两份全文 hash、15 份设计来源 hash、11 个符号/12 个显式 add 点的 AST 清单及独立源码/终稿审查。[STATIC-SEAMS.json](STATIC-SEAMS.json)只是矩阵起点，**不冒称传递消费者或 SQL 谓词穷尽证明**。官方事务资料核对见 [REFERENCES.md](REFERENCES.md)。无 DB 打开、模型/Mock/G0/W5、profile、pytest、旧实例恢复、权限/凭据/费用变更或新观察器；G0 性能仍未验收。

另对原计划独立缺口做了源码核验：旧 FirstMaterialRevision 文档说未提供的 CSV App 材料授权页，在当前代码已存在 backend、挂载和实际 UI render 调用，含明确 App/材料、READ+SUM、作用范围/期限及独立确认；实现祖先为 `a1649ed443280ad16da45a0a55a0f8086889d8fd`。见 [CSV-STATUS.json](CSV-STATUS.json)和既有 [产品说明](../../csv-app-material-access.md)。不能重复制造开发任务或替用户授 Grant；本轮没有重跑或提升该片验收范围。

本目录仅保存设计、核验与独审记录。最终交付 SHA、远端和工作区状态见最终回复。
