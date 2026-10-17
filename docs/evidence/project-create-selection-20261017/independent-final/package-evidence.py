import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path('/tmp/project-create-selection-independent-2acb62e5-20261017')
REPO = Path('/workspace/Sim2Act')
SOURCE = '2acb62e5bcc2c596bcb591d109433243691aeecb'


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
    objects[path] = dict(git_blob=git('rev-parse', SOURCE + ':' + path).decode().strip(),
        sha256=digest, bytes=len(data))
dump(BASE / 'source-git-objects.json', dict(source=SOURCE, files=objects))
root = ET.parse(BASE / 'junit.xml').getroot()
suites = list(root.iter('testsuite'))
cases = list(root.iter('testcase'))
failures = sum(int(s.get('failures', 0)) for s in suites)
errors = sum(int(s.get('errors', 0)) for s in suites)
skipped = sum(int(s.get('skipped', 0)) for s in suites)
proof = dict(source=SOURCE, requested_module='tests/test_project_create_selection.py',
    process_rc=int((BASE / 'pytest.exit-code').read_text().strip()),
    tests=len(cases), passed=sum(not any(c.find(k) is not None for k in ('failure', 'error', 'skipped')) for c in cases),
    failures=failures, errors=errors, skipped=skipped,
    seconds=sum(float(s.get('time', 0)) for s in suites),
    case_times={c.get('name'): float(c.get('time', 0)) for c in cases},
    executed_identities=[c.get('classname') + '::' + c.get('name') for c in cases],
    attempts_this_source=1, independent_repeat_of_same_three_author_cases=True, additional_unique_nodes=0,
    overall_review='PASS_WITHIN_EXECUTED_SCOPE' if not failures and not errors and not skipped else 'BLOCKED_OR_INCOMPLETE',
    source_file_count=len(objects), source_after=after,
    static_review=dict(remaining_blockers_in_modified_path=[],
        original_problem='The project-create receipt ID was discarded; loadProjects retained the previously selected A, causing the following explicit material Save to target A. The old create handler also allowed overlapping submissions.',
        implementation='The existing create API and policies remain unchanged. The frontend captures identity/connection/project-selection generation, synchronously claims a pending object and disables the button. It uses the returned project ID only while the user selection generation is unchanged, and otherwise reloads the same-identity project list while retaining the latest manual choice.',
        list_and_identity_fences='List generation suppresses older list success; identity and connection guard the create callback. Only the same pending object may clear its busy state in finally, so a stale identity callback cannot reset a new attempt.',
        event_contract='Actual dispatchEvent(change) runs existing resource preview/download, registered recovery, natural-project and context listeners. The existing onchange stores its refresh Promise synchronously; loadProjects awaits that Promise. Programmatic adoption uses the same clearing/refresh behavior as manual choice.',
        draft_coverage_gap_closed='The initial draft retained original rows without ruling out additions in A. The frozen verification additionally compares every project_id=A scope exactly and restricts new project/runtime/grant/resource rows to B.',
        baseline_boundary='Parent reported actual baseline failure with returned B/current A, a real FileReader resource POST persisted under A, and duplicate project POSTs. This reviewer did not rerun that baseline or reverify its original files.',
        related_boundary='Parent separately reported a background_poll failure and the same direct-driver failure on17b baseline; it remains not passed. This reviewer did not execute, reverify originals or count that batch.'),
    scenarios={})
provenance = {}
for p in sorted((BASE / 'data').glob('*/result.json')):
    if p.parent.is_symlink():
        continue
    raw = json.loads(p.read_text())
    info = json.loads((p.parent / 'info.json').read_text())
    dbpath = p.parent / 'database-proof.json'
    database = json.loads(dbpath.read_text()) if dbpath.exists() else dict(status='NOT_PRODUCED; post-driver verification incomplete')
    requests = raw.get('requests', [])
    observations = raw.get('observations', [])
    saved = [r for r in requests if r['method'] == 'POST' and r['path'].endswith('/resources')]
    case = raw['case']
    proof['scenarios'][case] = dict(status=raw['status'], error=raw.get('error'),
        checks=len(raw.get('checks', [])), check_labels=raw.get('checks', []),
        product_api_requests=len(requests), gets=sum(r['method'] == 'GET' for r in requests),
        posts=sum(r['method'] == 'POST' for r in requests), static_http_responses=len(raw.get('assets', [])),
        observations=observations, actual_material_save_requests=saved,
        database=database, real_model_calls=raw.get('real_model_calls'), worker_calls=raw.get('worker_calls'),
        info=str((p.parent / 'info.json').relative_to(BASE)), result=str(p.relative_to(BASE)))
    if raw['status'] == 'PASS':
        assert database['tables'] == 48 and all(v['project_a_scope_exactly_unchanged'] for v in database['proof'])
        created = next(o for o in observations if o['kind'] == 'after_create')
        if case == 'create-save':
            assert created['current'] == created['created']
            assert len(saved) == 1 and saved[0]['path'] == '/api/projects/' + created['created'] + '/resources'
            assert saved[0]['body']['content'] == 'city,amount\r\n杭州,9.25\r\n'
            pending = next(o for o in observations if o['kind'] == 'pending_duplicate')
            assert pending['post_count'] == 1 and pending['disabled']
        elif case == 'late-manual':
            assert created['current'] == info['project']
            assert any(v['id'] == created['created'] for v in created['options'])
        else:
            assert created['current'] == info['foreign']
            assert all(v['id'] != created['created'] for v in created['options'])
    for asset in raw.get('assets', []):
        name = 'src/sim2act/web/' + (asset['path'].lstrip('/') or 'index.html')
        data = git('show', SOURCE + ':' + name)
        assert sha(data) == asset['sha256']
        out = BASE / 'statics' / name.removeprefix('src/sim2act/web/')
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        value = dict(http_path=asset['path'], sha256=asset['sha256'], copied_file=str(out.relative_to(BASE)))
        assert name not in provenance or provenance[name] == value
        provenance[name] = value
