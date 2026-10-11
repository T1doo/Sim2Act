# 原失败和修复记录

原日志/XML 保留，不把中途源码或独审夹具故障算作最终冻结通过。

| 记录 | 实际结果 | 原因及后续 |
| --- | --- | --- |
| first.log / first.xml | 23 FAIL | 作者测试夹具取创建响应中未提供的 candidate fingerprint；改为读取实际保存的应用，并使用原锁 API |
| second.log / second.xml | 16 PASS、7 FAIL | 作者负例错误期待所有拒绝均 HTTP 409；实际原验证返回 400，修正错误码断言并保留零写检查 |
| third.log / third.xml | 23 PASS | 初始有限范围修复后执行；尚非最后冻结源码 |
| mypy-module.log | 2 新类型错误及所导入模块的既有诊断 | 使用原 Change 与 CSVInput 类型修复；最终 mypy 只有原 5 项基线诊断 |
| late-probes.log / late-probes.xml | 4 PASS、1 FAIL、29 deselected | 末尾撤权拒绝实际 409，作者断言仅容许 403；改为核 403/409 拒绝和完整回滚，scope-probes 中已通过 |
| independent/backend-first.log | 独审脚本 ERROR | 独审脚本误用复合主键表的不存在 id 字段；修正脚本，后续真实探针通过 |
| independent/ui-first.log / ui-fail.json | 产品 FAIL，此前 7 检查 PASS | 重签根指纹后空 actual.output 使 every 真空通过并错误启用最终保存；新增精确输出 key 集合验证，独立第二轮 12 检查 PASS |

独审还要求并已闭合：原始锁登记 ABA、不可变 accepted_at/deadline、达到期限边界和 receipt 插入后的最后期限/撤权检查、Python bool/int 指纹区分、保存和核对原页面 intent、peer 授权 revision、完整 checks 覆盖、首次明确拒绝后的可改正状态。见独审报告和最终冻结测试。

全关联第一轮 final.log / final.xml 在后续权限前置守卫及页面输出校验修复之前已开始，只作为中途关联回归；final-frozen.log / final-frozen.xml 才是全部最终源码与测试的执行证据。freeze-first.json 是中途来源，freeze.json 才是最后冻结来源。

uv/npm 默认缓存的首次写入尝试遇只读文件系统，随后按允许路径使用 /workspace 内本任务缓存；没有权限升级或改变网络保护。未导入旧被拒候选，未重试已知被拒原生浏览器动作。
