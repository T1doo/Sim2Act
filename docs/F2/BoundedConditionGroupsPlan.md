# 有限条件组合：原 F2-T04 的实质缺口

基线 `8c572154ff72ac61a506fb9313cb631996e76df7`，独立候选
`dev/bounded-condition-groups-20261009`。依据 V5 产品 §5.3 的“有限逻辑组合”与
阶段 F2-T04；现有 ControlledBranchesPlan 只实现 eq/in/exists 单一谓词并明确
拒绝组合。用户无法让同一步同时依赖“本次包含报告”及已核前驱 count/sum，
也无法声明任一满足。此切片补这一执行缺口，不新增工具、目标模板或外围检查。

when 保留原单条件，新增 flat `all` / `any`，conditions 恰为二至四个原谓词。
不接受嵌套、空/单项/超过四项、表达式/代码、未知操作符或额外字段。
每个叶子仍只引用 schema 声明的 input 或已声明直接前驱；完整常量类型检查、
来源/Grant/版本/锁/租约/fencing/预算门保持。预检检查所有叶子，不短路；运行
也求值所有叶子，any 已成立或 all 已失败均不能遮蔽缺失 eq/in 输入。exists
缺失=false，所有现有前驱跳过规则仍优先，不读取不存在输出、不制造 Operation。

单谓词计划及回执保持 typed-conditions.v1 的原形；包含组合的计划标记 v2，
每步持久决策按此版本冻结原组合与每个叶子的观察及布尔判定。冷恢复重建并
逐字指纹核对决策及已有实际回执；篡改观察或跳过证明拒绝。源码升级仍使原
来源图锚/执行证明失效，历史 JSON 原字节保留，不能改签旧成功。

原三节点及有限四节点组合页面增加“单个条件／全部满足／任一满足”和有界
添加/删除条件，保留第一条件原控件。条件/输入变更清空精确确认，未决原键
恢复时锁定控件；保存和运行仍走原 API、实际 Worker 和既有账本。没有新增
API、表、身份、Grant、工具、业务写入、模型请求、循环或正式发布。

验证限于新29后端病例、3实际 loopback HTTP/产品JS/jsdom 页面及必要原契约、
DAG/组合/页面回归、两实际旧源码升级；独立审查精确冻结后另记。SQLite 和自有
network-none/无端口 PG 串行，原900/240/150和等待上限不变；不全量、不CI、不部署。
先前 PG resources-history / 全量或探索超时 OPEN、HTTP200反馈限制、Windows
未验收保持。PROJECT PENDING/BLOCKED_PARTIAL、semantic UNKNOWN、owner PENDING、
整体 NOT_ACCEPTED、LIVE=0；本候选不合 dev/main，也不签收完整 F2-T04/P-A/P-B。
