# 旧 G0 路径与 native accounted 候选：路线校正

核对基线：`824dfed3e9294727fd05aa88140d66b58b60ba3b`；历史第三窗口冻结
`cdda2b2ed6bce1393b90a500c0377294e4d82e34`。本次只有源码／既存原件静态
核对，未运行产品导入、Worker、数据库、pytest、完整 prepare／commit、G0、Mock
或真实模型；没有增加 stub、假 account evidence、运行资格或窗口。

**校正结论：两者复用同一个 production-shaped SQLite Cold 核心，但执行前提不同。
第三窗口已有合成替换；当前候选没有接进该窗口的实际构造点。该候选不能称为
旧 G0 修复，也没有完整 prepare／两次 commit／G0 收益证据。**

## 历史第三窗口为什么确实能到 G0

既存 [第三窗口 README](../g0-monitored-third-20261021/README.md) 与原
`RUN/diagnostic.json` 记录：6 次合成交换／8 次入口，五阶段均到达，G0
30.985113144 秒，以原 30 秒租约超时拒绝，无 W5。这里不重跑、不改这些原件。

调用图（源码行号为当前基线；历史源码 SHA 另核，见 `ROUTE-EVIDENCE.json`）：

```text
g0_bounded 授权子入口
  → g0_prefix.run_prefix
    → configured(..., prepare_case=prepare_pb)                g0_prefix:92
      → ProductionTrialBinding                             test_spec:78
      → 原测试 environment 替换                            test_spec:100
      → evidence.resolve_account = 合成 source             test_spec:101
      → admission._qualified = 测试 no-op                   test_spec:102
      → AsyncClient 使用确切 MockTransport                 test_spec:111–117
    → Generate 3 / Source 2 / Cold 1 的既有有限前缀
    → factory(...) 后 worker.once()                        g0_prefix:256–259
      → advance_model（响应已归档后 renew，原事务／读集）
        → _cold_model_before                               runtime:3646
          → _cold_graph_read(pre)
          → _cold_first_binding
          → _ColdTrialGraph(..., completed=completed)       runtime:3048
        → cold.commit(first)                               runtime:3652
          → _ColdCommitDiagnostics
          → _prepare                                       runtime:2922
            → _journal_source                              runtime:2738
              → spec_production.source                     dispatch:1193
                → 原 _approved
                → configured 的合成 resolve_account
                → policy.check_source
                → configured 的测试 _qualified
            → Source accounted producer                    runtime:2750
            → 原 recipe 校验／版本查询校验
            → Generate accounted producer                  runtime:2765
          → run_context / pb_accounting / resolve / archive
          → 原期限检查拒绝（第三窗口实际终点）
```

这不是把硬拒绝当成当年不存在。历史三项合成边界在
[原窗口设计](../g0-fresh-mock-prefix-design-20261020/README.md) 第 9 行已明确说明，
`configured` 文件自己的首段也说明只为隔离接线测试替换来源、软件资格和环境。
`g0_prefix` 的“这里不替换 account helper”注释只适用于该文件直接操作；它调用的
`configured` 确实间接安装这些替换，不能概括成整个运行没有替换。

历史压缩 source-manifest 中 prefix、configured、PB prepare helper、production
evidence、spec controller、dispatch 和 admission 的 SHA 已与 `git show cdda2b2:...`
逐项对齐；除 dispatch／runtime 外，这些文件当前也一致。dispatch／runtime
已有候选消费者修改，完整文件不同，但 `_journal_source`、`_cold_model_eligible`、
`_cold_model_before` 的历史／当前函数 AST 一致；当前多了默认关闭的候选接点。
原始诊断五阶段均成功返回，和上述静态路径
相互支持；它不是当前未替换生产路径可达性的证据。

## 未替换的当前路径在哪里必然早退

```text
_prepare:2738
  → dispatch._journal_source:1188
    → _production_binding(ProductionTrialBinding) == True
    → spec_production.source:52
      → 原合同／approval 校验
      → production_evidence.resolve_account:188
        → requirements_for(...)
        → _deny(SOURCE_MISSING):196      # 无条件拒绝
```

`SOURCE_MISSING = "No reviewed production account evidence source is supported"`，
抛 `LIVE_BLOCKED`，先于 Source／Generate producer 和 candidate 选路。更早的
`Worker.__init__ → dispatch.validate → _account → _journal_source` 也会遇到同一门；
真实普通安装还需通过 `spec_production.environment`（非 test_only、非 SQLite 等）。
故不得为当前未替换路径申请注定在账户门前退出的性能窗口。

