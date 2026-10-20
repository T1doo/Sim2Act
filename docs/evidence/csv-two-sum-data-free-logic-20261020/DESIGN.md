# 双求和独立无内容逻辑：实施前有限合同

基线/远端 `6476056037325005c0688a9175927b70598ee0e7`，开发分支 `dev/production-trial-stages-20261018`；main `6f688e4dd80b5c81d41aecde90e360d3629f9c21`。命令、文件/Git/网络与干净工作区已核，根是唯一仓库写入者，既有独审只读。未运行产品测试、PB/G0 或模型。本设计先独审后实施。

范围沿原 F2-T03/AT-10：只有原成功一次读取→两个求和的同项目内部版本，另行明确授权其不含内容的结构在24小时固定期限内复用；授权后旧材料可撤权/删除，新目标仍须已有、当前授权的注册单 CSV。不是授权读取旧材料，不增加 Grant、身份、算子、执行器或外部调用。

1. 授权必须在旧源仍可完整核查时通过既有 material.recipe→read_release→真实 SUCCEEDED Run/三步 VERIFIED/双 sink/当前源权限；material/logic 派生版本不得再提取。双节点专用 consent `AUTHORIZE_DATA_FREE_TWO_SUM_CSV_LOGIC_IN_THIS_PROJECT`，旧单列 consent 不允许授权双节点，反向也拒绝。仍用原逻辑 authority/seal/revoke 账本、TTL、scope、软件 fingerprint；公共 namespace 保留既有逻辑族，由 execution_version=internal.csv-read-two-sums.v1、规范 recipe 与双 schema 精确分派。
2. 规范结构固定为 read→total_a 和 read→total_b。旧 step 名、列名、目标/事实/布局/结果/材料 hash/id 不进入公共 recipe；不从旧 input/candidate 拼新计划。源双 schema 须按其原 aggregate_steps 精确等于两个完整 tuple，授权公共 schema 归一为 result.{total_a,total_b}，每个 tuple 仍完整五字段。私有 audit 仅原六个不可变来源标识，继续绑定原 Release/consumed approval/family/原 Run scalar identity；后续不得读旧 resources、Run.result/context 或 operations。授权并不使旧 release 通过原当前源鉴权。
3. 两 sum 仍在同一读节点后，分别保留完整结果。全局 limits 沿用原 effective envelope。相同三节点 compiler 将 max_requests/max_tools/max_total_tokens/run_seconds 各保守除以3，max_repairs=0；不放宽原节点预算，不扩大工具/材料权限。
4. 目标保持原 target_for_schema 的 owner/project/注册类型、单 CSV schema、真实 hash/graph/当前授权门。仅目标注册 schema 为单个完整 tuple，执行结果 schema 则为规范双 tuple。拒绝原 source app 及其 resource alias，拒绝跨项目、未授权、hash/图/版本不匹配。
5. 新独立 TwoSumMaterialInput 恰两个规范节点 columns，值为目标当前数值列，可同列；与旧 column 互斥。完整 authority fp/target fp/graph/resource/hash/columns/key 保存于成对 origin/seal。定义与读回必须重建，不能靠同时重签 response 改第二列。同键异参零写入拒绝。
6. 源 target Run→新 Release→Instance 的 default_columns、双 schema、来源 marker 完整保存。所有派生 logic-instance-plan 由完整 canonical(columns) 核对，逐次 load 活跃独立授权及当前目标权限，禁止删 marker/origin 或降级成普通计划。source_snapshot 仅对已重建且恰一个 logical/material marker 的双来源保存实际两列；不放宽原实例校验。
7. queued/步间/最终 typed commit 都保留原 commit_authority 的授权状态、TTL、预算、target Grant 与原子回滚；独立授权撤销不可因旧源不可读而失效，也不可重新授予目标材料权限。历史保留原始行，授权失效后旧结果读仍按原守卫拒绝；不迁移旧实例或重写旧来源。
8. 页面明确“同一读取、两个求和、双列分别选择”的专用授权确认；原来源有效时才能 mint。全局逻辑 registry 冷恢复不 GET 旧材料/来源。目标两选择器标规范节点，改任一列清确认；回执按双 recipe/schema/input/预算/完整目标计划纯校验，保留原未知/晚回执/身份世代守卫。保存计划、执行、版本与实例仍分别确认。

必要本地合成因果证明：先授权再注册新目标、撤销/删除旧 CSV、拒绝再次 mint 原来源且原 release 保持拒绝；SQL 观察证明后续无旧材料或 Run.result/context/Operation 内容读取。真实 NoModel Worker 新目标双结果及冷 Store 交换列由独立 CSV/Fraction 核对，新 AppRun/typed ledger 独立；原历史字节及 principals/grants 不变。再核双 consent、错误/标量/混合 mapping、旧源 alias、跨owner/project、target 撤权/hash、logic撤销/过期（queued、首 sum 后、typed最终提交）与成对篡改/派生 origin 拒绝，旧单列/双材料回归，以及页面 mint/未知和晚回执/冷双列恢复。NoModel 禁真实发送；不运行完整 PB、G0、真实模型、PG/native 或发布。

设计授权通过后才改产品；最终需代码与实际证据独审、正常开发分支推送。完整 PB/G0、旧软件迁移、PG/native 验收保持未通过/未测试的原范围。
