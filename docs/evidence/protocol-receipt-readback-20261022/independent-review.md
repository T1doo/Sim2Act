# 只读独立审查

审查者 `/root/next_scope_review`，仅只读，未写入或运行测试/DB/网络。主线按代理原消息保全，不将主线实测表述为代理实测。

设计限定 ACK：已接受 Source/Cold review 可按当前认证项目/Run 只读定位；不新增持久 writer。无持久 UNKNOWN 不由此恢复，查无记录不得解释为未提交。必须精确项目匹配、拒多记录歧义、拒残留封印/成功态却缺 row，仅返回原请求/公开回执，新鲜复读后才确认。不能声称冷页辨认所有刷新前 UNKNOWN；首次独立新核查与只读恢复分开。

代码审查找到两项 P2：

1. `reviewLocateClosed` 被误加在独立 Source completion 的首次提交 guard，导致 Source 未完成时失败的核查定位可能阻断合法 V2 完成。已移除该跨范围 guard；最后只有 review writer 受它约束。
2. 合法 NOT_FOUND 原分支只改 message，可能保留旧 PASS/回执与提取路线。已走同一失败关闭路径，清成果、提取/Cold 入口和可见回执，保留原键并允许再次 GET。

修复后候选限定 ACK：两项 P2 闭合；定向断言覆盖独立完成不被阻断、已有 PASS→NOT_FOUND 清除。后端先 own 项目再精确项目/Run/user，复用全授权/来源/规范记录与封印校验；缺行/残封印/歧义均拒，不调用 writer 或输出 gold，未发现剩余确定 P1/P2。同 owner 错项目与结果快照损坏负例对应新增边界。

此 ACK 是静态审查，不代替最终测试、新原生 DOM、PG、OS 重启或未持久 UNKNOWN 的运行证明。最终主线冻结测试另见原始 pytest 日志。

最终证据限定 ACK：代理只读确认五源码哈希、MANIFEST 20/20 原件长度与 SHA、14 PASS/4.75 秒、25 项新 VM 检查及两旧控制器归档一致；ASGI/新 Store 非 TCP/OS，VM 非原生 DOM，只读零 POST/零新键与完成兼容的一次假 VM POST 分列准确。未重复测试或操作 DB。
