# 完整 CSV 报告流程的受限内部 Release / 实例交付

从远端实际可见且干净的 `44acab540dda5d090eccc21f07d461e2e4462d0c` 接续。新普通开发分支 `dev/csv-full-report-instances-20261017`；唯一仓库写入者为根代理。初始约26 GiB可用，Git/default网络正常，未发现适用AGENTS.md。`8fc70cc43a6ac81cd522249e8a3d367cd66c9238`、`2b290038a9f85417e3ed43187b0989c907e969f6`及44均为祖先。未访问旧满盘实例、依赖旧bundle或清理未知文件/锁/进程。

本片对齐原方案 F2-T03/T05/T08，仅交付既有 `csv-full-report-workflow.v1` 家族。原保存流程已经能逐次准备、确认、执行和下载完整MD；新增的是普通应用目录中可找到的内部版本批准、实例创建/明确选择、同配方内部版本采用，以及 Release—实例—普通Run—typed结果的绑定。定义仍为不可变v1，不支持任意配方编辑、通用CRUD或正式发布。

## 实现与边界

- `csv_full_report_instances.py` 是严格家族生命周期适配器，使用既有批准、Release、实例、AppRun和结果表及双份request journal。未新增表、executor、身份或业务Grant。
- 逐次准备复用原 `csv_full_report.use_tx` / `ordinary_csv.prepare_tx`，仍先产生 `WAITING_APPROVAL`，用户再独立确认。没有 `internal_run_bindings` 或 `INTERNAL_APPRUN` 分派标记；仍由原普通Worker调用原read/sum/save三个工具。
- Release冻结实际配方、完整报告来源/检查、formatter/tool定义及原限额；批准保留精确指纹、TTL、权限版本和消费边界。采用保留原lifecycle的revision/fromRelease/dataVersion/retained-data/grant/dependency CAS及提交后核对。
- 成功状态、完整MD独立回读和实例结果在原终态事务中绑定；历史按原Release、Run和采用边界重核。原Run、原MD和旧typed行不覆盖。完成来源不因其旧执行deadline而失效，新Run保留自己的deadline。
- 逐次材料/列、原键、合同与两个家族事件交叉核验；独立标量索引识别家族，标记缺失不能退回普通执行。当前来源、保存效果、输入和运行时权限仍需有效。缓存仅限同事务/写epoch，保留当前authority复核和深拷贝。
- UI每步单独明确提交，UNKNOWN只GET原键；account/project/workspace/实例选择generation隔离迟到回调。实例核查期间不展示旧流程的Run入口。取消仍使用原metadata命令。
- 准备批准/创建/采用/prepare不增Grant。原 `artifact.save_text` 正常执行仍产生既有两份输出read Grant，严格限定当次MD、原owner/runtime；不能将“全程Grant数不变”当断言。模型请求0，语义NOT_RUN、人工PENDING，正式发布门关闭。

基线独审先发现并修复可预测普通key的事后补绑；新实例层也拒绝已有派生workflow-use，不能事后给已接受/完成Run附实例。独审还促成canonical JSON类型、原合同FP、材料/列/原body、历史revision/Release及结果版本边界的独立锚核验。

## 冻结与实际覆盖

生产冻结：`cc85862a98b983b1665e9676640a8817e5840b1f`。这里的证据提交仅增加文档/原件；[code-freeze.json](code-freeze.json)列610份src/tests输入SHA256。此前两个冻结点为 `d2bacd5ccab8ac848956aa637771848ca58404a5` 和 `d22e82a66fdb010d778ee6d8903e50a61f755c52`。

共有 **17个唯一定向用例的通过证据，分批执行，并非最终SHA上的单次17项全绿套件**。原失败、WIP、source桥接及精确命令/原件均保留。[coverage.json](coverage.json)说明批次边界；完整原件含post-backend-byte-bridge和import-order-only-bridge。d2→d22的生产变化仅三行等待态UI隔离；d22→cc858的生产变化仅lifecycle两组局部import排序，规范化AST相同。最终页面在cc858实际运行。

