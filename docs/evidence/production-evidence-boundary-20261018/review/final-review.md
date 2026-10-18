# 生产证据来源边界：最终有限独立审查

**有限通过，无剩余已知 P1/P2 阻塞，可在授权普通开发分支交付。** 冻结 `8cd9d0040150dbd28a68bb622f5e6822577dad42`，基线 `494cf2e1490967f8cf8621bb48b52fa00713436d`。生产仅新 production_evidence.py 和 production_trial_admission.py 的4行接线/注释增加，另新测试。不是生产账户权益解析器或发送器完成，不开放LIVE。

本审查亲自进行只读源码/Git/AST及闭合JSON/XML/原stdout/stderr/manifest解析和散列；**未亲跑产品/pytest/HTTP/Worker/模型，未读DB/SQL、联网或写仓库**。作者执行目录 FINAL SEALED，本审查未写入；所有旧 sealed 独审目录未改。

## 源码与原发现

新严格frozen flat requirements/candidate绑定原主体、项目、runtime、trial/approval及完整contract、软件/授权FP、provider/model/endpoint、quota、expiry和paidcap0。未知撤销或权益不当True，严格有限时间、不续期；account quota复用旧唯一算法。即使候选数据全匹配，诊断仍 SOURCE_UNVERIFIED/NOT_VERIFIED/livefalse/dispatchfalse，无AccountEvidence/FeeProof/Permit或凭据。生产resolver无source/records/registry/callback/installer参数，无可信来源时恒LIVE_BLOCKED。

原P2为model_copy可遮蔽输入实例model_dump，修前记录保留、未声称动态复现或HTTP远程绕过。修后仅exact primitive、内建容器及固定受信nested schema进入raw声明字段校验，再原parse_contract重建；原实例serializer不调用。修后源码与本轮freeze的3文件读取SHA全部一致；实际测试覆盖顶层/nested shadow和callback字段拒绝。

preflight先原_approved，核当前主体/两READ+SAVE/完整Goal材料及原授权软件，再缺源resolver。旧_qualified/admit原样保留，但当前明确 **NOT_REACHED**，不能称软件资格通过。静态AST独立核旧offline `_resolve`、`_qualified`、canonical_quota_subject、dispatch_offline未变；11份受保护文件（原自然准入/总账/API、PA dispatch/PB uses、runtime/model/generation、PB source及资格anchors/pin）与基线完整bytes/SHA一致，另见protected-source-byte-bridge.json。原test_only/SYNTHETIC、预算/unknown/refund/resend逻辑及全部权限/Grant/executor/sender不变。

## 实际资格原件与独立复算

一轮 **9唯一节点/9执行/9 PASS/0 FAIL/0 ERROR/SKIP**。JUnit总25.526秒，outer28.618871秒；原pytest stdout与XML逐节点吻合，stderr为空。5新节点与4既有参数展开节点分别保留，不把单节点内的合成数据变体另加分母。

`verification.json`及audit-final-evidence.py/原stdout、stderr记录纯文件复算PASS：699输入before/after/current全bytes/SHA相同，134生产文件与精确freeze Git blob相同。最终作者manifest SHA为 `69a5feae66810641bb31c38ce435b6b3163705471d065dc13e99e46291deb4df`，34非DB清单路径项/650709B全部bytes/SHA匹配；其中pytest current别名不计新用例/fixture（30个不同物理非DB文件）。11个SQLite路径项仅stat大小及引用作者hash，未读DB内容（6个不同物理DB）；未复制DB到本目录。

原件是 **21份认证ASGI/TestClient结构化request/response记录**，不是loopback网络或原始HTTP wire证明：4次400缺源、3次403（外主体/外项目/READ撤销）、14次strict额外字段422。4次source调用投影已根据原请求独立重算完整contract/材料/Goal指纹与requirements全部字段；缺源拒绝safe_retry=false，不产生预留/发送。READ撤销前后的原权限拒绝优先，没有新增source调用。无支持生产source和实际fee authority。

两段55表窗口分别是owner重复/extra/foreign请求窗口和显式fixture READ撤销之后的拒绝窗口；测试**实际原行严格before==after**，原件持久保存每表行数及前后FP。审查核其55表FP相等及严格执行oracle，**没有独立重算DB原行**；窗口之间fixture显式撤权不误称全程零表变更。源码中provider/Settings读取trap及执行期guard的forbidden/downstream记录均为空；当前literal资格未触达。真实请求/模型/Worker/有效LIVE许可0，不推断实际费用已核实为0。

完整候选原件仍为非执行诊断；15个已保存数据拒绝记录及三原合同版本投影属于新节点内部合成oracle。未知费用/实际免费来源没有被bool/hash或诊断替代。

## 工具闭合问题与保留限制

测试没有失败或重跑。首closure helper拼错不存在的pb_trial_dispatch路径而exit1，失败脚本与observed tool-result metadata保留；该metadata**不是当时独立捕获的raw stderr文件**。后helper打印时先前manifest已把其重定向stdout记录为0字节，原旧manifest/实际274字节stdout均保留；closure-correction.json明确最终只用manifest-final.json核完整实际字节。本审查核了该差异，没有改写原件。

结论仅为生产证据要求/非权威诊断/缺源拒绝接点，未注册来源、provider/sender、FeeAuthority或installer，未启用默认LIVE或生成有效令牌。实际生产权益/强制不可收费/软件资格成功链仍缺；真实模型/费用/语义、Windows/native、PG、远端CI、旧永久取消窗口均未执行或提升。未背书后续push/部署。manifest生成后本审查目录停止全部写入。
