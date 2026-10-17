# 完整 CSV 报告流程：有界交付证据

已实现：原普通成功完整 CSV 报告 → 显式保存不可变 v1 流程 → 统一目录 `CSV_FULL_REPORT` → 每次明确选择已有授权新 CSV/列 → 独立新 Run 与完整冻结 MD 合同 → 另行确认 → 原 Worker 读取、精确求和、保存完整 MD → 同 Run 结果及原字节下载。它是已保存流程，不冒充内部 Release/实例；单步 SUM_ONLY 的范围没有扩大。

使用说明见 [完整报告流程](../../csv-full-report-workflows.md)。来源/定义和新 Run 关联同事务保存；读取/确认/Worker 路径核查当前来源、材料、项目保存权限及独立保存效果。没有新 executor、Principal 或写入 Grant；实际保存仍按原政策新增一个 Resource 和两条成果读取 Grant。结构化完整报告合同可 PASS，通用语义 NOT_RUN、人工 PENDING、正式发布关闭。

## 精确源码与实际测试来源

生产实现 SHA：`4a4a228f09203e08103904e3afdd04b12708a98b`。测试专改 SHA：`436c49cb8c2ac04489fd9dfd4baaf09bffea0298`，唯一变更为 `tests/csv_full_report.cjs` 的回读计数断言与原始诊断。124 个生产文件逐字不变；作者 601 个冻结输入中其余 600 个不变。独审另含原仓库 `docs/evidence/bounded-agent-offline-20261006/independent-gold.json`，共 602 个输入，其余 601 个不变。每批执行前后输入/Git 字节一致。

| 执行方 | 原实现 SHA 的22项实际批次 | 测试专改 SHA 的实际补验 | 最终准入来源 |
| --- | --- | --- | --- |
| 作者 | 20 PASS、1 FAIL、1 SKIP；JUnit 233.554秒 | 2 PASS；JUnit 42.729秒 | 原20项 + 新2项 = 22唯一，24次执行 |
| 独审 | 21 PASS、1 FAIL、0 SKIP；JUnit 234.893秒 | 1 PASS；JUnit 28.062秒 | 原21项 + 新1项 = 22唯一，23次执行 |

**不是在最终 HEAD 重跑全部22项。** 22唯一包含13个新 API 检查、5个新 JSDOM 页面检查及4个旧回归。原批、补验、节点、命令、时间、原件路径与来源选择见 [准入清单](raw/author-evidence/admission.json)、[作者原 JUnit](raw/author-evidence/author22.xml)、[作者补验 JUnit](raw/author-evidence/author-refine2.xml)、[独审原报告](raw/independent-4a4a228f/review.json) 和 [独审最终报告](raw/independent-436c49cb/review.json)。

原 FAIL 来自页面复合断言写死“恰好2次 GET”，实际既有后台回读参与后发生3次；原失败没有记录各保护子值，因此当时不能直接归因为画布清理失败。补验等待已发真实请求全部回复，分别记录3次读取、末尾403/403、App/Run为null及定义/成果画布清空，保留原实质权限断言并证明其通过。生产没有为此改动。原 FAIL/日志/页面原件完整保留。作者原 SKIP 为未给旧 HTTP CSV 使用检查设置全局 NODE_PATH；补验使用已有本地 JSDOM 后该节点实际 PASS。补验 runner 的继承标签误含 natural MockTransport，原结果不改，另附 [范围更正](raw/author-evidence/author-refine-scope-correction.json)。

## 检查实际证明的内容

- 目录独立分类并可选择；新材料列 `quantity` 的精确合计为15，完整 MD/保存 hash 来自本次新 Run，原成功报告不变。等待批准时无新工具执行，确认精确新合同后才执行原三工具。
- 新请求同事务绑定流程/版本、输入指纹、原 key 与新合同；同 key 并发只接受一个 Run，改正文拒绝，坏输入不留下接受记录。未注入“prepare成功后link插入失败”的崩溃窗口，事务原子性另有实现和静态依据。
- 当前来源、新材料、项目保存权限、账号和三锚完整性；canonical JSON 区分1和true。本次 MD 撤权且 receipt refs被清空时，独立 effect 的授权门仍先拒绝。SQL探针有正向完整Run读取控制，负向Run GET、confirm POST、原key GET均未读取该目标完整Run；不代表全局 SQL 隐私证明。
- 可见控件实际执行保存、选择、准备、另行确认、同 Run 打开、结果与下载；真实 Blob 的730字节 MD逐字及SHA与该Run冻结全文、保存回执一致，文件名含同Run/资源，原件保留。未进行操作系统下载。
- 实际202响应丢失、交付为另一个合法Run ID、原key GET恢复、防重复POST、同账号待接受页面重开通知、跨项目/账号迟到回调隔离、来源403及打开Run交接后的403正文清理。

两方选取的新5页各为85条检查、216个实际API回复和125个实际资产hash记录。作者包含4个预期403；独审另有12个背景 `/protocol/contracts` 的400（`Evaluation asset unavailable`），[逐条原件](raw/author-evidence/independent-background-400.json)保留，**没有把216个回复称为全部成功**。本轮未扩展这些背景故障或旧恢复矩阵。

旧回归分别为普通完整CSV合同、已有CSV实例实际HTTP使用、普通成功任务SUM_ONLY提取后的目录使用、自然P-A的合成显式人工声明。新18项使用拒绝模型请求的 NoModel，旧自然回归使用合成 MockTransport；没有真实模型，不能称整批零模拟provider调用。

另有作者独立的自有合成 SQLite 增量迁移探针：53个既有表的schema/全部行不变，仅增2个空表，第二次显式初始化不变。它不计入22唯一、不属于独审动态准入，也不代表真实旧用户库、PG或进程重启验收。记录见 [迁移结果](raw/author-evidence/migration/result.json)。Ruff核6个Python文件、mypy仅新模块、Node语法4文件及diff检查共7命令通过，见 [静态检查](raw/author-evidence/final-static-checks.json)。

## 原件封存与边界

[原件映射](artifact-map.json)列344份原始材料及原始/封存SHA、编码和路径，包含97份SQLite文件（开发、重复批次及副本，不是97个用例）。独审只按其已封存清单取原件：原批75份加manifest/sums，新补验23份加manifest/sums。没有复制可重建Git快照、cache、pyc或pytest current软链；原文件没有改动。

SQLite及大于1MiB材料以gzip(mtime=0)封装；解压字节必须匹配映射中的原始SHA。根 [SHA256SUMS](SHA256SUMS)只排除自身，包含嵌套独审的原SHA256SUMS。开发期失败、旧冻结失败、作者SKIP均保留，不重写为成功。

仅合成数据、SQLite、实际 ASGI、局部本机 HTTP 和JSDOM，PG、原生浏览器、Windows、真实语义/真人签收、真实模型、独立进程重启、远端CI、部署和真实旧用户数据库未执行。本分支不匹配现有Windows CI触发分支，未改工作流。未实际构造“旧SUM_ONLY已ACCEPTED再提完整报告”链；本轮实际证明新报告PENDING且未自动创建人工声明。前轮aa485249的覆盖限制及背景400不重分类；原满盘缺失独审文件仍是证据缺口，未补回。没有回旧实例写入/删除、浏览器下载重试或访问拒绝绕过。
