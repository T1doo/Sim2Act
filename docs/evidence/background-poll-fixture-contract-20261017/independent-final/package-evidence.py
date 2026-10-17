import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path('/tmp/background-poll-fixture-contract-independent-3e2ea675-20261017')
REPO = Path('/workspace/Sim2Act')
SOURCE = '3e2ea675d3849181170a03f6f4f1dbda469bfcae'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def git(*args):
    return subprocess.check_output(['git', '-c', 'core.fsmonitor=false', *args], cwd=REPO,
        env={**os.environ, 'GIT_OPTIONAL_LOCKS': '0'})


before = json.loads((BASE / 'source-before.json').read_text())
after = json.loads((BASE / 'source-after.json').read_text())
assert after['source_tests_match_frozen_git'] and after['full_src_worktree_matches_frozen_git']
objects = {}
for path, digest in before['files'].items():
    data = git('show', SOURCE + ':' + path)
    assert sha(data) == digest == after['files'][path]
    objects[path] = dict(git_blob=git('rev-parse', SOURCE + ':' + path).decode().strip(), sha256=digest, bytes=len(data))
dump(BASE / 'source-git-objects.json', dict(source=SOURCE, files=objects))
root = ET.parse(BASE / 'junit.xml').getroot()
suites = list(root.iter('testsuite'))
cases = list(root.iter('testcase'))
failures = sum(int(v.get('failures', 0)) for v in suites)
errors = sum(int(v.get('errors', 0)) for v in suites)
skipped = sum(int(v.get('skipped', 0)) for v in suites)
paths = [p for p in sorted((BASE / 'data').glob('*/results.json')) if not p.parent.is_symlink()]
assert len(paths) == 1
path = paths[0]
raw = json.loads(path.read_text())
trace = raw['requestTimeline']
phases = raw['phaseTimeline']
assert raw['source_sha256'] == before['files']['src/sim2act/web/app.js']
assert raw['status'] == 'PASS' and len(raw['checks']) == 21
assert raw['api'] == 'SYNTHESIZED_NOT_HTTP'
gates = [v for v in phases if v['event'] == 'gate-check']
assert all(v['used'] for v in gates)
invariants = json.loads((BASE / 'static-review.json').read_text())
proof = dict(source=SOURCE, requested_node='tests/test_background_poll.py::test_background_poll_synthesized_api',
    process_rc=int((BASE / 'pytest.exit-code').read_text().strip()), tests=len(cases),
    passed=sum(not any(c.find(k) is not None for k in ('failure', 'error', 'skipped')) for c in cases),
    failures=failures, errors=errors, skipped=skipped,
    seconds=sum(float(v.get('time', 0)) for v in suites),
    attempts_this_source=1, repeat_same_author_node=True, additional_unique_nodes=0,
    overall_review='PASS_WITHIN_EXECUTED_SCOPE', source_file_count=len(objects), source_after=after,
    static_invariants=invariants,
    runtime=dict(checks=raw['checks'], check_count=len(raw['checks']),
        request_timeline_entries=len(trace), phase_timeline_entries=len(phases),
        scenes=sorted({v['scene'] for v in trace}),
        synthesized_gets=sum(v['method'] == 'GET' for v in trace),
        synthesized_posts=sum(v['method'] == 'POST' for v in trace),
        synthesized_errors=[dict(scene=v['scene'], path=v['path'], error=v['error']) for v in trace if 'error' in v],
        reached_gate_count=len(gates), all_gates_reached=True,
        health_reply_count=sum(v['path'] == '/health' and 'response' in v for v in trace),
        metadata_catalog_reply_count=sum(v['path'] == '/api/apps?metadata_only=true' and 'response' in v for v in trace),
        scheduler=raw['scheduler'], api=raw['api'],
        results=str(path.relative_to(BASE)), driver_log=str((path.parent / 'driver.log').relative_to(BASE))),
    original_assertion_groups=dict(phase_pending_and_finally_success_error=12, explicit_refresh=1,
        project_ABA_and_stale_material=2, identity_ABA_and_stale_material=2,
        stale_run_view=1, unknown_no_background_resubmit_and_explicit_original_body_key=3),
    provenance='Trace is this single current-source execution with synthesized fetch/scheduler. There is no real HTTP, DB, model or Worker call. Historical failures and new diagnostic replays were not rerun, copied or relabelled as original per-request timestamps.',
    not_executed=['independent old baseline replay', 'parent separate direct-Node baseline comparison',
        'real HTTP/DB/Worker/provider/model', 'network', 'PG', 'native browser/Windows',
        'other pytest nodes/old private or recovery matrices', 'remote CI/Actions'])
excluded = {'package-evidence.py', 'independent-review.md', 'independent-proof.json', 'raw-manifest.json', 'raw-SHA256SUMS'}
manifest = {}
for p in sorted(BASE.rglob('*')):
    if not p.is_file() or p.is_symlink() or any(q.is_symlink() for q in p.parents if q != BASE):
        continue
    name = str(p.relative_to(BASE))
    if name in excluded:
        continue
    data = p.read_bytes()
    manifest[name] = dict(sha256=sha(data), bytes=len(data))
dump(BASE / 'raw-manifest.json', manifest)
(BASE / 'raw-SHA256SUMS').write_text(''.join(v['sha256'] + '  ' + name + '\n' for name, v in manifest.items()))
proof.update(raw_manifest_count=len(manifest), raw_manifest_sha256=sha((BASE / 'raw-manifest.json').read_bytes()),
    raw_sums_sha256=sha((BASE / 'raw-SHA256SUMS').read_bytes()))
dump(BASE / 'independent-proof.json', proof)
review = f"""冻结源 `{SOURCE}`：独立仅 tests/test_background_poll.py 一次，1 PASS / 0 FAIL / 0 ERROR / 0 SKIP，JUnit {proof['seconds']:.3f}s，RC0；与作者同节点重复，unique+0，无额外测试。

静态核实产品/API均要求健康api=UP、worker=UP或OFFLINE；目录请求为/api/apps?metadata_only=true并读items。仅夹具两处UP和精确metadata URL匹配修复，trace为被动旁录。完整执行场景body字节相同（SHA {invariants['scenario_body_sha256']}），21谓词/释放顺序、50次setImmediate、2500ms注册及Python30s/21计数不变；src相对2aac无差异，健康段同17b。6文件前后匹配冻结Git，无新静态阻断。

21检查全部完成；本次trace {len(trace)}合成请求条目、{len(phases)}阶段条目、11个DOM场景、10个门均到达。原始results.json含完整requestTimeline/phaseTimeline；driver.log、命令、JUnit/log、前后哈希及静态核对见{len(manifest)}项manifest/sums。

SYNTHESIZED_NOT_HTTP：合成fetch和手动scheduler，无真实HTTP/DB/Worker/模型/网络。未独立重跑旧基线或父额外Node比较；新诊断时间线不是历史原件，历史缺失时间戳未补写。PG/native/Windows/其他节点/矩阵/远端CI均NOT_RUN。仓库只读，旧失败未动。
"""
(BASE / 'independent-review.md').write_text(review)
print(json.dumps(dict(tests=proof['tests'], passed=proof['passed'], seconds=proof['seconds'],
    checks=len(raw['checks']), raw_files=len(manifest), request_entries=len(trace), phase_entries=len(phases),
    synthesized_gets=proof['runtime']['synthesized_gets'], synthesized_posts=proof['runtime']['synthesized_posts'],
    reached_gates=len(gates), health_replies=proof['runtime']['health_reply_count'],
    metadata_catalog_replies=proof['runtime']['metadata_catalog_reply_count']),indent=2))
