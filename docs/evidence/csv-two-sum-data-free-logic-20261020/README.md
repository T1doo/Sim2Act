# 双求和独立无内容逻辑：有限交付

原 F2-T03/AT-10 的有限工程缺项现已补齐：在原成功双求和来源仍可完整核查时，用户可另行明确授权其无内容的规范结构；之后旧 CSV 撤权或删除，新计划仍须在同项目另一份当前已授权的注册 CSV 上实际执行，保存两个完整结果、新版本和冷实例。不是完整 P-A/P-B 或真实语义验收。

起点/远端 `6476056037325005c0688a9175927b70598ee0e7`，分支 `dev/production-trial-stages-20261018`；main `6f688e4dd80b5c81d41aecde90e360d3629f9c21`。产品/测试源码提交 `e579c47ec3391dc3ffd7b4d49e705b7663483dc3`。已核环境、Git/网络、干净工作区、远端祖先与单写入者；根唯一写仓库，独审只读源码与原件，仅写独立 `/tmp` 审查记录。[实施前合同](DESIGN.md)先获得可实施 ACK 后才改产品，正式[设计独审](independent-review/DESIGN-ACK.md)亦保留。

## 实际合同

双节点必须明确确认 `AUTHORIZE_DATA_FREE_TWO_SUM_CSV_LOGIC_IN_THIS_PROJECT`，旧单列 consent 不允许授予双节点，反向也拒绝。首次 mint 保留原 material.recipe/read_release、真实 SUCCEEDED/三步 VERIFIED/两个 sink、当前旧源权限及冻结预算。load 的成对原请求也按已审计的 execution_version 重验 consent，不能同时重签两份 request 后换回旧确认。

公共逻辑只含规范 `read → total_a / total_b`、规范双 tuple schema、原 effective limits 和既有独立授权字段；不保留旧节点私名、列名、目标/事实/结果或旧材料 id/hash。source schema 按原私有 aggregate_steps 精确验证，公共 schema 则归一化。沿用原逻辑族 namespace，以 execution_version+精确 recipe/schema 分派，旧单列字段和值保留；字段声明顺序可能变化，canonical fingerprint 使用排序 JSON。

授权固定24小时，可独立永久撤销，不刷新期限。同键仅恢复已存在的同一份授权；新键 mint 必须再次核查当前原源。旧材料不可读后只使用独立批准的结构和新目标当前权限；仍会读取原 Release/consumed approval 的不可变 JSON 做 hash 审计，以及原 Run/来源 app 的标量身份，这不是完全不读旧 JSON。后续不读取旧 resources、旧 Run.result/context 或旧 operations；不恢复旧 source Release 的原权限。

目标仍走原严格 owner/project/注册 CSV 单 tuple schema/当前 graph/hash/源字节/权限门，旧 source app 和 resource alias 拒绝，未放宽共享 target_for_schema。双 columns 恰好 total_a、total_b，各为目标当前数值列，可同列。完整目标与映射绑定成对 origin/seal，派生 logic-instance-plan 同时核两列及完整 canonical，不只核 body.column。新 Release 保存实际 default_columns 和完整双结果 schema，源/派生 markers 不可删除降级。

同三节点编译器使用原 effective cap 保守除3、max_repairs=0；实际测试核各新 action cap 不超原节点。queued、首个 sum 后、最终 typed 提交均保留独立授权/TTL/目标 Grant、原子回滚、租约及预算守卫。产品逻辑动作不新增 Grant/身份/执行器；测试显式注册目标与撤销旧源属于夹具准备，准备后 baseline 的 grants/principals、旧 Release/Instance/AppRun/typed 原行均核不变。

页面区分双节点确认和两列选择，改任一列清确认；计划、执行、版本与实例分别确认。回执进入 accepted 缓存前，从已冻结的新目标 candidate 与规范结构纯重建完整 definition：每 action id/revision、预算、输入/输出 schema、权限/依赖，及 manifest 输入/双终端输出/schema/views/lock 均逐项相等，再走原通用 seal。没有执行新解释器或扩展通用 compiler。原键未知/晚回执/身份世代守卫保留，冷页恢复两个默认列并另行确认新列执行。

## 实际测试与版本范围

全部合成数据、本地 SQLite、NoModel Worker；页面为真实 loopback HTTP + jsdom 30.1.2/Node 24.19.0、独立冷页面，不是 native browser/PG/CI。[10个冻结文件](quality/source-freeze.json)及 `frozen-source/` 对应最终产品/测试字节，实际 JUnit 见 `originals/`，批次索引见 [test-runs.json](test-runs.json)。

