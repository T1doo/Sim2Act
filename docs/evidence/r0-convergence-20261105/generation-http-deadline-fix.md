# 正式生成HTTP期限与滚动租约分离

背景：a0534197第二请求约33.5秒后结束，而任务仍在300秒绝对预算内。代码核对确认，PG非独立租约模式的_execution_deadline返回滚动lease；policy._fresh据此返回deadline，sender原先将它直接用于HTTP总期限。

修复仅在有原业务绑定的generate阶段生效：先保留原_fresh、实际lease/fence、来源、账户及原guard核对，再取Run创建时间+配置期限、原caps期限、试验到期、来源到期、原controller期限及heartbeat绝对期限的最小值。续约不能向后移动这些上限。没有调整30秒租约、300秒任务预算或120秒保存协议。

网络等待另接原生Event：观察原generation heartbeat状态，失败、实际lease过期或worker取消时停止等待；原HTTP实现按停止事件取消接收。等待结束后排空观察线程；捕获、结算、写入前原校验保留，不把收到响应当作验收成功。

12项受控检查通过，包括：有效滚动租约不缩短HTTP绝对期限、续约不延长绝对期限、心跳失败/租约过期/取消、来源或controller期限拒绝，以及原InternModel捕获接口在MockTransport下跨过初始租约并完成、取消后停止。没有替换业务时钟、放宽生产期限或发送真实模型请求。见generation-http-network-final.xml。

这是工作树修复，尚未形成新资格清单/Windows包，也未证明真实模型超时解决。

另一个原独立租约P-B用例已结束失败，不能将旧包装观察器视为唯一根因。其源为natural-tool-qualified-source测试快照，保留natural-tool-authoritative-cold.xml；该用例未取得预期SUCCEEDED，须单独分析，不能与本修复合并签通过。
