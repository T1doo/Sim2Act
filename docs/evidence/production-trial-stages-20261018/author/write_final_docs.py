"""Render delivery notes from the closed qualification and exact copied evidence metadata."""
import hashlib,json,xml.etree.ElementTree as ET
from pathlib import Path
repo=Path('/workspace/Sim2Act');root=Path('/workspace/production-trial-stages-20261018')
dest=repo/'docs/evidence/production-trial-stages-20261018'
q=json.loads((root/'qualification-summary.json').read_text())
assert q['final_qualification_passes']==4 and q['real_model_requests']==0
source=q['final_freeze'];runs=q['runs'];final=runs[-2:]
manifest=json.loads((root/'sealed-manifest.json').read_text())
review=Path('/workspace/production-trial-stages-review-20261018/sealed-manifest.json')
a_sha=hashlib.sha256((root/'sealed-manifest.json').read_bytes()).hexdigest();r_sha=hashlib.sha256(review.read_bytes()).hexdigest()
selection=json.loads((dest/'selection.json').read_text())
def seconds(name):
 xml=ET.parse(root/name/'junit.xml')
 return sum(float(s.attrib.get('time',0)) for s in xml.getroot().iter('testsuite'))
rows=[]
for run in runs:
 rows.append('| '+run['directory']+' | '+', '.join(c['verdict'] for c in run['cases'])+' | '+str(run['actual_adapter_entries'])+' | '+str(round(run['execution']['elapsed_seconds'],6))+' |')
