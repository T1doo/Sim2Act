# 未注册的生产账户证据边界

基线 `494cf2e1490967f8cf8621bb48b52fa00713436d`，普通分支 `dev/production-evidence-boundary-20261018`；root唯一仓库写入者。开工checkout与远端同SHA、clean，指定环境约23GB可用，原`8fc70cc`仍远端可见且为祖先。未访问或修改旧满盘实例。本轮按后续明确开发授权，交付一个独立工程切片：生产账户证据要求、非权威候选数据诊断，以及原准入入口的缺来源默认拒绝接点。原F2及V5来源与设计静审见证据目录；真实执行没有获本轮授权。

实际已有的`AccountEvidence/_resolve`只服务test_only SQLite的合成固定发送器；PB source resolver验证运行归档，不能充当免费账户权益来源。现有通用InternModel网络发送器也不等于已具备自然应用生产准入。本轮不把这些已有代码重新计为新实现，不新造executor、Grant、费用来源或成功的生产发送链。

新增`production_evidence.py`：从原完整合同投影principal/project/runtime、trial/原approval key、完整contractFP、软件/权限FP、固定provider/model/endpoint、quota、原到期与严格整数paid_cap0。投影本身不证明已批准；生产调用必须先过原`gate._approved`。V1/V2/PB均保留完整材料、Goal及caps的原合同指纹，不迁移、续期或恢复旧批准。

候选schema只存有界opaque来源/账户ID、两种证据hash、要求FP、quota、有限时间、显式权益/不可收费/撤销bool或None以及来源读取结果。未知撤销没有False默认，未知或False权益不满足诊断。时间须issued≤checked≤参考时点<expires≤原到期且距checked≤30秒；这是保守工程检查，不声称provider规则。账户quota复用原唯一canonical算法，不生成第二账户桶。候选与要求均strict/frozen/extra-forbid；model_copy绕过校验仍在使用时重校，原始对象方法遮蔽与嵌套callback在序列化前拒绝。

即使所有数据吻合，结果仍固定`SOURCE_UNVERIFIED / NOT_VERIFIED / live_allowed=false / dispatch_authorized=false`，仅证明数据结构一致。bool、来源名称和hash不等于真实权益或权威来源；不返回AccountEvidence、FeeProof或Permit。没有注册/安装/自动发现接口，没有HTTP诊断或凭据字段，生产resolver也没有source/records/registry/authority/callback覆盖参数，当前恒缺源拒绝。

原`production_preflight`只增加一处调用：同transaction原`_approved`→缺来源resolver→保留原`_qualified`→原`gate.admit`。原身份、两份材料READ、SAVE、当前Goal/material/auth/software及批准/撤销检查仍前置。缺源目前提前返回`LIVE_BLOCKED`，后置literal软件资格和admit为**NOT_REACHED**，不能写成通过。旧literal pin/anchor、offline `_resolve`、test_only/runtime/model门、总账、API DTO及发送器均未修改。新增生产模块改变implementation指纹，旧批准不会自动适配新软件；不得重钉旧资格目标或重开已永久撤销窗口。

源码冻结 `8cd9d0040150dbd28a68bb622f5e6822577dad42`。Ruff与diff检查通过；9个唯一定向pytest节点一次运行全部PASS（JUnit25.526秒、外28.619秒），没有测试失败或重复运行。5个新节点核非可执行诊断、scope/账户/权益/撤销/未知结果/时间拒绝、严格类型/额外字段/遮蔽回调、V1/V2/PB完整投影与真实ASGI两路由；4个既有节点含P-A/P-B各一次原准入拒绝、SYNTHETIC_ONLY permit仍livefalse和旧offline callback/非test_only拒绝。合成同意记录及仅合成permit不是有效LIVE令牌。

新实际ASGI用例21个POST：4次缺源400（两route各重复一次）、14次额外source/evidence/registry/sender/fee/free/usage字段422、跨账号/跨项目/READ撤销3次403。仅前4次进入resolver；原软件资格未触达。请求前后两个窗口均执行全55表严格before==after；证据仅保存每表行数/指纹及已执行断言，没有导出全行或冒称独立重建DB。fixture本身正常建立两份材料/Goal、合成批准及一个普通生成Run并claim；没有Worker.once、模型发送、reserve或生产许可。撤销仅在两个请求窗口之间明确修改该合成fixture。

699个输入/134个生产文件前后零漂移。运行级哨兵禁止sync/async HTTPTransport、Settings.from_env及InternModel各请求方法，未触发；ASGI TestClient不属于真实provider HTTP。新生产路径因缺源无法发送，缺用量或发送结果未知不会被自动补零/重发；原usage/unknown ledger逻辑字节不变，本轮未新增成功发送、settlement、恢复或真实adapter验收，也未重复旧故障矩阵。

原始测试日志、JUnit、命令、输入hash、三版本投影、实际HTTP/表窗口证明及独审见[证据索引](../evidence/production-evidence-boundary-20261018/README.md)。封存辅助器首次用错一个已有文件名，失败脚本与工具结果metadata保留；第二次旧manifest在stdout完成前计算其空文件hash。原件未覆盖，`closure-correction.json`披露，`manifest-final.json`最终闭合完成字节。该两次是归档辅助器问题，没有产品源码/测试变更或重复运行；首个工具结果metadata不冒充原始stderr文件。

有限最终独审通过，无剩余已知P1/P2；独审复核源码与全部非DB原件SHA、699/134输入桥、JUnit/日志、结构化ASGI记录及已执行表断言，不另跑产品、DB/SQL或网络。原serializer遮蔽问题的草稿发现、修后静审与最终核验分别保存；独审不提前背书后续push。其目录含清单10文件40984B，已封存停止写入。

剩余真实来源、合法免费权益和强制不可收费证据、生产FeeAuthority、自然生产发送接线仍未具备，需后续独立实现与审查。当前代码不注册provider/sender、不签发有效LIVE许可、不发现或读取真实凭据、不发送真实请求。Windows/native、PG、远端CI、真实费用/语义均未执行；本轮没有额外费用或权限扩张。旧满盘独审未落盘的历史证据缺口仍未补回。
