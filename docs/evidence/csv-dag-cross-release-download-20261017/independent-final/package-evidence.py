import hashlib
import json
import os
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path('/tmp/csv-dag-cross-release-download-independent-a865971e-20261017')
REPO = Path('/workspace/Sim2Act')
SOURCE = 'a865971e73e4ce20cffec61e3bce5b71f5b0504c'
NODE = 'tests/test_csv_dag_cross_release_download.py::test_visible_compatible_adoption_cold_old_new_downloads_and_revoke'


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
proof = dict(source=SOURCE, requested_node=NODE,
    process_rc=int((BASE / 'pytest.exit-code').read_text().strip()),
    tests=len(cases), passed=sum(not any(c.find(k) is not None for k in ('failure', 'error', 'skipped')) for c in cases),
    failures=failures, errors=errors, skipped=skipped,
    seconds=sum(float(s.get('time', 0)) for s in suites),
    case_times={c.get('name'): float(c.get('time', 0)) for c in cases},
    executed_identities=[c.get('classname') + '::' + c.get('name') for c in cases],
    attempts_this_source=1, independent_repeat_of_same_author_node=True, additional_unique_nodes=0,
    overall_review='PASS_WITHIN_EXECUTED_SCOPE' if not failures and not errors and not skipped else 'BLOCKED_OR_INCOMPLETE',
    source_file_count=len(objects), source_after=after,
    static_review=dict(
        remaining_blockers=[],
        original_finding='dagReuseRead updated r.release after full verification without synchronizing the visible Release selector.',
        author_baseline='Author reported f1c69f557b9f71bf3bf08b0791efe0fff17904e3 with product src identical to9ac: one actual baseline failure at initial visible Release assertion, 28 GET/0 product POST, adoption not reached. Not independently rerun. Original baseline did not record actual selected ID; no such ID is inferred.',
        frozen_fix='One product line sets #dag-reuse-release.value=rel.id immediately after verified r.release assignment and current check. It does not dispatch onchange, create an intent or change version/authorization semantics.',
        own_release_contract='Each run is sealed with its own historical Release and revision, and each download closure retains that Release; the expected Blob content uses the two independently prepared fixture Releases.',
        real_adoption='Visible target selection, prepare POST, approval GET/readback, separate manual confirmation and commit POST use the existing controller. No DB writes are used to simulate adoption.',
        revocation_boundary='Old Run is denied through visible download403; new detached callback is checked to issue no request/Blob, then the new Run gets a separately labelled direct existing API403 after view clearing. These are distinct entry paths.',
    ))
results = [p for p in sorted((BASE / 'data').glob('*/result.json')) if not p.parent.is_symlink()]
provenance = {}
assert len(results) == 1, results
p = results[0]
raw = json.loads(p.read_text())
info = json.loads((p.parent / 'info.json').read_text())
fixture = json.loads((p.parent / 'fixture-proof.json').read_text())
dbpath = p.parent / 'database-proof.json'
database = json.loads(dbpath.read_text()) if dbpath.exists() else dict(status='NOT_PRODUCED; post-driver assertions incomplete')
requests = raw.get('requests', [])
captured = {}
for saved in raw.get('saved_files', []):
    path = p.parent / saved['filename']
    data = path.read_bytes()
    assert len(data) == saved['bytes'] and sha(data) == saved['sha256']
    value = json.loads(data)
    assert data == (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
    assert value['run_id'] == saved['run_id'] and value['release_id'] == saved['release_id']
    assert value['result_version'] == saved['version'] and value['instance_revision'] == saved['revision']
    captured[str(path.relative_to(BASE))] = {**saved, 'node_output_ids': list(value['node_outputs'])}
proof['execution'] = dict(driver_status=raw['status'], driver_error=raw.get('error'),
    checks=len(raw.get('checks', [])), check_labels=raw.get('checks', []),
    product_http_requests=len(requests), product_gets=sum(r['method'] == 'GET' for r in requests),
    product_posts=sum(r['method'] == 'POST' for r in requests),
    post_identities=[dict(path=r['path'], body=r.get('body'), status=r.get('status')) for r in requests if r['method'] == 'POST'],
    static_http_responses=len(raw.get('assets', [])), boots=raw.get('boots'),
    database=database, fixture_source_worker_runs=len(fixture['source_worker_run_ids']),
    actual_source_run_ids=fixture['source_worker_run_ids'],
    old_source=info['old']['snapshot']['execution_source'], target_source=info['target']['snapshot']['execution_source'],
    same_material_source_hash=info['old']['snapshot']['execution_source']['source_hash'] == info['target']['snapshot']['execution_source']['source_hash'],
    visible_releases=raw.get('visible_releases', []),
    forbidden_after_revoke=raw.get('forbidden_after_revoke', []),
    actual_http403=[dict(path=r['path'], method=r['method'], status=r['status'], response=r['response']) for r in requests if r.get('status') == 403],
    heldWaits=raw.get('heldWaits', []), synthetic_response_mutations=raw.get('mutations', []),
    blob_metadata=raw.get('download_blobs', []), anchors=raw.get('download_anchors', []),
    captured_blob_files=captured, scope=raw.get('scope'),
    raw_result=str(p.relative_to(BASE)), raw_info=str((p.parent / 'info.json').relative_to(BASE)))
if raw['status'] == 'PASS':
    assert len(captured) == len(raw['download_blobs']) == len(raw['download_anchors']) == 5
    assert all(v['revoked'] for v in raw['download_blobs'])
    assert len(raw['visible_releases']) == 3 and all(v['selected'] == v['selected_option'] == v['expected'] for v in raw['visible_releases'])
    assert len(proof['execution']['actual_http403']) == 2
    assert len(raw['heldWaits']) == 1 and raw['heldWaits'][0]['outcome'] == 'exact gate reached'
    assert not raw['mutations']
    old_files = [BASE / path for path, v in captured.items() if v['version'] == 1]
    new_files = [BASE / path for path, v in captured.items() if v['version'] == 2]
    assert len(old_files) == 3 and len(new_files) == 2
    assert len({sha(f.read_bytes()) for f in old_files}) == len({sha(f.read_bytes()) for f in new_files}) == 1
    proof['execution']['old_blob_bytes_identical_before_and_after_adoption'] = True
    proof['execution']['new_blob_bytes_identical_across_history_selection'] = True
for asset in raw.get('assets', []):
    name = 'src/sim2act/web/' + (asset['path'].lstrip('/') or 'index.html')
    data = git('show', SOURCE + ':' + name)
    assert sha(data) == asset['sha256']
    out = BASE / 'statics' / name.removeprefix('src/sim2act/web/')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)
    item = dict(http_path=asset['path'], sha256=asset['sha256'], copied_file=str(out.relative_to(BASE)))
    assert name not in provenance or provenance[name] == item
    provenance[name] = item