readme=f'''# P-A 实际阶段桥：离线原件与有限独审

基线 `4bb3c26f5f67511795771c9187537aee4e852590`；最终源码/测试冻结 `{source}`；普通分支 `dev/production-trial-stages-20261018`。[实现及边界](../../F2/ProductionTrialStages20261018.md)。本片以原Worker/GA/NS实际调用完成新journal与generate3/source2/cold2证明桥；明确UNINSTALLED，全部模型输出为合成MockTransport。

最终同SHA四唯一节点/四次执行/四PASS，链组JUnit {seconds('run-8-chain'):.3f}秒、外层{final[0]['execution']['elapsed_seconds']:.9f}秒；负向组JUnit {seconds('run-8-negatives'):.3f}秒、外层{final[1]['execution']['elapsed_seconds']:.9f}秒，两进程并行。各自652输入/138生产及runner+guard前后零漂移。8生产改变、130生产同基线；基线651输入加一个新测试。此范围只枚举src/tests及pyproject/uv.lock，不混用前片707的更宽口径。

- [资格汇总及外部DB索引](author/qualification-summary.json)、[最终Git冻结范围](author/final-freeze-scope.json)。[链组命令/退出/时间](author/run-8-chain/execution.json)、[JUnit](author/run-8-chain/junit.xml)、[stdout](author/run-8-chain/pytest.stdout)、[stderr](author/run-8-chain/pytest.stderr)；[负向组命令](author/run-8-negatives/execution.json)、[JUnit](author/run-8-negatives/junit.xml)、[stdout](author/run-8-negatives/pytest.stdout)。旧19/12/8/9矩阵重跑0，无新crash恢复矩阵。
- [实际七次阶段结果](author/run-8-chain/actual-tmp/actual-prefix0/actual-pa-stages.json)：原GA生成3、用户确认release/instance、Source2及新B材料+完整Goal冷运行2；每次actual Attempt与新slot一一对应，实际6个间隔均>=60秒，旧预算/SENT行0，14份PA request/response body档案。七份响应raw SHA均不同于canonical SHA，均从实际bytes复算；不是caller body摘要或泛型协议通过。
- [当前Cold与Source历史入口只读核验](author/closed-output-audit.json)：Cold结果/人工入口精确同Run、B材料可读、owner PENDING；Source旧Run仍有结果/历史，但新结果写入后owner内容按VERSION_CONFLICT拒读。两者semantic_goal_acceptance NOT_RUN，未代替人工验收。[九项新鲜前缀反证](author/run-8-chain/actual-tmp/actual-prefix0/fresh-proof-rejections.json)：同读段写epoch失效、scope缓存命中实际重授权/写撤销、无写真实到期，以及仅accounting、混旧backend、canonical/raw/aid/scope损坏，均实际拒绝，窗口全55表严格不变、无新模型。
- [错误业务schema](author/run-8-negatives/actual-tmp/test_known_accounting_cannot_a0/business-schema-rejected.json)：HTTP200/known1000可计账，原第一步业务失败、无结果、无下阶段，handler1且再次Worker.once不重发。[Store替换](author/run-8-negatives/actual-tmp/test_original_controller_store0/late-store-refused.json)：合法第二Store/engine同URL，setter拒绝/poison，原Store保实际body+usage1000，原Run FAILED，foreign engine SQL0，handler1/no resend。
- [链离线guard](author/run-8-chain/offline-guard.json)、[负向guard](author/run-8-negatives/offline-guard.json)及各组保存的guard.py：pytest sessionstart先于fixture，禁止真实HTTP/socket/环境发现/MockModel fallback，只允许原InternModel+exact MockTransport+固定synthetic token。最终adapter {q['final_synthetic_adapter_entries']}次，全部本轮历史合计{q['actual_synthetic_adapter_entries']}次，真实模型0；嵌套adapter方法不能另算请求。原heartbeat仅被观察，未mock成功，原lease<=30、CAS与deadline保留。

## 全部执行历史

累计{q['total_executions']}次node执行、{q['pass_count']}PASS、{q['error_count']}ERROR、{q['failure_count']}FAIL；唯一node4。最终四PASS不抹掉前序失败。

| 原件目录 | JUnit结果 | 实际synthetic adapter | 外层秒 |
| --- | --- | ---: | ---: |
'''+ '\n'.join(rows)+f'''

前五次依次暴露claim新binding缺接线、原checker协议、Core Run与AppRun key、发送前lease、接收后lease；run6再次保留knownbody但验证区间超原lease；run7已完成Source而Cold reserve事务退出，没有Cold adapter，精确异常语句当时未记录。run6负向的C通过，D在handler之前因test_only=False的SQLite构造错误失败，后修合法独立Store再验；未放宽隔离断言。各run保存精确源码副本、inputs/helpers before/after及原stdout/stderr/JUnit，不把复跑冒称首轮绿。run1顶层runner在一行调整后按该run保存副本恢复并核精确helper SHA，后续run在启动时直接保存copy；各run前后helper均稳定。

[原只读cProfile](author/readonly-profile.json)/[同源段优化诊断](author/readonly-profile-optimized.json)及各txt保留；前者stage_review14.805秒/13409 SQL，后者只调私有_stage_current6.560秒/4782 SQL，入口范围不同且有cProfile开销，不是同口径性能保证。[run6闭合组件计时](author/controller-read-components.json)七次bound/stage分两读段22.200秒，DB byte SHA前后同；没有lease/commit_guard/receipts或产品运行，不算资格PASS，也未修改旧Run/批准。Cold旧proof只读7.436963秒/5324SQL，source_scope79/77次约4.165秒；双reauth WIP诊断10.212086秒/3867SQL，墙钟未更快，不承诺性能，最终去掉一遍冗余reauth。该诊断WIP源码从一行差异重建并核运行时已记SHA，明确标作reconstructed；不是原始整文件捕获，也不是补回旧满盘报告。

## 设计、静审与原件封存

[设计v1](author/minimal-design-v1.md)、[v2](author/minimal-design-v2.md)、[claim/serializer修正](author/minimal-design-v3-amendment.md)、[同原读段](author/minimal-design-v4-read-segment.md)、[原heartbeat边界](author/minimal-design-v5-controller-heartbeat.md)、[controller读段](author/minimal-design-v6-controller-read-segments.md)、[完整scope同段复用](author/minimal-design-v7-source-scope-read-segment.md)。[独立设计审](review/design-review.md)、[最终有限独审](review/final-independent-review.md)、[结构化复核](review/final-verification.json)。先前静审的terminal RUNNING门、私有Attempt读取顺序、serializer shadow及HB后stop/time P2均保留修复记录；早期usage8误读已明确撤回，实际本片wire固定known1000。

[作者manifest](author/sealed-manifest.json) SHA256 `{a_sha}`；[独审manifest](review/sealed-manifest.json) SHA256 `{r_sha}`。原作者/独审目录封存后停止写入，仓库仅逐字副本。[总选择清单](selection.json)为{selection['file_count']}路径/{selection['total_bytes']}B，DB复制0；[作者](author-selection.json)/[独审](review-selection.json)逐项列原绝对路径/bytes/SHA。DB仅外部保留，作者记录hash，独审仅stat、没有SQL重建或读取私有参考。以上数量不含本README和selection元数据。

## 真实API与未执行

用户已授权既有Intern免费额度；[候选与明确剩余条件](author/real-prerequisites/candidate.json)、[仅presence/nonempty布尔](author/real-prerequisites/credential-presence-only.json)。当前INTERN_API_TOKEN确实存在且非空，应用支持此别名；没有显示、复制或hash其值。离线子进程刻意移除真实凭据，不能据此说未配置。真实model POST=0。两次无凭据公开Chat根GET均失败，[有限重试原件](author/real-prerequisites/public-read-bounded-retry.json)保存DNS errno-3及proxy tunnel403；停止进一步探测，没有绕拒绝路径。

真实账户身份、当前剩余额度及强制零费/禁止付费fallback事实仍未核实；真实source producer/controller binding未安装，production resolver/preflight继续默认拒绝。新候选上限7次、每次输出1024/合计7168、>=60秒、无自动重试，未知费用或余额发前拒绝；未推断90m余额、未拿其它产品价格替代。不是缺用户授权。

未执行真实账户/费用/模型/语义/人工评分、PB新资格/AT10、LIVE安装、浏览器本片新验收、PG、Windows/native或远端CI。旧满盘独审未落盘报告NOT_RECOVERED，不补签；本片不签整体F2或生产LIVE。
'''
(dest/'README.md').write_text(readme)
report=f'''# P-A journal接入原generate/source/cold控制器

接续接受基线 `4bb3c26f5f67511795771c9187537aee4e852590`，保留原8fc祖先；唯一repo writer=root，普通分支 `dev/production-trial-stages-20261018`。源码/测试冻结 `{source}`，8生产文件改变、130生产同基线；无需新表、executor、Grant或第二份旧预算。

新JournalTrialBinding只接受P-A TrialContract/V2，固定原Store、Settings、完整contract、approval、account和原worker身份。它明确UNINSTALLED，仅test SQLite+exact MockTransport；PBTrial拒绝，旧PATrial路径保留。原Worker.claim新增限定支路、排除qualified-associated Run，并重核owner/project/runtime、冻结材料/Goal/phase/版本/lease/fence。默认生产source resolver/preflight未安装。

每次沿原GA/NS Intern adapter、原controller guard与新journal/source读取执行，实际Core Attempt、request bytes、capture、usage及原PA/NS档案逐项绑定。accounting接受不代替业务成功；生成3须原checker/candidate/anchors，Source2和Cold2须原NS操作VERIFIED和同Run结果，Cold另证原Source2来自同新backend。raw bytes及canonical response分别保存/复算；旧预算/SENT不镜像造账。

原Store被替换时binding失效且保原Store接收事实；迟到body/known usage先commit，再拒业务，不退款、不重发。terminal验证仅原成功事务continuation，未把终态重开为send admission。原NS同步心跳接到新增journal事务边界，仍30秒CAS且不能复活expired；deadline不大于原node、contract Run300或原expiry，HB提交后才publish，前后检查stop/time。

完整generation证明只在现SourceReads同Store/Connection/driver transaction/thread/写epoch内复用，首个完整history/checker/candidate/authority证明不省，命中重核source/authorities并deepcopy。NS写前和最后事件后显式各开原读段，第一处写入立即作废旧段，不跨写/事务保有权限。完整生成scope首调用保留全部原门；只有实际3新marker和自然generation双锚/无LIVE aid才复用，命中先完整reauthorize再双标量锚与epoch复核。仅新binding延长controller段；旧PB门保持，generic wrapper在已有SourceReads且实际gen3新marker时也可命中，未声称所有PB行为完全逐字不变。

最终同SHA四节点四PASS：原generate3→source2→新B材料+完整Goal cold2、结果/同Run人工入口；新鲜实际前缀九个拒绝窗口；错误业务schema；Store替换隔离。两进程并行，原1RPM实钟未跳过。Cold可读/PENDING，Source历史内容在新结果后拒读，semantic_goal_acceptance仍NOT_RUN。保留累计{q['error_count']}次ERROR和{q['failure_count']}次fixture FAIL、以及一次较早C PASS；不冒称首轮全绿。最终synthetic adapter{q['final_synthetic_adapter_entries']}次，真实模型0。[全部命令/JUnit/原始档案/失败与有限独审](../evidence/production-trial-stages-20261018/README.md)。

用户已授权现有Intern额度，INTERN_API_TOKEN在当前环境存在且非空，未泄露/复制/hash值；offline runner主动去除真实凭据。真实API仍阻于公开Chat根GET的DNS/proxy403、当前账户/余额/强制零费事实未知，以及真实source/controller安装尚未完成；不是缺授权。真实model POST=0，不推断90m剩余，不新增付费或凭据，不绕访问拒绝。

未执行真实语义/人工评分、PB新资格/AT10、LIVE、浏览器新验收、PG、Windows/native、远端CI；旧19/12/8/9矩阵重跑0，旧满盘未落盘报告NOT_RECOVERED。原DB到外部IO边界仍不宣称跨系统原子取消。
'''
(repo/'docs/F2/ProductionTrialStages20261018.md').write_text(report)
print(json.dumps({'readme_bytes':len(readme.encode()),'report_bytes':len(report.encode())}))
