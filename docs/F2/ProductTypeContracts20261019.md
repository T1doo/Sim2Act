# 原项目完整源代码类型门修复

从 `5f5f964906792433d51140871d9d7b7aab365de0` 接续原开发分支 `dev/production-trial-stages-20261018`。此前“同 8 条旧诊断”是 14 文件定向检查，不能代表完整项目。README 和 `scripts/Test.ps1` 均要求 `mypy src`，现有配置没有这些诊断的豁免。原 HEAD 完整检查实际为 **31 条诊断、10 个来源文件、113 个源文件**；本轮修复涉及 11 个产品文件，包含共享异常契约。

V1/V2 共用私有字段基类，各公开模型保留自身精确 namespace Literal、默认值、字段顺序和校验器；接受两版本的函数签名明确写出并集。可空 slot、body 和最新声明在解引用前显式按原错误码、文案拒绝。接收证据仅增加无默认值的私有类型注解，保留 `hasattr` 所依赖的缺席语义和原异常对象。CSV/MD 使用各自真实签名的 gate 别名，CSV 原事务内前后两次检查保持。版本常量、有限 CSV/账本容器、状态 DTO 和已有修正反馈 Issue 使用实际类型。

未增加 Any、ignore、类型检查豁免或删除检查；检查配置、依赖锁和测试源码均未改。原 executor、Grant、durable intent、权限、版本、租约、额度与资格边界保持；固定生产账户来源仍拒绝，软件资格锚未更新。

## 实际验证

| 范围 | 结果 |
| --- | --- |
| 完整 `mypy --no-incremental src` | **PASS，113 源文件，零诊断，62.61 秒**；原基线 FAIL/31 条 |
| 11 个改动产品文件 Ruff / diff whitespace | PASS |
| 完整 `ruff check src scripts tests` | **FAIL**；原 HEAD 与候选完全相同的 117 条诊断，未视为豁免或通过 |
| 纯模型对照 | 8 个公开 schema、V1/V2/P-B 三种合同序列化及指纹与原 HEAD 完全相同；错误 namespace 三例仍拒绝，私有接收证据仍不进入 public 输出 |
| 独立 unittest | 状态诊断 12 PASS；CSV 整数 oracle/结构边界 30 PASS |
| 原生产链定向批次 | **62 项：60 PASS / 2 FAIL，658.53 秒**；682 个列举的源码、测试及配置输入前后不变 |
| 原 HEAD 失败对照 | 旧 V2 节点在相同阶段证明处 FAIL；MD 修正节点在相同 RUNNING/PARTIAL 断言处 FAIL |
| 候选 MD 单项隔离复跑 | **1 PASS，136.77 秒**；原批次 FAIL 保留，不声称本类型补丁修好了间歇执行问题 |

V2 旧节点的普通 Worker 只完成三次 Mock 生成，没有当前阶段证明要求的控制器 backend 标记，`stage_review → _generation_accounted` 拒绝 `Mixed or unknown actual trial backends cannot prove a stage`，尚未完成七槽。基线和候选同点拒绝；本轮不修改产品隔离来迁就旧夹具。

MD 修正初批子 Run 在一次 Mock 读取后仍为 RUNNING。原 HEAD 同断言失败，候选隔离复跑通过。基线及候选隔离被动日志均出现 Run 心跳的 SQLite errorcode 5；成功候选也出现此错误，不能把任意 Busy 单独当成失败的充分原因，原候选初批的具体心跳异常未直接观测。原 Worker/Store/租约没有修改，此项仍为开放质量问题。

两次对照的夹具和观察限制完整保留：首次基线导出缺少一份已提交的导入依赖，收集 ERROR、未执行节点；精确补齐同 HEAD blob 后执行。随后基线 V2 观察脚本在 pytest 写完 JUnit/stdout 后记账异常，实际 pytest 退出码未持久化，依据真实 JUnit/原文报告 FAIL，不补造退出码或时间。该 doc 导入依赖只做事后 HEAD 字节比对，未冒充包含在初始 682 输入冻结中。

独审为冻结源码契约和原始文件的 **LIMITED PASS**，未发现本补丁明确 P1/P2，未执行生产链。作者和独审原件见[证据入口](../evidence/product-type-contracts-20261019/README.md)。作者 seal SHA256：`253de8ccbde6458d33437d58b17d1385a00b7c19b1fca41c2881111f3866b1f4`。

真实模型请求 0；本轮未执行全量 pytest、Windows/native/浏览器、PG、远端 CI、真实账户/免费额度、人工语义/场景验收、部署或发布。完整 Ruff 和旧集成失败保持开放，类型门通过不代表工程或产品整体验收。旧满盘环境缺失的独审报告没有恢复或补签。
