# 固定两步 CSV DAG 的内部版本与冷实例复用

本页记录原两步冻结切片。2026-10-10 新增的严格三步报告链复用见[三步报告内部版本](CsvReportDagInternalReuse20261010.md)，原两步版本字段与语义保留。

候选限定为同一已授权 CSV 上无条件的 `resource.read → data.aggregate_csv`；成功来源必须有两个真实 VERIFIED Operation、正确前驱和独立算术读回。条件、报告、额外节点或可编辑接线不在此复用切片。原 CSV 草案保留，不新增 AppManifest 家族、执行器、身份或 Grant。

内部版本仍属 `INTERNAL_ENGINEERING_ONLY`。准备、确认保存、实例创建和每次新列运行分别手动进行；版本来源与独立双行 seal 冻结成功来源 Run/version/fence、计划、草案、图、授权、真实 source hash、两个回执、允许数值列、输出 schema 和预算。未知来源版本、移除来源标记或改为单节点执行均拒绝。首片禁止 DAG 实例版本切换。

每个实例运行只接受 `{"column":"已冻结数值列"}`，同请求键严格比较完整输入、实例 revision 和版本指纹。可信编译器派生独立计划与 seal，原计划和版本不修改。执行继续使用原 runtime、当前授权网关、真实 CSV 字节、同一 DAG Worker/Run/Operation、租约与 fencing；预算取来源计划、来源合同、内部版本、接受合同与当前平台交集，收紧后保守拒绝。

成功时以同一事务写入两个已核回执的最终结果、内部 AppRun、typed instance result 和 data_version，然后改变 Run 终态；事务失败、旧 fence、撤权、来源变化或实例 ABA 不追加结果。typed result 保存原聚合五字段，Run 留有独立计划和两个回执；这一实例结果写入如实计 `business_writes=1`，真实模型请求仍为 0。冷历史严格比较接受事件、双行回执标记、实际 binding/AppRun 三组 Run 集合，再对每条数据重构真实 Run/Operation；不能用结果行与 AppRun 同改 hash 自证，也不能共同删掉两组标记后把仍有接受事件的历史显示为空。

在原 CSV 应用的 DAG 面板选择“有限节点组合”，仅连接读取与一个求和节点，保存精确计划并确认执行。成功后在“两步流程内部版本”区域准备来源、核对允许列与预算、显式保存版本、创建实例，选择另一数值列并单独确认排队。读回结果、关闭页面、重新连接后读取已有版本与实例，全程只读恢复；新列再确认后才建立新 Run。普通单节点 CSV 使用入口不会把该内部版本描述成单节点执行。

接受回执 UNKNOWN 时保留本页原 body/key；未收到接受回执的显式恢复只允许同键同请求，已知接受 ID 后只 GET。准备批准、保存版本、实例创建和运行使用既有持久账本幂等，无自动重试或继续后续写入。页面重开会丢失未确认 intent，应先只读核实已有来源、版本与实例；不承诺跨刷新自动恢复所有未知 UI intent。原材料保存 UNKNOWN 仍仅页内 Map、无幂等键，不保证跨刷新 exactly-once；此流程只复用已保存、已授权并有成功回执的材料，不自动重复材料保存。

本片最终源码/测试冻结 `d716feda486fd6f0322c11b2e1b5112f718a94fa`，357文件；69产品与039修复完全同字节。SQLite039整批72PASS/1测试钩子FAIL/1PG角色SKIP，d716仅修测试钩子后定向1PASS（74节点覆盖73PASS/1SKIP，非一次全绿）；PG最终74PASS。每库9真实HTTP/jsdom页面104检查及4实际旧源码升级。原807联合历史遗漏独审BLOCK保留，修复后必要增量4例12检查LIMITED_PASS，旧14API/5UI矩阵按807归属。[完整范围、失败及字节桥](../evidence/csv-dag-internal-reuse-20261010/README.md)。

合成工程证据不等于完整 P-A/P-B、非 CSV/PROJECT、R0、语义或 owner 验收。`LIVE=0`；PROJECT PENDING/BLOCKED_PARTIAL；语义 UNKNOWN、owner PENDING、整体 NOT_ACCEPTED、正式发布关闭。PG resources-history 历史超时 OPEN、807新增Report GET idle失败OPEN、其他 HTTP200 损坏响应提示限制、Windows900/Edge240/Node150未验收均保留；不改 main、不强推、不部署、不改凭据或安全网络、不真实模型调用。
