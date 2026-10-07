# DeliveryGraph 服务端与界面集成 Plan

2026-10-07，父明确授权整合远端 dev/delivery-graph-core `e66a437be14d40ff7ad70bad2a96e30a1d3db572`。正常 fetch 后在独立树普通 cherry-pick 为 `2a872d8`；根 e4ea5dbf 全量树仍冻结，本集成不污染正在运行的 PG 回归。模块83专项不是整体V5验收。

## 有界交付与所有权

后台：现有CSV/agent/Report已校验候选→可信current授权/来源/版本→持久逻辑ID与source/authorization版本→封存图锚→持久幂等规划回执→真实项目App范围的等待扩验队列。新增表仅通过既有显式Store.initialize/controller迁移创建；正常API只CRUD，不建表/Grant，不写业务对象或发布。图/规划/队列不执行模型、补丁或检查，不伪造已验证状态。

界面：既有generic App打开态中的入口，保存图锚/当前读回、选择真实节点生成影响规划，显示确定/不确定/保留/锁/等待扩验状态。保存或规划回执丢失/畸形后保留原键与原body，重新取可信当前对象并完整绑定当前project/identity/app/source/graph；ABA与撤权清空。文本安全渲染。

root负责API mount/static路由、接口协调、最终整合冻结与验收。后台owner只delivery_graph_apps/db/专项；UI owner只web及UI专项；独审不写这些文件。delivery_graph纯模块修订先回报父交独立线，不重复实现。

## 真实验收门

正常链从真实完成来源/现有候选创建图锚，重启/冷页读回，再持久生成同键规划并枚举实际项目扩验队列；不借客户端context或伪造source_versions。所有negative均验证无新产品权限和原候选/Run/历史字节不变：跨project/owner、撤权、过期、同键异参/竞争、coherent图与回执重hash、当前资源hash/format/status/来源seal改变、strict bool/重复/锁/未知范围、队列归属、缺显式迁移。

资源表没有原生revision，图版本账本只记录可信资源快照的变化，不声称修改资源计数列。VIEW/CHECK稳定逻辑ID持久mapping与执行check_id分开。authorization_revision由服务端相关授权状态变化驱动，缓存同键请求仍重验当下授权/版本。无sourceproof或unsupported family受控拒绝。

先专项SQLite/实际HTTP与DOM/独立oracle/静态验证，PG最小CRUD角色永久用例与整树回归在旧e4 PG自然终态闭合后另冻结执行。每轮source SHA、实际导入、全部收集、JUnit/skip/失败/cleanup各自记录；不得把e4通过计作后续新源码全量通过。若旧PG失败，先保存自然trace并修本轮具体问题，不能合并掩盖旧失败。

Windows预算仍NO_GO，原900/240/150、全部断言/保护/清理不变。普通既有dev同步需显式延后自动CI；本切片不授予LIVE/models预算、不上传其他目的地、不签完整增量补丁/发布/P-B/F1/AT02/Win11。

## 组合前验收进展（全量尚未执行）

后台 `73d80f0e` 的专项 34 PASS / 1 PG 角色 SKIP；独审冻结 `3f07b751` 的 9 项实际 HTTP/SQLite 攻击限定通过。原 peer 缓存/历史漏洞及独审脚本主键假设失败均保留，不抹除。合法 peer 可入等待队列；缺锚、缺权限或不支持的 peer 明确 BLOCKED_PARTIAL，未伪装完整项目已验证。

UI 源码 `2b642618`、交付 `8de03b51`：4 项实际 HTTP/DOM 回归 PASS / 62.66s，图 CSV 和 Report 各 29 检查、原 Report 49 检查及原应用流程，图请求模型增量 0。真实服务契约交付 `ff04a78e`：17 个黑盒检查实际到达，加冷 Store/撤权及 Report 部分扩展 2 例，共 19 PASS / 13.20s。完整 PROJECT fixture 使用现有声明式 bounded_agent 与合法 CSV peer，未冒称 agent 来源任务终态；真实 promoted Report 的不支持 parent 保留为部分扩展额外验收。

整合冻结前仍须关闭纯核心 raw source_versions 的 bool/float 类型问题，上游负责修复；随后重新收集全部测试、证明实际 source-first 导入，执行新版完整 SQLite→PG 串行回归和两个最小 CRUD 角色用例。旧 e4 的 SQLite 通过及 PG 2 FAIL 保留为旧源码终态，不能计入此组合通过。