| 批次 | 实际结果 | 范围 |
| --- | --- | --- |
| 最终双逻辑后端 | 28 PASS，0 SKIP，56.053秒 | 最终 Python 字节，包括恢复400的精确回归 |
| 最终页面 | 9 PASS，0 SKIP，91.639秒 | 最终10文件冻结；6双节点+3旧单列，含两个篡改修复 |
| 旧后端回归 | 67 PASS，2 SKIP，155.590秒 | 旧逻辑、双材料、单列材料；在两P2修复前执行 |
| 旧页面回归 | 14 PASS，0 SKIP，166.315秒 | 10单列逻辑+4原双实例；在最终完整definition seal前执行 |
| 最终静态检查 | 全7项 exit 0 | Ruff、3 Python文件 mypy、4 JS语法、diff check |

最终9页面与旧14页面中有3个相同用例；不将重复轮次相加，主验证共115个不同通过病例、2个条件跳过。两 skip 是未提供实际50b/fab旧源码 archive，不能声称旧软件迁移通过；旧批次不冒充最终新字节运行。一次 Starlette/httpx 弃用 warning 保留。

正例先明确授权，再注册新目标，撤销/删除旧合成 CSV。原 Release 与 fresh-key mint 继续拒绝，同 key 恢复原 authority 与原 expires_at；实际新 target 两结果为 net=8.75/count3、units=13/count3，冷 Store 交换后分别13与8.75，由独立 CSV/Fraction 核 resource/hash/column/count/sum。新 Run、typed 版本与旧历史独立，模型请求0。另覆盖私有节点名归一、双 consent、错误/标量/混合/多余输入、owner/hash/target Grant、同列双 sink、同键异参、origin 双重重签、派生第二节点接线、queued/首sum后撤销或过期/目标撤权，以及 typed 写后期限拒绝导致整事务无 partial append。

`originals/sim2act-dual-logic-backend-final-20261020/` 保存实际 proof 及完整 SELECT 原文/原参数 JSONL。测试观察器在实际热/冷路径按显式旧ID参数拒绝旧 resources、旧 Run.result/context/operations 投影；旧不可变来源审计明确例外。完整 JSONL 也包含测试 snapshot 用于零写入和历史对照的无WHERE宽表读取，不能声称全体 SQL 零旧正文。参数谓词的零触达与产品路径源码核查共同支持有限结论，测试 oracle 不冒充产品读取。`inspection/source-identities.json` 仅根在测试结束后对闭合合成库以 mode=ro&immutable=1 提取标识，total_changes=0、库前后 SHA相同，便于核 SQL 参数；不把事后投影当运行记录。冷 Store 继承原 schema 隔离选项，本轮不运行PG。

## 独审、失败历史及边界

首轮独审两P2：旧单列非法列错误由400误改409，已恢复精确 INVALID_INPUT/message；前端只核总预算，可能缓存节点预算或第二sum schema被篡改的回执。后者先实际红测2 FAIL/5.497秒，均在错误 GET-only 恢复计数处失败，弱seal实际源码为 `originals/weak-seal-red.js`；补完整definition纯核对后，相同两病例在最终页面9 PASS中通过，不缓存坏回执并原键恢复。首版匿名化夹具大写 node id 违反现有 pattern，27病例中26 PASS/1 fixture FAIL；改合法小写后定点PASS，最终28全部PASS。原件均保留，失败XML和大文件gzip原样压缩，未修剪原始错误/空白。

冻结[代码 ACK](independent-review/CODE-ACK.md)与最终[运行 ACK](independent-review/RUNTIME-ACK.md)均无未闭合P1/P2；运行独审核468个装载资产哈希、独立Fraction双结果及SQL范围。完整报告在 `independent-review/`；独审未执行产品、测试、Worker、数据库、PB/G0 或模型。证据含完整大小/SHA及gzip原字节SHA索引，推送前后核源码与冻结一致。

本轮 PB/G0/真实模型调用0，无发布、部署、新凭据/安全权限、main修改、旧服务或取消窗口恢复；不改TTL/lease或任何安全门。最近已封存[完整Mock PB](../pb-full-current-once-20261020/README.md)仍FAIL_NOT_ACCEPTED（G0 32.041秒、首binding4.368秒，实际复合期限/stop拒绝的最小条件未知），W5/G1/finalguard未达。本有限双求和交付不关闭旧迁移、PG/native、CI、完整AT-10或完整PB/G0资格。
