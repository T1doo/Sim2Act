# 双求和独立无内容逻辑：实施前设计独审

**ACK，可按该有限合同实施。无未解决 P1/P2。** 基线 `6476056037325005c0688a9175927b70598ee0e7`，设计 SHA256 `49fcd81bcf767250fee70559023b2ce027173a5a428b65a8e90e84f18f44aa51`。本审只读设计和现有源码；产品导入、测试、Worker、DB、模型、PB/G0 执行全部0，仅写本 `/tmp` 报告。

归一化与现有独立授权模型兼容：原 source 双 schema 按其私有 aggregate_steps 完整校验，公共 recipe/schema 固定 read/total_a/total_b，无旧节点名、旧列名、材料 hash/id 或结果混入。旧 Release/consumed approval 仍可作不可变 JSON hash audit，原 Run 仅标量身份；这不等于完全不读旧 JSON。新目标继续原严格普通单结果 tuple schema/当前授权门，不以双嵌套输出 schema 放宽目标。

专用双 consent 必须在新 mint 和 load 的 AUTH pair 中都按 audited execution_version 核对；两份 request seal 同改不能换回旧 consent。公共既有 namespace/marker 以 exact execution_version+canonical recipe/schema 分派，不需扩大原 LogicOrigin 或旧 scalar body。源仅原成功 closed 三节点两 sink，一跳限制保留。

新 strict dual columns 恰 canonical total_a/b 两 key。base origin、derived plan_origin、prepare_instance_plan 均从完整 canonical(columns) 逐节点核验，不能只检第一个 body.column。全局 frozen cap 不变，同三节点 compiler 保守除3、max_repairs=0，不增加 Grant/身份/工具。source_snapshot 新 logical dual 须恰一个 origin、实际两终端核验和 default_columns；实例来源/markers不可删除后降级普通计划。

同 key 授权读取/恢复可原样返回已存在 authority，旧材料不可用时不得因此刷新TTL、重新mint或扩大范围；fresh key mint 仍须完整当前源授权。撤销/过期后的 inspect/revoke 延续原 active=False 行为，不能因预算收紧或旧源删除妨碍独立撤销。queued、步间和最终 typed 事务保留原 authority/TTL/当前 target Grant/预算/fencing/全回滚。

后续必要证明是新目标注册在 mint 后，旧材料撤权/删除仍能新计划→实际双结果→Release→实例→冷交换列；SQL原参数/列投影证明 post-mint 不读旧 resources、Run.result/context、operations，明确仅旧不可变 Release/approval audit 例外。独立 CSV/Fraction 核两完整输出，旧历史/principals/grants按设置后基线保持；错consent/映射/alias/scope/target授权/成对篡改/derived降级、queued/首sum后/final-typed撤销和过期均拒绝。旧单列logic与双材料回归、真实HTTP/JSDOM明确双consent/未知晚回执/冷双列恢复需要实际测试。

这是工程设计可实施 ACK，具体补丁与实际局部测试尚待独审；不签新 runner、PB/G0/真实模型/PG/CI、旧软件迁移、完整P-A/P-B或发布资格，不另开执行窗口。
