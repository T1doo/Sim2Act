# WIP 实现独立静审

结论：发现的 P1 原key历史解包错误已由root在冻结/首跑前修正；当前未发现其它确定产品P1/P2。实际pytest/产品资格仍未运行，不能写PASS。

## 已修 P1_HISTORY_LEDGER_ARITY

首次工具输出的 sender._source_history 把 journal._ledger 三项返回解包为四项，任何已有journal原key会ValueError，导致history恢复不可用。最小修正已读到：现sender346行使用 `_, state, _ = ...`。正常重复及晚撤销重复两个现有节点会实际命中该分支，不增加节点。初见未修行按工具输出转录保留于discovery-tool-output-transcript.txt；未修完整文件字节未及时落盘，不冒原件。wip-source-history-fragment.txt是随后实际读到的修后片段。较早implementation-review-draft.json记录发现当时状态且其broken_arity_present_in_preserved_fragment=false明确反映这点；以修复记录为当前状态。

## 其余源码

新source176–232行先exact Store/test_only SQLite、活动同engine连接，再原contract/user/project/runtime/canonical account，之后owned scalar requestFP双锚、pair与有限base64raw。raw模型四角色严格，显式identity/entitlement/零费+禁付费fallback/revocation事实；未知enforcement保持None。所有SourceVerificationResult只是固定synthetic数据合同；issuer/seals不证明provider事实。生产resolver/admission、journal/policy未改，未增加API/Worker或真实source注册。

仅pair VERSION_CONFLICT被转SOURCE_INTEGRITY/UNKNOWN，其它真实权限/DB异常不吞。新source模式通过私有sentinel固定loader，无调用者source/callback/selector；完整原key先_source_history，只按完整owner/scope/wire/identity返回原history，不读当前source、不重发。reserve/marker各同c读source后原_apply_in_transaction，guard同c重读，receive在原owned Run门后重读，再capture+settle同TX。DENY/UNKNOWN通过原settle保存body/usage而拒接受。captured Store/engine/settings/transport/worker围栏保留。旧sender其它原函数AST均一致；_receive/dispatch是本片有意接线变更，需实际最小compat而不冒旧8节点已重跑。

## 测试范围与1处建议

4个测试函数含6参数化拒绝，共9唯一节点；正常观察4次source load及reserve/marker/settle同Connection。跨项目使用真实另owned项目，先校准snapshot SQL正例，再缺本项目锚时确认不读foreign payload，拷foreign raw到本scope仍拒绝。来源晚撤销由实际Mock handler修改服务端status；接收应保8usage、halt/拒接受，重复不send。边界节点覆盖exact offline门、权限异常传播、默认production拒绝及旧入口1次compat；不重跑旧19/12/8。fixture保护其它54表，完整拒绝/历史窗口另做55表严格相等。

当前inconsistent节点只检验两seal完整且四角色冲突，未命中新source的pair VERSION_CONFLICT→UNKNOWN分支。建议同节点恢复valid源后，仅破坏一半source fingerprint（保requestFP标量锚正确），核SOURCE_INTEGRITY/UNKNOWN、dispatch LIVE_BLOCKED、损坏后55表不变及handler0。无需新节点；未补前不得把此分支声称已实际验证。

本审只文件/Git/AST，不运行产品/pytest/collect/HTTP/SQL/DB/网络，不改repo或旧sealed。目录未seal，后续冻结与闭合原件资格另审。
