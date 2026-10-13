"""Build the delivery narrative only after both actual frozen runs close."""
import hashlib
import json
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path('/workspace/Sim2Act-pa-provider')
DEST = REPO/'docs/evidence/pa-natural-spec-20261012'
REVIEW = ROOT.parent/'independent/integration-r2'

def load(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

result = load(ROOT/'final-r2-results.json')
history = load(ROOT/'historical-rounds-r2.json')
ui = load(ROOT/'final-r2-ui-summary.json')
bridge = load(ROOT/'author-independent-source-bridge-r2.json')
archives = load(DEST/'archive-verification.json')
counts = result['counts']
assert result['selected'] == 231 and counts['FAIL'] == counts['ERROR'] == 0
assert result['process']['exit_code'] == 0 and result['process']['source_differences'] == 0
assert bridge['independent_current_unique'] == 38 and len(bridge['overlapping_nodeids']) == 34
assert ui['total_checks'] == 87 and ui['total_asset_gets'] == 160
skip = [n for n in result['nodes'] if n['status']=='SKIP']
skip_text = '; '.join(n['nodeid']+': '+n.get('diagnostic','See XML') for n in skip) or '无'
rows = '\n'.join(f"| {v['scenario']} | {v['checks']} | {v['distinct_assets']} | {v['asset_gets']} | {v['status']} |" for v in ui['cases'])
archive_rows = '\n'.join(f"- [{label} 完整包]({label}-complete.tar.gz)：{v['entries']}项（{v['files']}文件、{v['directories']}目录、{v['symlinks']}链接），{v['archive_bytes']}bytes，SHA256 `{v['archive_sha256']}`；包内全部{v['verified_entries']}项复核一致。" for label,v in archives.items())

report = f'''# P-A 未标注短规范：有限工程验收

已完成目标驱动、默认关闭的模型抽取节点、受保护样例预览、原子JSON保存和新材料冷复用。来源无需synthetic标题或MUST/MUST_NOT标签。模型决定有限recipe、事实分类及关系；机器核结构和原文引用，语义保持UNKNOWN/NOT_RUN、owner PENDING。

分支 `dev/pa-natural-spec-20261012`；原基线 `259f583eba6dd6c5580834878da6bd3cb1f648a7`。功能提交 `1b03567aa7f3f8d643c1026766186538be7e5370`，队列兼容修复 `2fa5e92bd184164350451233730b7b78b99c74c3`；最终实际冻结测试/资格提交 **`c28e91a5066e59c1c36e76b910515298d0d1eb28`**。后续交付提交仅补文档、证据及字节保留规则，不改变冻结src/tests/fixtures/pyproject。

## 实际终态

作者一次完整最终重跑 **231个唯一节点：{counts['PASS']} PASS、{counts['FAIL']} FAIL、{counts['ERROR']} ERROR、{counts['SKIP']} SKIP**，exit0；pytest `{result['pytest_summary']}`，runner墙钟 {result['process']['wall_seconds']:.3f}s。SKIP原原因：{skip_text}。没有把SKIP计通过。

当前SHA独审两次完整运行 selected36+独有CAS/cancel probes2：**38唯一、38 PASS、0 FAIL/ERROR/SKIP**，均exit0，runner墙钟164.352/3.493s。34节点与作者重叠，另有旧233/a747冷续用代表2及独有probe2；两方分母不相加。独审结论LIMITED PASS，当前有限修复无新核心阻塞。

原827轮完整作者仍为 **218 PASS/9 FAIL/1 SKIP、exit1**，未覆盖。原827独审79 PASS属于旧SHA；当前38没有重新跑全部79。两版本完整434项图有6项变化/428项相同，静态字节桥不会把旧测试升级成当前实跑。

当前作者/独审各有**434项**src/tests/fixture/pyproject完整源图，各自运行前后及双方逐路径SHA全部**0差异**。当前独审before/after文件自身SHA均 `519f6618aa5d88df95e8c2c22c62771c7d125907c4874bfffc3845a2c1c7cc84`；作者JSON包装不同，不称两个JSON字节相同。73-file资格新pin **`e3e4bf188a1c4932ba0950916c5fc570da8a4f6a4c47a0f074b1afd4c4d23ba0`**，review baseline827、candidate2fa；仅唯一pin literal归零避免hash循环。原CHANGED、ANCHOR_HASH、旧anchor字节及两份历史source FP不变；未知来源仍拒绝，旧实例仍须精确批准。

全体src/sim2act Ruff PASS。全体mypy检查74文件仍FAIL：status_report.py/tools.py中原有5错误，两文件相对259无变更；不称整体类型检查绿。最终diff检查另核；原始诊断保持字节，不删改空白。

## 实际产品合同

- 单个授权TXT/MD≤2048 UTF8 bytes、≤40行；完整Goal及最多16人工未决项进入实际请求。source来自实际resource.read；产品不用gold、关键词/正则或源预标签替代含义。
- 合成Intern sender用3条生成响应消费read和实际checker反馈。单/双模型、逻辑独立/顺序反馈图均运行；独立分支按稳定次序串行，未实现同时dispatch。checker PASS后换另一合法图仍VERSION_CONFLICT、0应用、无重发。
- 应用只保存recipe和opaque样例seal；新Store/Worker实际读取另一中性材料、发送其新模型输入并产生新回执与JSON。新材料预览MODEL_EXECUTION_REQUIRED，不使用旧答案伪算抽取。
- 当前只test_only+mock+显式MockTransport可执行；普通MockModel/客户端replay不兜底。真实请求/费用0。预算取平台/Release/冻结Run/节点最小值，不提高原4请求/4工具、1024输出、64000保守额度、300秒deadline和30秒lease。
- raw先存owned Attempt，再核identity/usage/schema/quote；unknown只原key读取。取消/撤权/源或Goal变更/version/lease/fence/deadline/审计竞争、迟到和坏响应不得VERIFIED/保存。最后节点回调后重新核当前授权和完整账本。
- JSON保留全部原文、事实、条件/例外关系或UNASSIGNED、open_question、未覆盖片段及人工未决；引用PASS不授予语义PASS。8合并事实/8000字符上限，超界失败不截断。
- resource/局部grant/effect/完整intent+receipt/typed data/instance CAS/Run+AppRun终态同事务；实际测试回滚、坏operation/instance scope、rejected锚、元数据和末回调。
- 撤权私有cell探针实际校准：full SELECT会拒绝，产品撤权后full private cell0/blocked0。raw保留、reservation不退款、typed0/save operation0。owned raw写仅允许精确NULL-presence CAS，不声称所有backing JSON/null求值0。
- 新队列claim仍先授权，再读私有body。GRANT_REVOKED/RESOURCE_UNAVAILABLE记WAITING_RESOURCE，结构/版本错误FAILED，已取消优先CANCELLED。错误收尾只header、binding scalar、独立ACCEPTED及实例scope标识；按原key/owner/iid/release/requestFP更新原QUEUED AppRun和Run。version/fence/cancel/CAS失败整事务回滚，坏pointer不污染其他历史；恢复授权前resume被拒。
- 旧标记规范仍零model Attempt/request。旧字面应用、Goal边界、bindings、bounded agent实际回归；233/a747代表使用原TTL的本地合成replay clock，不装旧源码、不重签旧seal，不称通用旧库升级。

## 实际页面

| 新场景 | 检查 | 每场景不同资产 | 资产GET | 结果 |
| --- | ---: | ---: | ---: | --- |
{rows}

作者当前新页面87项检查/160次GET，20种真实加载资产逐SHA匹配；旧Goal页面5种配置重验也真实执行。当前独审旧Goal5页检查38/38/33/39/45，各20资产SHA匹配。采用TestClient进程内HTTP/IPC/JSDOM，**不是native browser**。失去响应只原key恢复；编辑/undo使迟到响应不能画结果；篡改sample或sample_nodes不能确认。

## 失败保留和修复证据

全部既往 {len(history['rounds'])} 轮XML保留实际 **{history['historical_failures']} FAIL/{history['historical_errors']} ERROR**，与最终重跑分开。827完整9F中4是前置scope门提前导致旧队列错误状态；5是继承NODE_PATH未指向已安装jsdom。修复保留前置门，只加精确元数据错误事务，并为重跑子进程显式设置已有模块路径；没有安装依赖或改全局环境/凭据。新坏pointer夹具首轮触发原UNIQUE约束、6P1F，原日志保留；明确孤立另一历史row后7P，不删除数据库约束或降低断言。

更早recipe值验证、Replay误分类、cold preview、lease竞争安全停止、metadata初始化、授权正文读取次序、页面分派及夹具断言失败也保留。原独审S1–S6及cancel CAS建议都是静态发现，不计动态FAIL。最终独审无FAIL；原报告/manifest和author失败XML/SQLite/wire不改。

## 未运行与真实验收条件

真实模型/费用/凭据、账户免费权益、人工语义、完整P-A/P-B、PG、Windows、native browser、旧源码安装/通用DB升级、wheel、CI、部署和永久取消旧安装/取消窗口均**NOT_RUN/NOT_VERIFIED**。不称远端CI绿，没有本轮工具授权拒绝/空间escalation/未知临时清理/已拒browser重试。

[真实验收提案](PANaturalSpecRealAcceptanceProposal20261013.md)限定唯一intern-s2官方端点、两份中性材料、最多7请求/7168输出tokens/三Run保守总额≤192000及原deadline/lease。零付费、凭据状态未核；精确LIVE/跨Run/强制零收费门尚未具备，**提案不可执行**。当前无需token，不发送真实请求。

[产品合同](PANaturalSpec20261012.md)；[完整证据入口](../evidence/pa-natural-spec-20261012/README.md)。正常push只指定本分支，无force/main/core写。保护远端、原owner草案、最终远端完整SHA和clean/ahead/behind由交付外部回执及最终答复核对，避免自引用提交SHA循环。
'''
(REPO/'docs/F2/PANaturalSpecAcceptance20261013.md').write_text(report)
readme = f'''# P-A 未标注短规范工程证据

最终冻结 `c28e91a5066e59c1c36e76b910515298d0d1eb28`。作者231选中：{counts['PASS']} PASS/{counts['FAIL']} FAIL/{counts['ERROR']} ERROR/{counts['SKIP']} SKIP；当前独审38唯一/38 PASS/0F/E/S，交集34，不能相加。双方434完整源图前后/互比0差异；73-file pin e3e4bf188a1c4932ba0950916c5fc570da8a4f6a4c47a0f074b1afd4c4d23ba0。

[完整验收](../../F2/PANaturalSpecAcceptance20261013.md) · [作者当前结果](author/final-r2-results.json) · [作者当前JUnit](author/final-r2.xml) · [当前独审](independent/integration-r2/FINAL_REVIEW.md) · [当前源图桥](author/author-independent-source-bridge-r2.json)。当前独审报告SHA `{sha(REVIEW/'FINAL_REVIEW.md')}`，manifest SHA `{sha(REVIEW/'manifest.json')}`。

[原完整9F轮](author/final.xml)仍218P/9F/1S/exit1；[原79独审](independent/final/FINAL_REVIEW.md)只属于827。所有 {len(history['rounds'])} 历史XML的 {history['historical_failures']} 原FAIL完整保留，不覆盖、不并入当前分母。source/资格旧快照、静态发现、实际SQLite、raw/wire、HTTP/JSDOM结果都在完整包。

{archive_rows}

[作者全清单](author-full-manifest.json)、[独审全清单](independent-full-manifest.json)记录每项大小/SHA、类型和链接目标；[包内复核](archive-verification.json)重新流读包内全部成员，字节/目录/链接全一致。只排可重建cache/__pycache__，没有删除未知数据；直接副本逐字复制。原失败和原sealed报告亦保留。

LIMITED工程结论；真实请求/费用0，semantic UNKNOWN、owner PENDING。真实model/凭据/paid/人工语义、PG/Windows/native/CI/deploy/完整P-A/P-B/完整旧升级均NOT_RUN或NOT_VERIFIED。[具体真实提案](../../F2/PANaturalSpecRealAcceptanceProposal20261013.md)当前不可执行。
'''
(DEST/'README.md').write_text(readme)
manifest = {str(path.relative_to(DEST)):dict(bytes=path.stat().st_size,sha256=sha(path)) for path in sorted(DEST.rglob('*'))
            if path.is_file() and path.name!='artifact-manifest.json'}
(DEST/'artifact-manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(report=str(REPO/'docs/F2/PANaturalSpecAcceptance20261013.md'),artifact_entries=len(manifest),
                     artifact_manifest_sha256=sha(DEST/'artifact-manifest.json')),indent=2))
