# 双求和独立逻辑：冻结代码静态 ACK

**ACK 当前冻结代码；两个 P2 均闭合，无新增 P1/P2。** 10 个文件逐一与 quality/source-freeze.json 的 SHA256 匹配，清单见 CODE-ACK.json。本审产品导入、测试、Worker、DB、模型、PB/G0 执行均0，只读源码及作者原 XML，未改仓库。最终选中9页面批次仍待完成，运行 ACK 另行核原件。

旧 scalar 非数值列恢复原 `DomainError(INVALID_INPUT, Choose a current target numeric column)`，即原400与原message，新增严格400回归可见。TwoSum 映射仍恰规范两 key，并不改旧 scalar 同键语义。

新 csvLogicDefinitionSeal 在 i.accepted 写入前，依已冻结的新目标 candidate 与 canonical recipe/列、独立逻辑 cap 纯构造期望 definition，并整体 equality，再调用原 generic seal。逐项对照后端 compile_closed(..., READ_OUTPUT)：复制 manifest/action 后递增revision；同版本/app/step生成确定性action ID；原正预算按节点数2/3保守floor，max_repairs=0；read/sum/report 全 input/output schema、selected enum、permissions/dependencies/executor/继承字段；bindings/workflow/ports/边；完整sink输出映射与 schema、views、resource/tool/check lock，均对应。仅固定无条件规范结构，不声称任意DAG compiler等价。它不读取旧来源、调用产品/DB或改变业务预算。

因此单个sum node cap或第二sum output schema即使攻击者重算plan fp，也会在缓存接受前因完整definition不符被拒绝。已读弱seal源（无该mirror）及实际red JUnit：2FAIL/5.497秒，两例均在预期unknown恢复POST/GET计数断言失败，而非fixture setup。修复后最终页面绿色原件仍待核。新后端JUnit已实核28PASS/0skip/56.053秒。

前轮其他有限结论保留：mint及load AUTH pair按audit版本核专用consent；old sid动态双schema仅私有校验，public固定read/total_a/b并不携旧列/正文/hash/id；post-mint只做不可变Release/approval JSON hash audit和Run标量身份，不能宣称完全不读旧JSON。新target依原普通单tuple schema/当前权限；derived prepare和restore完整canonical逐节点比对；authority撤销/TTL/queued/步间/typed最终事务守卫保留。原source grant仅fresh mint用，原key恢复不刷新TTL。无新Grant、身份、工具、模型或来源权限。

最终页面原件未收齐前，本ACK仅产品静态结论；旧backend67PASS/2 archive SKIP和UI14PASS都发生于P2修复前，不能直接算最终冻结qualification。没有PG/native/CI/真实模型、完整P-A/P-B或旧软件迁移结论；本报告不授权执行新窗口。