还必须区分资格交集：未替换 `environment` 要求 `not store.test_only and not
store.sqlite`，而原 `_cold_model_eligible` 要求 `store.test_only and store.sqlite`，
native candidate 也只接受后者；这些条件不可能同时成立。`ProductionTrialBinding`
类型名不能消除这项区别。即使未来补上真实 account resolver，非 SQLite 的正常
生产安装也不会因此自动进入这个 Cold 图；`_cold_model_before` 在不合资格时
`yield None`，调用者走原 `spec.commit_guard` 分支。原性能问题及本候选目前针对
有明确合成前提的旧 SQLite G0，不能称为现实生产 G0 已接通／已优化。

缺的是**已审注册的服务端 account evidence 实现与相应软件资格**，不是需要再填一个
fixture 参数：`resolve_account` 当前没有 producer／registry／callback override，
只有 requirements 和无条件 deny；`CandidateDiagnostic` 不是 authority。
`spec_production.source` 后续仍要求 requirements 绑定、有效 account/quota/model/
endpoint、合法免费且强制不可计费、撤权／新鲜度／期限、软件 qualification 等原检查。
本片不实现或伪造这些真实来源，不把已准备合同／grant／CLI 选择当成替代证据。

## 当前 candidate 与旧核心的真实连接状况

| 层次 | 当前事实 | 可证明／不可证明 |
| --- | --- | --- |
| 领域核心 | 同一 `_ColdTrialGraph.commit → _prepare`，相同两个 producer 位置 | 源码可复用；不是另一套 G0 算法 |
| 运行资格 | `_NativeCandidate` 限 exact `_ColdGraphRead`、pre、test_only SQLite | 当前不是现实生产环境可启用组件 |
| 显式接点 | `_ColdTrialGraph(..., _accounted_candidate=None)` | 参数存在、默认关闭 |
| 实际两个构造点 | `_cold_model_before:3048`、post:3316 均未传 candidate | 默认产品／旧诊断路径尚不选择优化；post 不在本候选范围 |
| 本轮既有 337 项回归 | 真 SQLite producer／Source helper／coordinator，禁止 Worker／模型／transport | 证明组件与有限核心消费；不证明完整 `_prepare` 通过账户门 |
| account 拒绝用例 | native tests 的 `_graph_pb_accounting` 保留原 `SOURCE_MISSING` | 证明未绕过；不是 full prepare 的成功见证 |

已审优化可复用的**最小静态接点**是原 `_cold_model_before` 的同一个 `pre`
graph scope：在已有 `_cold_first_binding` 完成后、构造 `_ColdTrialGraph` 前，显式
创建 native candidate 并把它传入既有 `_accounted_candidate` 参数。继续执行原
`advance_model` 的 first／second commit；不另造 producer、不改 `_prepare` 的
entitlement 顺序、不把 candidate 接到 post／真实生产安装入口，也不解锁账户门。
候选 lifetime 必须留在原 guard scope（正常最后原检查之后释放，异常整族关闭）。

这只是接点定位，**本次没有新增运行接线或执行它**。如果日后在原合成测试路径验证，
必须明确其历史 `configured` 三项测试边界，而不能以当前真实 account 硬门已修好
为前提；若禁止这些合成边界，则旧前缀无法构造。此次指令禁止新增 stub，故本次
未安装任何替换。历史 grant 已消费，没有第四窗口授权。

此外，真实完整输入能否在合法 allowance 下选择 OWNED、两次完整 continuation
是否闭合及是否降低 G0 时间都仍未证明；现有夹具大 allowance 不能作为该结论。
不能只把 candidate 参数接上就承诺收益，不能加假 evidence 或扩大 lease 来试门。

## 本片实际验证与交付边界

`ROUTE-EVIDENCE.json` 保存历史 manifest／Git／当前源 SHA 对照、精确行号和
既存诊断的有限摘录；`reviews/` 是两个独立只读复核。没有新增 pytest／性能
运行，也不把上一片 337 项改记为本片执行。所有 `src`／`tests`／诊断脚本相对
`824dfed3...` 不变，旧窗口和上片证据原件不改。仅本路线校正文档正常开发分支交付。
