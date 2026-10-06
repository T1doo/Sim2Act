# E16：内部合成 Release / Instance / AppRun

依据原 V5 分阶段计划 §4.3 F2-T08、§4.5，以及产品设计 §10。事前范围提交 eaeb731，正确工作副本 /workspace/Sim2Act-pb、dev/f1-foundation，基线 764a20f。这是内部 Python service 的合成工程路径，未接入 HTTP、用户发布按钮或实际部署；不是正式发布链签收。

## 范围与调用

`sim2act.lifecycle.prepare_release` 重新验证已有可信候选，实际授权执行样本并以独立 integer sum oracle 检查。`commit_release` 需要该批准的完整精确 fingerprint，绑定用户、项目、到期时间、候选版本、当前 Grant 版本、manifest/actions/dependency lock、检查证据和类型化数据 schema；批准只可消费一次，已提交 Release 的同批准重试返回原对象。Release 保存不可变快照，不追随随后编辑的工作草案；每次使用仍验证独立来源锚点、当前授权和实际文件 hash。

`create_instance` 绑定精确 Release，创建独立 instance 数据命名空间；复用既有应用 runtime，无新 principal/Grant，无恢复或扩张授权。五张 `internal_*` 表经既有显式 migrate/Setup 建立，API/worker 不建表；后续业务操作仅 CRUD。

`run_instance` 固定 instance revision 与 Release fingerprint，重新经过现有 user/project/app 权限交集的 resource.read、data.aggregate 和独立 oracle。每次新请求产生绑定 instance/Release 的新 AppRun，成功追加该 instance 的类型化 result 数据及结果版本；失败持久 FAILED，不追加结果版本。幂等键以 instance/user 分域，同键不同输入拒绝，缓存重放也需当前权限。没有读取 preview 历史来充当运行。

数据仅为该固定可信工具的类型化结果账本，非通用业务数据库/任意写入工具。允许现有 result 字段及可选 string release_ref 元数据，封闭 schema；不支持额外 enum/约束、字段删除/改类型或破坏性迁移。schema 变化需严格增加版本，同 schema 不允许偷换版本。支持同 schema/version 不同 Release 升级和回退；可兼容添加可选 release_ref，但回退删除字段拒绝。

`prepare_switch` / `commit_switch` 精确批准固定 instance、原/目标 Release、指针 revision、数据版本及全量数据指纹、当前 Grant 版本。事务内 project→instance/approval→gateway Grant 锁序；前置变化拒绝，不切指针。切换仅增加 revision/history，不重置数据、不回滚数据。旧结果继续绑定原 Release/Run，新 Run 使用新 Release。

## 验收及保留边界

新测试位于 `tests/test_internal_lifecycle.py`；原 `tests/test_lifecycle.py`/AT05 实际进程测试逐字保留。覆盖批准指纹/期限/草案/Grant/source bytes 变化、快照改写重算 hash、双实例隔离、当前撤权/过期、跨 owner/项目/应用、结果 lineage、幂等并发、兼容与不兼容升级/回退、前置变化后切换拒绝、历史与数据保留；PG 应用角色验证新表 CRUD 无新增 Grant。实际结果见 [证据](../evidence/F2-internal-lifecycle-20261006/README.md)。

同工作区独立只读审查实际复现缺 properties 的 KeyError、顶层 enum 可在批准 PASS 后令同样运行 FAILED；已改为受限封闭 schema，并加持久负例。审查发现测试文件重名覆盖原 AT05，已恢复原文件并更名新增用例。这些是开发过程中发现并纠正的缺口，未称已发布事故或权限泄露。

正式发布入口/真实部署不启用；完整 P-A/P-B/AT10/通用应用、Win11/F1 正式签收仍未完成。无新增前端或真实浏览器检查；保护浏览器通道仍 BLOCKED，不用 DOM 冒充视觉。0真实模型请求、无业务外发/恢复包/其他目的地上传，V5 与历史 AT02 不改。
