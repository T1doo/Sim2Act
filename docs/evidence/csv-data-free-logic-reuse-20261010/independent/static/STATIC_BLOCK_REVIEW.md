# STATIC_BLOCK — v3 暂冻结实现

HEAD `fab14d542d7efe41d0b290e5b5baec433a1669a9`，未提交产品v3；不是最终源码冻结SHA。仅静态只读审查，**动态测试0**。初始/v2/v3各10个接线产品原文/hash已保存，另保存5个不可变基线依赖。v3已读10个产品与作者intermediate-source-v3清单逐项匹配，停止ACK前后字节一致。

v3仍有两项硬阻断：

- `target/options → target_for_schema` 在旧rid排除前先运行 graph.current/load_family/authorized_read。其他CSV app可引用同一个原rid，因此global options读旧CSV后才排除；direct target原app也先读后拒绝。应先只读目标App候选元数据，排除原app/rid及非canonicalCSV/多binding，再执行全部原目标授权/图/源证明门。
- 新 `csvLogicPlanSeal` 在验证POST接受期间调用targetApp GET，而 `api`读取global token。旧身份有效POST迟到且用户已切身份时，会以新身份查询旧目标，可能失败而丢掉“known accepted”缓存。应在POST前当前上下文获取并冻结目标App，迟到回执完整纯seal验证后先保接受，再守当前页面；之后的当前GET回读仍核实时权限。

初始null guard/派生实例原prefix验证/公开payload数值等价风险已修到v2。v2仍可共同改签两个authority origin的 model_requests0→False，保留approval原payload0，通过`frozen==p`；v3完整对象fingerprint比较修复该静态路径。未将作者动态通过当独立测试。v4及后续修复尚未审阅。

其余主要静态门存在：独立明确mint、固定规范结构/schema/cap；源JSON仅hash及opaque joins、Run/App最小projection、不查原Operation/Run.result；privateaudit不对外；独立loader无consumed过期例外；any撤销证据/consumed拒绝；reserved base与instance前缀双origin、exact祖先；新target全当前权限/图/字节/schema/锁/预算；每步及最终typed前后commit_guard再次strict loader。`authorize(data.aggregate_csv)`内部递归核`resource.read`，不存在最初疑似“只核aggregate”缺口。

所有静态发现已通知root。当前保持STOP ACK、无独立动态进程，源码写入者仅root。需实际修复、精确最终源码冻结后再独立动态验证。此报告不签PG/native/升级/整体/性能或模型；PROJECT PENDING/BLOCKED_PARTIAL、overall NOT_ACCEPTED、semantic UNKNOWN、owner PENDING、LIVE0及历史OPEN不变。
