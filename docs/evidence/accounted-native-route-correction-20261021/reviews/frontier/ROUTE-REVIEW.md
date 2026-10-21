# 历史第三 Mock 与当前 candidate：静态路线对账

结论：**历史 Mock 到达原 G0 与生产默认 account 硬拒绝同时成立；当前 native candidate 尚未接入那条原 G0 构造链。** 337/66 下级回归不能称旧 G0 修复，也不能因生产硬拒绝就推断原隔离 Mock 前缀不可达。

本轮只读 Git 源码、归档 manifest/设计和当前调用点，使用标准只读文本/哈希工具；没有执行产品、测试、DB、Worker、Mock、完整 prepare、trial commit、launcher 或业务。仓库写入0，仅本 /tmp 报告。不建议新增 stub、代码或窗口；历史 grant 已消费，静态路线不是任何执行授权。

## 冻结来源确实相同

历史完整 SHA 为 `cdda2b2ed6bce1393b90a500c0377294e4d82e34`，当前读取 HEAD 为 `824dfed3e9294727fd05aa88140d66b58b60ba3b`。对 `RUN/source-manifest.json.gz` 解压后的完整文件 SHA 为 `632ac8ae7be4060d7cebe8c12df26fdfa16f34de8243d6af506e281f6d2584db`，符合历史 receipt 的该原件 SHA。其内逻辑 source digest `9069483f35b43e61dcfb3be4ed92cd4c8eb5fc00c51a2e47ef957b5efd6118a4` 是不同概念，不能与文件 SHA 混用。

独立抽查以下六个 manifest 项，逐项与 `git show cdda2b2:<path>` 计算 SHA 对照，全部匹配；前三 helper 及两个硬门文件又与当前工作树相同：

| 文件 | 历史 manifest = 历史 Git SHA | 当前是否同 SHA |
| --- | --- | --- |
| scripts/diagnostics/g0_prefix.py | 5e8a3a948dc689ceb16cb91a3a1def8eadf02f9a16f3275580fa11bfcfe2c006 | 是 |
| tests/test_spec_production_controller.py | 4a9d6856b05304f3d16614db7f8b4ed92d58481c8d344aadb763bd2216dd53c3 | 是 |
| tests/test_pb_spec_production_controller.py | eee8394578c643989c3858826fa2f15ec41fe02436be574e3f6bbfea2c764146 | 是 |
| src/sim2act/production_evidence.py | 18d31d67f47fc3946bb2d846deca2ec653d9d5b786ac7fc71307061a5c3f4258 | 是 |
| src/sim2act/production_trial_admission.py | efe92f8dbd97cba94ff19dd6faaad0a43c1613625494b118d493b120dee01b7a | 是 |
| src/sim2act/natural_spec_runtime.py | dd2eaff6dcb362fce4c1408f8df6dc76dc31a4c427e2ec7c8d34328bbf73c934 | 否；当前77907505b42d1e46cc8d133b91a2349ebdd5c2df8b06d6a398bde668a82130e6 |

这是指定六项核查，不冒称重新审核全部4137项或重做历史执行。

## 历史为什么能过 account 门

`g0_prefix.run_prefix` :28 导入原 configured，:92 调用 `configured(..., prepare_case=prepare_pb)`。相同冻结 helper 在 test_spec_production_controller.py:100–102 安装三项原合成测试替换：controller.environment 为 test_only/SQLite 断言；evidence.resolve_account 为固定合成 SourceVerificationResult；admission._qualified 为测试 no-op。原设计 README 第9行明确这些边界不是现实账户/软件资格通过，不能新增 ALLOW 或改账链/批准/时间门。

prefix 内“No account/qualification/approval helper is replaced here”只描述该函数没有直接再替换；不能据此忽略它调用 configured 所间接安装的三项边界。原 production_evidence.resolve_account 硬拒绝代码当时就存在，SHA 与当前相同。

历史继续原 Generate3→Source2→提取/发布/实例/Cold首响应1；wrapper 只包原 `_cold_model_before` 的停止/记录边界。历史 runtime 的 :2967 `_ColdTrialGraph(..., completed=completed)` 没有 candidate 参数，原 advance_model 进入真实 commit→_prepare。历史原件记录 G0_ORIGINAL_REJECTION_NO_W5、6 exchange/8 method，G0 30.985113144秒并原期限拒绝。此处仅读原记录，不重新执行、不把有仪器结果当性能验收。

## 当前原硬门与 candidate 的两个缺口

生产默认：production_evidence.py:188–196 `resolve_account` 先 requirements_for，再 `_deny(SOURCE_MISSING)`；不存在受支持的生产来源。spec_production.py:54–69 source 调原 approval，再 resolve_account、check_source、_qualified；resolve_account 没有原 configured 时即已拒绝。另 controller.environment :37 本身也拒绝 test_only/SQLite，历史 fixture 明确替换了它。

当前 G0 内原顺序可精确定位：

`_ColdTrialGraph.commit:2922 → _prepare → :2738 dispatch._journal_source → pa_trial_dispatch:1188 spec_production.source → resolve_account`。

该点在 :2742 journal、:2750 accounted Source、:2765 accounted Generate 之前。因此当前下级 candidate consumer 测试不沿用 configured 时，在真实 `_graph_pb_accounting` 继续原 account 拒绝是预期负例，不是历史 Mock 可达性的反证。纯 `_journal_state/_graph_journal_state` 不能笼统称作 resolve_account 硬门；这里直接拒绝的原位置是 `_journal_source/spec_production.source`。

连接缺口独立于上述资格边界：当前 `_ColdTrialGraph.__init__:2442` 虽接受 `_accounted_candidate=None`，两个实际 runtime 构造点 :3048（pre `_cold_model_before`）及 :3316（post）都没传它。当前 g0_prefix 仍只 wrap 原 context，不创建或传候选。故即便复用原 configured 三项边界，现有 prefix 调用也只到默认原路径，不能自动测到 candidate。

## 唯一最小接点的静态定位

可以复用的上游是已冻结原 fresh-Mock prefix、configured 三项合成边界以及完整原审批/账链/Mock保护；不需要另造 account ALLOW stub。需要区分“被测 native candidate”时，既有签名的最小接点位于原 pre 构造点 :3048：同一 `_cold_graph_read` guard 与生命周期中的候选须在该 `_ColdTrialGraph` 构造参数中实际出现，原 `_cold_first_binding`、Source→recipe→backend→Generate、五函数及停止边界不因此换成 stand-in；post :3316 仍不是候选入口。

这只是指出当前缺失的调用边，**不提出或批准本轮实现/新窗口**。具体 bounds 是否可使完整输入走 OWNED、原 full prepare/两次 continuation 是否通过、G0是否改善均未测；只传参数也可能 LEGACY，不能按名字认作 candidate 性能结果。337/66 原件仅证明已声明的离线 helper/coordinator 范围。
