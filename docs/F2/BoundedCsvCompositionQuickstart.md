# 有限只读 CSV 节点组合（工程候选）

在原应用页面使用，复用原 CSV DAG 接口和后台 Worker。当前最多四个节点，
每次最多四个工具操作；模型请求和业务写入均为 0。语义 UNKNOWN、用户验收
PENDING、正式发布关闭。这不是非 CSV 能力、PROJECT 完成或 AT13 验收。

## 页面复现

1. 在已配置的 MOCK 环境打开已有 CSV 应用。仅使用它当前已经授权的一份 CSV。
   工程示例 `tests/fixtures/column-binding.csv` 的 amount 总和为 30，quantity 为 15。
2. 在原影响规划区保存当前派生图锚；锁冲突需按原精确版本流程处理，不能绕过。
3. 在原 CSV DAG 面板选择“有限只读节点组合”。默认四个可编辑节点：amount 求和
   → 报告，quantity 求和 → 报告。可以删到一节点、添加至四节点、切换已有动作，
   选择列及来源、报告前驱和额外前驱。只有三种已注册动作可用。
4. 如需条件，在节点上选择 eq/in/exists、输入或前驱字段和类型正确的比较值。
   本次是否包含报告使用原布尔输入；缺失不会自动补成 true。
5. 保存计划，读回精确指纹、实际拓扑、固定来源、列和输出，再勾选确认并排队。
   保持原 Worker 运行。刷新读回四个持久步骤证明和两个末端输出。
6. amount 求和条件为 false 时，其报告继承跳过，quantity 支路仍产出 15。
   此时终态 PARTIAL、amount 报告为 null，不能当作完整成功或验收。
7. 同键恢复只恢复原接受回执；创建新运行必须重新确认。原暂停、继续、取消和
   历史入口仍可用。撤权或来源变化后证明失效，停止控制仍可用。

选择“原三节点流程”继续使用原预览 → 求和 → 报告及既有接线/条件入口。
不覆盖旧应用、旧计划或旧结果。源码升级会使原来源图锚失效，必须重新派生并
另存计划、重新确认，不能把旧成功重新签成当前证明。

## API 定义

POST 原 `/api/projects/{pid}/apps/{aid}/csv-dag`，保留原候选/图指纹、request_key
及兼容用 column 字段，增加 `composition`。column 只用于原三节点模式；组合
的每个 aggregate 必须声明自己的 column 及同名固定输入 `{step_id}_column`。

```json
{
  "version": "csv.composition.v1",
  "nodes": [
    {
      "step_id": "a",
      "action": "data.aggregate_csv",
      "column": "amount",
      "depends_on": [],
      "inputs": {
        "resource_id": {"source": "data", "ref": "source", "field": "resource_id"},
        "column": {"source": "input", "field": "a_column"}
      }
    }
  ]
}
```

报告的 resource_id/column/count/sum/source_hash 五个端口须来自同一个求和节点。
读取或求和的 resource_id 可接当前 source，也可接已有读取/求和前驱的
resource_id。每个 step 引用（包含条件）须声明 depends_on；节点输入次序可由
编译器整理为确定拓扑。第五节点、环、自引用、未知来源、跨语义端口、混合
报告元组、未知/非数值列、任意代码和超预算会在保存之前拒绝。

保存后的原 `/{plan_key}/runs` 入口仍要求 CONFIRM_EXACT_OFFLINE_CSV_DAG 与
expected_plan_fingerprint。组合不能同时带旧 wiring_patch 或 branch_patch。
结果包含 output_by_step（各末端输出或 null）、扁平 output、实际前驱回执哈希、
input_sources 及工具计数。SKIPPED 不制造 Operation、不消耗工具预算。

定向测试及执行源码哈希见 [证据目录](../evidence/bounded-readonly-dag-20261008/)。
SQLite 是工程夹具；应用安装仍按原 PostgreSQL/普通 CRUD 角色流程，不新增配置。
