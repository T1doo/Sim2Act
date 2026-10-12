# 候选7独立复验：37 PASS、4 FAIL，不能全绿

2026-10-12，独审`/root/text_logic_review`。基线`e2b856bb453fc74452583fa10843148758e2d9b9`，分支`dev/pb-text-logic-reuse-20261012`未提交候选7。32作者新例+原独立API9例=41，实际37 PASS、4 FAIL、exit1，156.41秒；运行前后全部378个src/tests文件匹配冻结清单，零变化。完整命令/log/XML/退出结果和指纹文件在本目录。

API/Worker/index以及原独立9项均通过。新ReleaseIndex模型闭集、owner/app/project/candidate/logic身份、双seal指纹比较、列表先load_draft防降级、metadata定位后只读索引Release、commit tx内写index/approval consumed、任一seal缺失拒绝及写index故障全回滚已静态审查并有对应实际测试。没有发现需要新增产品写入的阻断。

四个Python UI节点都FAIL，必须保持该结果；不能借作者流程proof把独立轮写成PASS。它们具体不同：

| 场景 | 独立实际证据 | 失败 |
| --- | --- | --- |
| valid | 完整DOM proof PASS/error null；原+新两个SUCCEEDED AppRun；SQL屏障零阻断 | 资产38而严格要求2 boot × 20=40，漏CSS |
| authorization-lost | 完整DOM proof PASS/error null；GET-only授权恢复；原+新两个SUCCEEDED AppRun；SQL屏障零阻断 | 同上CSS漏取 |
| binding-lost | 没有result.json，隔离数据库仅原来源AppRun，没有新运行 | Python IPC BrokenPipe |
| revoked-retained | 没有result.json，隔离数据库仅原来源AppRun，没有新运行 | Python IPC BrokenPipe |

两处BrokenPipe的Python错误和JUnit完整保留；当时harness只在正常流程读取Node stderr，异常退出未收集Node stderr/exit，无法补造真正Node原错。其根因保持UNKNOWN。闭窗未排空旧异步请求只是后续排查假设，不能当已证实原因。只读检查本轮/tmp数据库元数据见`post-test-ui-metadata.json`，不涉及原内容读取或新测试。

已向root建议：显式真实HTTP加载CSS并注入style，保留20*boots断言；窗口关闭前停止poll并排空IPC/active fetch；任何异常finally保留Node原stderr/exit和SQLtrace。候选8是单独冻结/重跑，不能与本候选累计全绿。

本候选所有测试/Node/runner已结束并向root解除编辑等待。只写自己的/tmp；无产品/作者tests修改、push、socket/native、PG/Windows、真实模型或已取消目标probe。候选3/4/5红记录保留；候选4误选socket实际P/F及OUT_OF_SCOPE_EXECUTED_NO_ACCEPTANCE不改写。精确安装竞态对照永久NOT_VERIFIED；完整P-A/P-B/AT-10、人工语义/owner、正式发布/部署等未跑项不签。