dump(BASE / 'static-source-provenance.json', dict(source=SOURCE,
    provenance='Frozen Git source copies matched recorded actual served HTTP-response SHA256. They are not raw transport-body captures or new requests.', files=provenance))
proof['not_executed'] = ['independent baseline rerun', 'background_poll or other related nodes', 'PG',
    'native browser/Windows or native OS file-picker UI', 'real models/semantic scenarios', 'remote CI/Actions',
    'unknown project-create acceptance recovery', 'download/old private or failure matrices']
excluded = {'package-evidence.py', 'independent-review.md', 'independent-proof.json', 'raw-manifest.json', 'raw-SHA256SUMS'}
manifest = {}
for path in sorted(BASE.rglob('*')):
    if not path.is_file() or path.is_symlink() or any(q.is_symlink() for q in path.parents if q != BASE):
        continue
    name = str(path.relative_to(BASE))
    if name in excluded:
        continue
    data = path.read_bytes()
    manifest[name] = dict(sha256=sha(data), bytes=len(data))
dump(BASE / 'raw-manifest.json', manifest)
(BASE / 'raw-SHA256SUMS').write_text(''.join(v['sha256'] + '  ' + k + '\n' for k, v in manifest.items()))
proof.update(static_copies=len(provenance), raw_manifest_count=len(manifest),
    raw_manifest_sha256=sha((BASE / 'raw-manifest.json').read_bytes()),
    raw_sums_sha256=sha((BASE / 'raw-SHA256SUMS').read_bytes()))
dump(BASE / 'independent-proof.json', proof)
table = ['| Case | Checks | Product API HTTP / POST | Static responses |', '|---|---:|---:|---:|']
for name in ['create-save', 'late-manual', 'late-identity']:
    if name in proof['scenarios']:
        v = proof['scenarios'][name]
        table.append(f"| {name} | {v['checks']} | {v['product_api_requests']} / {v['posts']} | {v['static_http_responses']} |")
review = f"""冻结源 `{SOURCE}` 独立同3参数一次：{proof['passed']} PASS / {failures} FAIL / {errors} ERROR / {skipped} SKIP，JUnit {proof['seconds']:.3f}s，RC{proof['process_rc']}。无重试或额外节点；重复作者用例，unique+0。静态审查在本修改范围无新阻断：真实change及等待保留现有listeners，项目ABA/连接/列表代次隔离，旧回调只释放自身pending。

""" + '\n'.join(table) + f"""

真实ASGI + 全served JS/JSDOM + 合成SQLite。create-save通过注入合成File、真实JSDOM FileReader解码和显式Save，确认返回B==当前B，资源POST/SQL均归B且UTF8/CRLF不变；pending的disabled click和submit仅1次创建。late-manual在POST及列表GET两阶段other→A，B可发现且不劫持；late-identity保持第二真实合成身份的项目/列表。原始result保留实际ID、options和响应；未记录单独门耗时，不声称该数据。

48表原行全保留，A作用域精确相等；新增project/runtime/grants及唯一保存资源仅归B，沿用服务器原授权政策。Worker/model均0，无Run/Release/approval POST。{len(objects)}文件前后匹配冻结Git，完整src无差异。{len(manifest)}份原件见manifest/sums；21静态拷贝明确为Git源、匹配实际served响应SHA，非传输原件。

基线未独立复跑。父另批background在17b基线亦失败、未计通过，本审未执行/复核其原件。PG/native/Windows/原生文件选择器、模型/真实语义、CI、unknown创建回执恢复及其他矩阵均NOT_RUN。仓库只读。
"""
(BASE / 'independent-review.md').write_text(review)
print(json.dumps(dict(tests=proof['tests'], passed=proof['passed'], failures=failures, errors=errors, skipped=skipped,
    seconds=proof['seconds'], raw_files=len(manifest), scenarios={k:dict(checks=v['checks'],http=v['product_api_requests'],posts=v['posts']) for k,v in proof['scenarios'].items()}),indent=2))
