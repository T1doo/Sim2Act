"""Render the final repository report from completed, sealed evidence."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path('/workspace/Sim2Act-pa-provider')
DEST = REPO / 'docs/evidence/pa-natural-spec-20261012'

def load(path):
    return json.loads(path.read_text())

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

result = load(ROOT / 'final-results.json')
history = load(ROOT / 'historical-rounds.json')
ui = load(ROOT / 'final-ui-summary.json')
bridge = load(ROOT / 'author-independent-source-bridge.json')
archives = load(DEST / 'archive-verification.json')
review = load(ROOT.parent / 'independent/final/review-result.json')
assert result['selected'] == 228 and result['counts']['FAIL'] == result['counts']['ERROR'] == 0
assert result['process_exit']['exit_code'] == 0
assert review['combined_unique'] == 79 and review['combined_counts'] == {'PASS':79,'FAIL':0,'ERROR':0,'SKIP':0}
assert bridge['source_differences'] == 0 and len(bridge['overlapping_nodeids']) == 75
assert ui['total_checks'] == 87 and ui['total_asset_gets'] == 160

rows = '\n'.join(f"| {v['scenario']} | {v['checks']} | {v['distinct_assets']} | {v['asset_gets']} | PASS |" for v in ui['cases'])
archive_rows = '\n'.join(f"- [{label} 完整压缩包]({label}-complete.tar.gz)：{v['entries']} 项（{v['files']} 文件、{v['directories']} 目录、{v['symlinks']} 链接），{v['archive_bytes']} bytes，SHA256 `{v['archive_sha256']}`；从包中复核全部 {v['verified_entries']} 项。" for label,v in archives.items())
counts = result['counts']
report = f'''# P-A 未标注自然短规范：有限工程验收

已完成目标驱动、默认关闭的自然规范模型节点、受保护样例预览、原子 JSON 保存，以及新材料冷复用。来源无需 synthetic 标题或 MUST/MUST_NOT 标签。模型决定有限 recipe、事实分类与关系；服务端核结构和原文引用，语义保持 UNKNOWN/NOT_RUN、owner PENDING。

独立分支 `dev/pa-natural-spec-20261012`；基线 `259f583eba6dd6c5580834878da6bd3cb1f648a7`。核心提交 `1b03567aa7f3f8d643c1026766186538be7e5370`，实际冻结测试与资格提交 `82717272e61c2fa174ad8772e54cd9e9eb947c49`。后续交付提交仅补文档、原始证据和其字节保留规则，不改变冻结 src/tests/fixtures/pyproject。

## 实际结果

作者一次完整最终运行选中 **{result['selected']} 个唯一节点：{counts['PASS']} PASS、{counts['FAIL']} FAIL、{counts['ERROR']} ERROR、{counts['SKIP']} SKIP**，process exit0，pytest `{result['pytest_summary']}`。JUnit 记录 suite 时间 {result['suite_seconds']:.3f}s；外层启动/墙钟未独立记录，标为 NOT_RECORDED。唯一 SKIP（如有）的原原因在完整 XML 中，不计通过。

独审三次完整运行：selected77、撤权 raw-response probe1、checker-PASS 后换合法图 probe1，**79 个唯一节点，79 PASS、0 FAIL/ERROR/SKIP**，三个 runner 均 exit0，墙钟分别 1443.695/15.810/4.172s。75 个节点与作者选集重叠；另有历史233/a747冷续用代表2和独有probe2。两组通过数不能相加。

作者与独审各有 **434 项** src/tests/fixture/pyproject 完整源图，各自运行前后和双方逐路径 SHA 均 **0 差异**。两份独审源图文件自身 SHA 都为 `5a32f41932c6a2ccee283e23dfc1b727a3127b31b28d2ed5d8b21718c6b954ae`；作者 JSON 包装不同，不声称文件 JSON 字节相同。73 个实现文件资格 pin `82dc63fdf2dd21906a5d055a598a765569a27a88ee32196128e2a1952f1e1030` 精确匹配，原 CHANGED、ANCHOR_HASH、旧 anchor 字节与两份历史源指纹不变。资格不会替代旧实例的精确批准，也不会迁移未知来源。

全体 src/sim2act Ruff PASS；15 个本轮改变的 Python 文件 Ruff PASS；diff 检查 PASS。全体 mypy 检查74文件仍 **FAIL：5项既有错误**，涉及 status_report.py 和 tools.py，两文件相对基线259字节未变化；不称整体类型检查绿。

## 实际合同和回归范围

- 单个获授权 TXT/MD≤2048 UTF8 bytes、≤40行；完整 Goal 及最多16人工未决项进入实际请求。plain source 由实际 resource.read 取得；不在产品解析器使用测试 gold/标签语法替代语义。
- 合成 Intern sender 用3条生成响应实际消费 read 和 check_candidate 反馈；合法单/双节点、逻辑独立/顺序反馈 recipe 均运行。独立 DAG 分支按稳定顺序串行发送，未实现同时 dispatch。checker PASS 后只能原候选；换成另一合法图仍 VERSION_CONFLICT、0应用、无重发。
- 应用定义保存 recipe 和 opaque 样例 seal，样例答案只在受保护历史。另一个 Store/Worker 读取另一中性材料并真正产生新模型节点回执和结果。新材料预览明确 MODEL_EXECUTION_REQUIRED，不输出伪造抽取。
- 每节点1条合成请求，最多2模型节点/4本地工具；沿原平台/Release/冻结Run/节点预算取最小值，不提高4请求/4工具、1024输出、64000保守额度、300秒绝对deadline或30秒lease。当前仅 test_only+mock+显式 MockTransport 可执行；普通 MockModel/offline replay 不兜底，真实请求和费用0。
- 响应先保留完整 owned raw，再解析 identity/usage/schema/精确 quote。STARTED/unknown 仅读原 key；取消、撤权、Goal/源/版本/lease/fence/deadline/审计变化、迟到及坏响应不 VERIFIED/不保存。末节点回调后再核当前授权、原生成审计和本次完整账本。
- JSON 保留完整原文、全部事实、条件/例外关系或 UNASSIGNED、open_question、未覆盖片段和人工未决项；引用 PASS 不授予语义 PASS。8个合并事实、8000字符成果上限，超限失败不截断、不丢项。
- 成果/局部 grant/effect/完整 intent+receipt/typed data/instance CAS/Run+AppRun 终态同事务。逐表 rollback、错误 operation Run 链接、AppRun instance scope、完整 rejected anchor、Run metadata 和最终回调故障均被实际测试。
- 独立 SQLite 屏障在撤权前后故意 full SELECT 非空 response 各命中真实 cell 拒绝；产品撤权后 full private cell 0、blocked0。仅允许1次 owned UPDATE 的精确 NULL-presence CAS，不冒称所有 backing JSON/null flag 求值为0。raw 保留、reservation 不退款、typed0、save operation0。
- 旧标记规范继续零 model Attempt/request；旧字面文本应用、新材料 bindings、bounded agent 和Goal边界实际回归。旧233/a747代表使用原TTL的本地合成 replay clock，不安装旧源码、不重签旧seal，不称完整旧库升级。

## 五个当前冻结页面场景

| 场景 | 实际检查 | 每场景不同资产 | 资产GET | 结果 |
| --- | ---: | ---: | ---: | --- |
{rows}

作者和独审各为87项检查、160次资产GET；20种实际加载资产逐源码SHA核对。使用 TestClient 进程内HTTP/IPC/JSDOM，**不是原生浏览器**。绑定响应丢失只原key GET恢复；迟到响应遇编辑/undo不能画结果；篡改样例事实或 sample_nodes 均不能确认。

## 失败和独审历史

当前任务早期19个独立 XML 轮次保留 **{history['historical_failures']} FAIL、{history['historical_errors']} ERROR**，不覆盖为最终通过。包括测试夹具/断言错误、通用值验证错用于recipe、Replay家族误分派、cold preview缺失、SQLite lease竞争的安全停止、metadata初始化、撤权私有正文读取次序、页面family/preview/JSON分派；实际修复后才跑当前完整最终选集。旧日志、JUnit、SQLite、页面wire/结果、资格快照及失败证据都在本任务完整 archive；可重建缓存除外。

独审先前 S1–S6 是六项静态发现，**不计六个动态FAIL**；原 code-r1 报告和 manifest 原字节保留，最终 addendum 对应每项修复。最终独审本身0 FAIL。没有本轮工具授权拒绝、空间 escalation、未知临时清理或已拒浏览器重试。

## 未运行和后续条件

真实模型/费用/凭据、账户免费权益、人工语义验收、完整P-A/P-B、PG、Windows、原生浏览器、旧源码安装/通用DB升级、wheel构建、CI、部署及永久取消的旧安装/取消窗口均 **NOT_RUN / NOT_VERIFIED**。不称远端CI绿，不把独审有限工程结论当生产或语义验收。

[最小真实验收提案](PANaturalSpecRealAcceptanceProposal20261013.md) 已具体给出唯一 intern-s2/官方端点、两份中性材料类别、最多7请求/7168输出tokens/三个Run保守总额≤192000、原deadline/lease及合法 secret 入口。当前免费权益和凭据状态未核，精确 LIVE 批准与跨Run/零付费门尚未实现，**提案不可执行**；当前不请求凭据、不发真实请求、不收费。

## 可复核交付

[产品合同](PANaturalSpec20261012.md)；[证据入口](../evidence/pa-natural-spec-20261012/README.md)。核心文件为 natural_specs.py、natural_spec_runtime.py；复用 pa_spec_apps.py/goal_applications.py/Worker 的实际事务与账本，没有另写通用执行器。

main/core/CSV/compat/旧spec远端和原 owner HEAD/WIP 在推送前后复核；正常 push 只指定本开发分支，无 force。最终远端完整 SHA、clean/ahead/behind 和原owner两个草案 SHA 以交付外部回执及最终答复为准，避免把包含自身提交 SHA 的回执循环写入提交。
'''
(REPO / 'docs/F2/PANaturalSpecAcceptance20261013.md').write_text(report)

readme = f'''# P-A 未标注规范完整工程证据

冻结实际测试源码 `82717272e61c2fa174ad8772e54cd9e9eb947c49`，核心 `1b03567aa7f3f8d643c1026766186538be7e5370`。作者 {counts['PASS']} PASS/{counts['FAIL']} FAIL/{counts['ERROR']} ERROR/{counts['SKIP']} SKIP（228选中）；独审79唯一、79 PASS/0 FAIL/ERROR/SKIP，75与作者重叠，不能相加。

[完整验收说明](../../F2/PANaturalSpecAcceptance20261013.md)；[作者结果](author/final-results.json)；[作者JUnit](author/final.xml)；[独审报告](independent/final/FINAL_REVIEW.md)；[独审结果](independent/final/review-result.json)；[源图桥](author/author-independent-source-bridge.json)。两方完整434项源图前后及互比0差异，资格73文件精确pin保持。语义UNKNOWN、ownerPENDING，真实请求/费用0。

独审报告 SHA `{sha(ROOT.parent / 'independent/final/FINAL_REVIEW.md')}`；原最终独审 manifest SHA `{sha(ROOT.parent / 'independent/final/manifest.json')}`。原静态code-r1六发现与设计报告/manifest完整保留，最终结论 LIMITED PASS。19个作者历史XML中的14个原FAIL保留，不并入最终结果，也不改成PASS。

{archive_rows}

[作者全清单](author-full-manifest.json)、[独审全清单](independent-full-manifest.json)逐项记录文件大小/SHA、目录/链接类型和目标；[实际包内复核](archive-verification.json)从压缩包重新读出每个成员，全部一致。压缩包保留本任务SQLite、实际HTTP/JSDOM wire、原始失败与source snapshot；只排除可重建 __pycache__/pytest/cache目录。没有删除未知临时数据。直接可读副本从原证据逐字复制。

本验收为SQLite实际Worker、合成sender、进程内HTTP与JSDOM的有限工程结果；真实model/paid/credentials/semantics、PG/Windows/native/CI/deploy/完整P-A/P-B/完整旧升级均NOT_RUN或NOT_VERIFIED。完整提案在[真实验收提案](../../F2/PANaturalSpecRealAcceptanceProposal20261013.md)，零付费与LIVE门未具备，当前不可执行。
'''
(DEST / 'README.md').write_text(readme)
artifact = {}
for path in sorted(DEST.rglob('*')):
    if path.is_file() and path.name != 'artifact-manifest.json':
        artifact[str(path.relative_to(DEST))] = dict(bytes=path.stat().st_size, sha256=sha(path))
(DEST / 'artifact-manifest.json').write_text(json.dumps(artifact,sort_keys=True,indent=2)+'\n')
print(json.dumps(dict(report=str(REPO / 'docs/F2/PANaturalSpecAcceptance20261013.md'), artifact_entries=len(artifact),
                     artifact_manifest_sha256=sha(DEST / 'artifact-manifest.json')),indent=2))
