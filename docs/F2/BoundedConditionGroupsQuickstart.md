# 同一步的二至四个条件

原计划 F2-T04 / V5 §5.3 的独立工程候选；仅现有授权 CSV 与三种已有动作，
0模型、0业务写入、未发布。已按限定独审集成 dev/f1-foundation；原候选为
dev/bounded-condition-groups-20261009。[集成回归与限制](../evidence/bounded-condition-groups-integration-20261009/README.md)。

1. 原 CSV 应用派生当前图锚，打开既有 CSV DAG 面板。
2. 原三节点选择 report 或 aggregate，或在“有限只读节点组合”选择一个节点。
3. 保留第一个 eq/in/exists 条件，例如“本次是否包含报告 = true”。将条件关系
   选为“全部满足”，第二条件引用已验证 aggregate.count = 2。也可选择“任一满足”。
   组合模式的第二条件引用自己声明的前驱，例如 node_1.count；引用会加入前驱集合。
4. 可以添加至总共四个条件、删除条件，或切回“单个条件”。条件变化清空旧计划
   与确认，需重新保存、核对新精确指纹并明确确认运行。本次 include_report 必须
   手动选择，缺失不自动补真值；缺失 eq/in 输入使运行失败，exists 缺失为false。
5. Worker 执行实际工具与条件决策，结果中保留每叶观察。全部满足要求每项为true；
   任一满足要求至少一项为true，但两种关系都验证并求值所有叶子，不能用其他条件
   的真假掩盖缺失字段。前驱被跳过时整步仍继承跳过，不制造结果或Operation。
6. 合成 quantity 例真实求和为15、count=2。“全部满足”输入false跳过报告，输入true
   产出报告；“任一满足”第二条件count=3时同样由本次输入决定。四节点组合中跳过
   一条报告仍保留另一支路的真实新结果，缺失必需输出为PARTIAL。
7. 冷页面回读和失联后原键恢复只读持久回执；不能自动重新运行。源码升级后旧锚
   失效，旧历史保留，必须重新派生和精确确认，不把旧成功改签为当前验证。

API 的 when 增量示例（其余原字段不变）：

```json
{"op":"all","conditions":[
  {"op":"eq","source":{"source":"input","field":"include_report"},"value":true},
  {"op":"in","source":{"source":"step","ref":"aggregate","field":"count"},"value":[2,3]}
]}
```

all/any 不嵌套，二至四项，叶子仍是原 eq/in/exists。未知字段/表达式、bool与数值
混用、未来/自己/未声明前驱或 data 引用均拒绝；不增加工具与运行预算。
单条件仍v1，组合计划v2，权限和发布门不变。候选的精确测试和独审以交付证据为准。
Windows/Edge/Node150未验收，既有PG全量/历史超时OPEN；PROJECT
PENDING/BLOCKED_PARTIAL、semantic UNKNOWN、owner PENDING、整体NOT_ACCEPTED、LIVE=0。
