# 同工作区独立只读复核（修复前）

执行者：独立代理readonly_boundary_review；基线6b008b2094da83632cd97167b4fbb76ee6635d06。范围为既有固定模板与PREVIEW来源权限、参数化、来源/版本、过期与UI选择。主开发后续修改不在此次独立复核范围；不声明独立验证修复或阶段签收。

代理未编辑源码/push、调用模型或外部服务；/tmp合成SQLite fixture已清理。既有test_app_previews/test_goal_candidates/test_preview_extraction专项77PASS/2PG角色SKIP。

四个可复现问题：

1. apps.load_draft只在generation存在时核对来源。删除字段/重算指纹后GET200/preview SUCCEEDED；撤回目标卡额外conditions.txt使用者权限仍可运行，绕过完整原目标材料链。
2. apps.compile_preview只检查节点数/工具名。将manifest.outputs.sum.field改成column/重算指纹后GET200、SUCCEEDED且sum=amount。P-B当时的require_fixed_source拒此来源，但P-A不拒绝。
3. app-form异步POST挂起→同项目打开其他草案→放行旧POST，activeApp被抢回新创建草案。独立jsdom/mock fetch复现，没有截图或真实浏览器运行。
4. CSV n/1e1000000（换行分隔）被guidance标numeric:true，preview未捕获decimal.Overflow，HTTP500且无FAILED历史。

额外P-B自然过期检查5组：user_source、project_source、source_app、target_user、target_app，派生候选inspect/preview均403。现有P-B负例对非成功状态、来源/回执篡改、跨主体/项目、撤权、依赖版本、幂等与递归提取仍有效。

未测：真实浏览器/手机视觉、Windows/PG独立复跑、完整P-B/AT10/Release、Win11/F1签收。复现后的修复及11项持久专项、DOM20项由主开发验证，不能写为独立复验PASS。
