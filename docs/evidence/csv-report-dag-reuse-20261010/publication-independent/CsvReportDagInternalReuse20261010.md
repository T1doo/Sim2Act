# 已完成三步报告流程的内部版本与冷输入复用

原计划 P-B/F2-T03 与 T04 的一个实际缺口：读取、求和和报告已经可以组成有限 DAG 并逐步验证，但仅两步流程可以保存为内部版本。最终源码冻结 `50b10417a99a070f6bcd614471cc00ec102b7836` 补充严格的无条件 `resource.read → data.aggregate_csv → intern.csv_report.v1` 复用。继续使用已有动作、编译器、Run/Worker、runtime 与当前授权；没有新模板、执行器、身份、Grant、网络或模型调用。

新来源版本为 `internal.csv-read-sum-report.v1`。它只能由实际三节点结构派生：读取无前驱且引用原 CSV；求和只依赖该读取；报告只依赖该求和，五个端口全部引用同一个聚合元组；唯一终端输出是报告。三个真实 VERIFIED Operation、前驱、工具计数、来源字节、图、计划、草案、授权、合同预算、Run/version/fence 均需重新核查。条件、额外接线、额外节点及实例版本切换仍不在此切片。

新版本保存 `report_step` 和三个回执指纹，来源双 seal、snapshot、binding、接受标记和冷读回使用同一精确版本。旧 `internal.csv-read-sum.v1` 保留两节点结构及原字段，不能用改标签方式获取三步权限。每次输入仍只允许选择冻结数值列；接受同键严格比较完整请求，派生计划只改变允许的列和请求键。

实例每次实际执行三步，报告仍占一个工具步骤并受原三节点预算分摊与当前限额约束。typed ledger 保留原五字段聚合结果；完整报告文本和三个回执保留在 Run 的唯一报告 sink。读回验证报告严格等于已核聚合元组的确定性格式化结果。最终 typed result、data_version、AppRun 与 Run 终态在同一事务提交；撤权、源变化、实例 ABA、绑定删除、第三回执损坏或终态事务失败不能追加结果。

页面分别手动准备、核对并保存版本、创建实例、确认新列排队。UNKNOWN 保留原请求；已知接受回执只 GET，未知接受只显式同键恢复。冷页面读取历史与结果零 POST。报告用现有纯格式化动作，不把结果解释为语义或 owner 验收。

初始候选 `5588a94faeb90abb2052a8ae5327810b8d27c287` 的限定独立复核及固定 native11/Edge 通过后，追加独立类型反例发现 BLOCK：将整数 `2` 改为浮点 `2.0`、重签 typed row 与 Run 指针，分别保留或同时改变 AppRun.output，都使三个公开 GET 返回 200，而冻结 schema 拒绝浮点 count。原 Operation/回执未改，GET 零写。两例 BLOCK 与此前有限通过的原件均保留。最终修复同时严格比较 row→AppRun→真实聚合结果的规范 JSON 指纹，防止 Python 宽松数值相等绕过类型合同；不是只检查行签名，也不是仅修 AppRun。最终两步/三步及 row-only/joint 四种攻击、正常回归的范围与遗漏分别封存。

实际 f13 旧源码创建的两步版本与结果，在本次源码升级后触发既有图基线保护并返回 VERSION_CONFLICT；旧原始 JSON/行保持不变。需要新成功来源与新内部版本，不改签旧历史，不承诺跨源码变化无缝复用。

验证结果与原始失败、跳过及远端状态在[本轮证据目录](../evidence/csv-report-dag-reuse-20261010/README.md)封存。仅 3/69 产品文件变更，其余 66 与前冻结 `47388f573746daa27f8d5790ca358eef91378ad5` 完全同字节。全量原生 Windows 900 秒容量仍 BLOCKED：原 9002 作业实际不够，未执行尾部成本 UNKNOWN；没有全量重跑、共享可变夹具或按分片增加总预算。

历史 Report GET idle6、PG resources-history Future10 保持 OPEN；其他 HTTP200 损坏响应及反馈限制保留。PROJECT `PENDING/BLOCKED_PARTIAL`、整体 `NOT_ACCEPTED`，semantic `UNKNOWN`、owner `PENDING`，正式发布关闭；Windows900/Edge240/Node150 未验收。`LIVE=0`，真实模型调用 0。不改 main、不强推、不部署、不改凭据或安全网络。