| 实际批次 | 结果 | 唯一合格覆盖 |
| --- | --- | --- |
| 根backend-pass-candidate，d2 | 2 PASS | 两次新CSV、精确批准/采用、独立完整MD/旧历史；预创建成功普通Run碰撞 |
| 独立Git快照seals，d2 | 2 PASS | Release数值类型重签、终态结果重标至从未采用Release均409且55表不变 |
| 根backend-negative候选，d2 Python | 3 PASS / 3 FAIL | 3 PASS覆盖配方/检查/schema/typed `count=2.0`/TTL；版本与派生key碰撞/防重/active采用/取消；CAS漂移确认及真实Worker拒claim。3 FAIL见下 |
| 根focused-regression | 4 PASS | 既有兼容schema采用、认证Worker、跨实例控制、原workflow-only实际页面 |
| 根qualified-d22 | 3 PASS / 1 FAIL | 三种来源CSV/MD/运行时撤权：实际403、无受保护正文读取/无写入、取消仍可用。页面后验FAIL见下 |
| 独立Git快照page，d22 | 2 PASS | lost与navigation：四阶段实际接受回执丢失原键GET；账号/项目/实例迟到隔离、双击不重发 |
| 根final-cc858-page | 1 PASS | 真实控件批准/commit/create/select、新CSV、显式普通确认、原Worker、MD Blob字节/hash、采用、旧Run入口及cold Store重开 |

权限候选3个FAIL来自SQL观察器把既有 `pa_spec_run_scope` 空探测误计为正文。独立SQLite只读精确COUNT均0；修订只豁免已证为空的精确SQL/身份/kind/key，正控仍有真实受保护正文，其他正文仍拦截。仅重跑该三项，均PASS；未修改邻家族产品gate。快速初始统计曾含pytest `current` symlink别名，原件保留，最终唯一计数排除别名。

qualified-d22的页面JSDOM driver已PASS，Python后验因新增断言误取顶层runtime_id而KeyError；更正为冻结合同中的runtime_id，仅重跑该失败节点，最终PASS。此前开发期的lease耗时/原创建键采用后回读失败和已修正原件也保留，不算合格通过。没有用静态/语法检查冒充运行测试。

## 原始证据与限制

[raw-evidence.tar.gz](raw-evidence.tar.gz)包含155个本任务原件、解压24,083,110字节；包括HTTP、实际页面请求/控件检查、加载assets哈希、MD下载字节、SQLite、pytest/JUnit、冻结/桥接、独审、失败与修正记录。[raw-inventory.json](raw-inventory.json)逐件记录SHA256/字节。归档逐成员解压哈希已重核，无snapshot旧docs、依赖目录或symlink别名。

[后端独审](independent-backend-review.md)只签其d2两例；[页面独审](independent-page-review.md)只签其d22两例。其输入清单/原件校验也在压缩包中；未把两个独立批次或不同冻结点拼作一批。Ruff、JS syntax和diff whitespace检查通过。

仅合成数据、Linux、SQLite、ASGI TestClient与JSDOM。未执行真实模型、真实语义/场景验收、Windows、PostgreSQL、原生浏览器或远端CI；未部署。现有Windows工作流仅监听另一指定开发分支，此分支不触发，未更改CI权限/触发器。旧满盘环境最后独审报告缺失仍是既知证据缺口，本片没有声称补回。

断连通知后只做了一次有界环境检查：工具、原测试与日志继续；HEAD/两份未提交差异已哈希及tar保全，后续按原进程完成，没有重复启动写入者或删除未知锁进程。

远端最终SHA、是否干净和推送差异以交付后 `final-delivery-verification.json` 为准；普通开发分支正常推送，不修改main或任何旧分支、不强推。
