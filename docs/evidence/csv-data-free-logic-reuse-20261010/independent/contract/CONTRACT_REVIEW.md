# 独立安全合同审查：LIMITED_DESIGN_PASS

审查合同 `e65768715b097c75ffe732c9a5ac11da5b5bbabf2770f9e806cd5e6198e0fc1c`；基线 `fab14d542d7efe41d0b290e5b5baec433a1669a9`，产品709。只读审查合同与现实现，没有执行测试/PG、修改源码、Git或远端。本结论允许按下述硬门实现，不是源码或产品验收。

此切片实质解除既有 material reuse 每次 recipe/readRelease→原 resource/Grant/graph 的运行依赖：来源仍完整合法时，owner显式授予24h独立逻辑权限；结构由服务端固定allowlist生成，目标另行完整授权和真实执行。撤销原资源权限不自动撤销已显式独立授权；UI必须清楚说明，逻辑本身可以另行撤销。源失效后补授权/续过期授权仍拒绝。没有必要新executor、AppManifest家族或数据库表。

原合同§6只读“元数据”但要求发现封存JSON任意变动存在歧义，§7 consumed与旧approval过期例外冲突，§11原instance-plan可丢来源marker。修订已明确只hash旧sealed JSON、独立loader无例外、logic-instance-plan强前缀。原合同摘要和精确hash保留；复制时遇到修订后的hash守卫失败也保留，没有混作同一冻结。

实现必须满足：

1. Mint仅原实际成功无条件闭合Run，拒绝internal_instance/material/logic任何祖先；全当前权限/源字节/每步成功证明先核后写。Canonical双/三步、固定step IDs/端口/schema由服务端重构，不复制旧列、goal、自定义节点、输入输出、CSVhash/bytes或caller代码。Cap取原有效冻结上限。
2. Immutable logic payload准确包括owner/project/id/24h expiry、固定结构/schema/cap、当前实现承诺及opaque审计引用。双origin/seal要核对**重构的规范值**，不能仅比较可共同重签的两份hash。新kind不能被旧release/app approval入口误处理。
3. 后续审计允许旧Release.snapshot/approval.payload仅hash和opaque identity/version joins，比较mint冻结FP并核既有family origin pair；不调用旧readRelease/recipe/load_draft，不SELECT旧resource/Operation/Run.result。Run/App只取明确的身份/版本/fence/acceptedFP字段。不宣称该审计复验不读取的Operation/Run内容；旧公开GET继续全门。
4. Dedicated loader每次精确核owner/project当前归属、immutable字段和实现承诺、finite expiry、consumed及任一revoke凭据。不能用 `approval(allow_consumed=True)`；旧helper在consumed时绕expiry，语义不适用此新kind。Same-key mint/revoke不能重置到期或补发权限。
5. Revoke与DAG采用相同project锁序，在一事务提交flag+独立receipt。consumed=true或任一revoke证据都否定执行；恢复flag、删一边或重签一边不复活。Idempotent revoke可以读原receipt，但不能因要求active而丢已撤销回执。
6. logic-plan与logic-instance-plan reserved prefix及独立dual origins构成防降级门；任意相关marker存在也要求全pair。后续新Release/Instance的family origin与执行来源必须锚定同一logic ID/FP，删除逻辑marker和origins不能让普通instance-plan重放绕过撤销。No recursive mint须检查真实祖先而非仅外层key文本。
7. 新目标按当前owner/project、candidate/graph、真实rid/bytes/hash/schema、user/runtime Grants、手工锁、冻结cap和当前平台上限完整核验，同key换target/column/CAS锚点拒绝零写。FrozenRunContract只含新目标，实际工具只读新目标，严格五字段typed ledger/完整report sink走原worker/原子提交。
8. 当前 `commit_guard` 只核fence/budget，不核逻辑expiry。除了load/enqueue和advance开头，最终typed写入前后必须显式核logic current/expiry；即使撤销被project锁序阻挡，expiry仍可在一次事务内跨过。拒绝时整事务回滚，不留typed/AppRun/SUCCEEDED半状态。
9. 当前c/project的global UI无需打开原app或读旧Release/CSV；三种独立exactconfirm，所有await后current/identity/project/generation门，迟到有效接受先保回执再守页，UNKNOWN原body/key、known只GET，坏200不paint/cache。列表展示只能固定“两步/三步”等通用结构信息，不能意外回传private审计snapshot。

后续最有价值反例是：原user/runtime资源撤权或真正删除后旧GET拒绝，新逻辑+新目标正常真实结果且原resource/Operation零SELECT；新增注册导致旧授权图变化仍不用重跑原任务；逻辑expiry/revoke/flag恢复/缺seal/joint marker降级及派生instance撤销；enqueue后撤销与提交临界到期无typed写；跨owner/project/target变化和同key变化零写；坏200及迟到ABA/UNKNOWN原bodykey，global冷入口无旧app请求。SQLite不能代PG并发权限，完整AT10/AT11/native/历史超时不在此签收。