dump(BASE / 'static-source-provenance.json', dict(source=SOURCE,
    provenance='Frozen Git copies matched recorded actual served HTTP-response SHA256. These are source copies, not raw transport body captures or new requests.', files=provenance))
proof['not_executed'] = ['independent baseline rerun', 'other download families/nodes', 'rollback/old private or recovery matrices',
    'PG', 'native browser/Windows', 'real models', 'real semantic scenarios', 'remote CI/Actions', 'project-creation follow-up']
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
e = proof['execution']
review = f"""Frozen source `{SOURCE}`: independent exact single-node repeat {proof['passed']} PASS, {failures} FAIL, {errors} ERROR, {skipped} SKIP; JUnit {proof['seconds']:.3f}s, process RC {proof['process_rc']}. One attempt of `{NODE}`, no retry/additional nodes. Repeating the author's same node adds zero unique tests.

The frozen one-line product fix synchronizes the visible Release selector only after successful full instance/history verification and the current-selection check. It does not dispatch onchange or change authorization, durable intent, version adoption or execution semantics. Static review found no remaining blocker. The author's baseline failure is retained separately by root; this reviewer did not rerun baseline or infer its unrecorded selected ID.

Actual ASGI HTTP and full served JS in JSDOM use the original controller with synthetic SQLite and NoModel Workers. The fixture creates two real successful source Runs and two immutable report Releases using the existing release/next_release APIs. The page explicitly runs old amount30 at revision1/resultv1, selects the exact compatible target, prepares/reads approval, separately confirms and commits adoption, then explicitly runs new quantity15 at revision2/resultv2. Adoption preserves old records and grants; Python checkpoints compare all48 table snapshots, allowing prepare to change only internal_approvals and commit only internal_approvals/internal_instances. No direct DB mutation adopts a version.

Executed driver: {e['checks']} checks, {e['product_http_requests']} product API HTTP ({e['product_gets']} GET/{e['product_posts']} POST), {e['static_http_responses']} served static responses, {e['boots']} full page boots. The four product POSTs are exactly two explicit Runs plus one switch prepare and one commit; downloads add zero POST. Fixture source Workers2, directory cold Workers2; actual counts/checkpoints/authority proof are retained in database-proof.json. Three visible Release observations record selected IDs and option labels before/after adoption and after cold reopening.

Five exact Blob.text() UTF-8 JSON payloads, MIME, filenames, full own-Run/typed AppRun/instance/revision/Release/result/source/plan and aggregate/report outputs are checked. The old file is byte-identical before adoption and after cold reopening; the new version uses its distinct immutable source Run and plan fingerprint. The material source hash remains the same because these compatible Releases use the same fixed CSV. One held old-Run response is invalidated by selecting the new result's download button, followed by an explicit correct old-result download. This is a download-button choice, not a separate row selection handler.

One real Grant revoke occurs. The visible old-result download receives actual403 and clears all protected results. The captured new-result detached callback then creates no request or Blob. A separate, explicitly labelled direct existing API GET for the new Run also returns actual403 after the view is cleared; this is not a second visible button click. Both actual403 bodies and entry paths are retained. All five Blob URLs are revoked and download keys cleared. The one held gate has original timing/reply offsets; no synthetic response rewrite is used.

All {len(objects)} selected product/backend/test/helper files match frozen Git bytes before/after, and full src worktree matches the frozen tree. Original DB/fixture/info/driver result/stderr/Blob files, command, JUnit/log and source hashes are indexed by raw-manifest.json ({len(manifest)} files) and raw-SHA256SUMS. Frozen static copies explicitly state their Git/recorded-response-hash provenance.

JSDOM anchor capture is an adapter, not native download acceptance. PG, native browser/Windows, real models/semantic scenarios, rollback, other families/nodes, old private/recovery matrices, remote CI/Actions and the separate project-creation task are NOT_RUN. This reviewer changes no repository source.
"""
(BASE / 'independent-review.md').write_text(review)
print(json.dumps(dict(tests=proof['tests'], passed=proof['passed'], failures=failures, errors=errors, skipped=skipped,
    seconds=proof['seconds'], raw_files=len(manifest), checks=e['checks'], api_http=e['product_http_requests'],
    posts=e['product_posts'], blobs=len(e['blob_metadata']), captures=len(captured),
    database=e['database']), ensure_ascii=False, indent=2))
