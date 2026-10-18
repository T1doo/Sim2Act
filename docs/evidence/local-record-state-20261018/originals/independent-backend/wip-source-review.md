# 本地结构化记录：非作者有限源码独审（冻结候选）

本人只读 `/workspace/Sim2Act`，没有编写产品或资格测试。父级是唯一产品写入者；审查产物和自有隔离数据库仅写到本目录。此报告当前对应候选产品 `a38c33f7496dca3da079d59bab16f13b5c283d1e`，资格测试提交 `81ad223bf72fb6e15af03ef6aca87af70e9bf4f8`。父级随后修复3项mypy类型收窄，最终冻结字节桥及资格另报；不能把候选报告冒充最终状态。

## 当前有限结论

经独立源码复核和下述有界实际probe，已知P1/P2均在候选a38收敛，未发现新的明确P1/P2阻塞。该判断覆盖固定CREATE及OPEN→DONE typed合同、独立业务record_id/revision、完整事件投影/历史、原键恢复、同事务保存/Operation/typed/CAS/finalgate、当前授权以及旧家族入口隔离。不是全系统安全证明，也不是独立亲跑作者UI资格。

新族明确拥有受限的typed业务适配器，不伪称save_text工具自身理解业务记录。其canonical ActionSpec保持既有 `artifact.save_text@1`；实际仍调用原 `write_text_artifact`，复用user∩projectruntime交集及project_write/transactional，不新增executor.ref、Principal或write Grant。每事件新增JSON成果及原helper既定2条derived resource.read Grant，不能称Grant行完全不变；preview不保存JSON。当前投影来自完整事件链，未把最后报告改名冒充记录。

## WIP发现及收敛（保留历史，不重写为初次即通过）

1. **P1：原key成功回执缺业务成功证明。** 早期 `request_state` 在accepted分支经accepted_binding后只根据Run.status回传成功，未调用完整projection；缺typed或Operation可能仍显示成功。该结论首先来自当时源码阅读，未独立在未修字节上动态复现。候选现 `local_record_apps.py:691` accepted分支调用projection并唯一匹配同Run/AppRun历史；`:600` projection验证typed版本、同iid/release、原接受双seal、唯一VERIFIED Operation/intent/local_effect/receipt、真实JSON字节hash、Run/AppRun结果、COMMITTED事件及全链折叠，且拒绝未成功AppRun的output/result/Operation残留。本人后修实际独立probe证明缺typed或Operation时原GET拒绝成功，且无写入。**修前完整文件字节没有在本目录独立封存，不能声称补回；后修字节、日志均保存。**
2. **P2：家族独立锚不足。** 原is_instance只沿当前instance.release_id识别；单指针污染可丢失新族识别。原approval旧路由guard只凭approval.kind识别，污染kind可能先碰私有payload。候选`:188`加入原INSTANCE双seal.response.id OR识别；`:436` instance_header要求唯一原创建pair、当前release_id及原releasefp精确匹配；`:210` reject_legacy增加PREPARE.response.id与RELEASE_SEAL.approval_id元数据OR。本人候选实际SQL分类probe验证iid指针改旧、approval.kind改旧、以及PREPARE移除后仅RELEASE_SEAL存留，三者均UNSUPPORTED_CAPABILITY。
3. **P2：失败路径提前读取整行私有Run。** 原fail_job在仅metadata scope后select(runs)；Worker claim后历史读取权限被撤销时，该路径无须读取private frozen/result。候选`:839`只选择id/fence/status/cancel_intent/version并使用原state_write终结，未读取私有整行。

另核实父级修正：原释放批准已过期且未消费时，GET原receipt可读而commit仍严格拒绝；旧generic approval commit在完整payload前guard；RUNNING控制保留active lease，原fenced Worker完成pause/cancel；只允许合法Run RUNNING/AppRun QUEUED claim过渡，其余状态仍精确核验；开始及最终guard后检查原created_at+min平台/manifest run_seconds及原preview期限。

## 本人实际执行的独立短验证

- `wip-recovery-probe/`：独立源码快照131文件，local模块SHA `feafa7ad5413986c02947a194183f6300bc07c1f5443dd2846f7eb1d77142274`，是P1修后、最终独立锚修前WIP。1个实际正常NoModel Worker（模型次数0）；原GET成功；删除自有typed/Operation后原GET各409 VERSION_CONFLICT、数据库只读；known fixture精确恢复。probe自身1.78093s。首次setup仅观察器把项目POST的201写成200失败，无Worker或污染；原件保存在first-attempt，不隐藏或计为产品失败。
- `frozen-probe/`：候选a38的132个Git生产文件逐字节复制；a38、81ad与当时工作树0差异、clean。local模块SHA `56230e320d961843ff36a1acc4c97ecb7f2eaa1478d2cd7382dfd0e26520452a`。独立1个实际正常NoModel Worker（模型0），两项原key证明及3项独立锚分类均PASS，known fixture全表精确恢复，probe自身1.809646s，命令退出0。不是3个完整HTTP故障矩阵；后三项为同一自有fixture的元数据分类调用。

原始脚本、全部HTTP请求/响应、stdout、result和源码manifest分别位于以上目录。本人未亲跑作者完整backend/UI资格；父级报告及日志回读将另列，不把作者测试算独立执行。

## 尚待最终关闭

父级a38资格原日志已可读：backend-final.log显示9PASS47.00s，ui-final.log显示3PASS49.48s；尚待按冻结SHA核对原XML、HTTP/DOM证明和源文件前后快照，不能据摘要认定全部产品验收。mypy原件记录3错误，父级正在仅类型修复，尚未在本报告中认作通过。最终重freeze后需单独记录精确字节与必要资格，不将a38旧测试冒充修正SHA亲跑。

未执行真实模型、真实业务语义/场景、Windows、原生PG、远端CI或部署。未访问旧满盘环境，也未重建丢失旧独审报告。
