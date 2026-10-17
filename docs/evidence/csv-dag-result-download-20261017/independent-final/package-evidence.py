import hashlib
import json
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

BASE = Path('/tmp/csv-dag-result-download-independent-3be0300b-20261017')
REPO = Path('/workspace/Sim2Act')
SOURCE = '3be0300b306fac0cb6f5d9e0a1521ca16814c126'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def git(*args):
    return subprocess.check_output(['git', *args], cwd=REPO)


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


before = json.loads((BASE / 'source-before.json').read_text())
after = json.loads((BASE / 'source-after.json').read_text())
assert after['source_tests_match_frozen_git']
objects = {}
for name, digest in before['files'].items():
    frozen = git('show', SOURCE + ':' + name)
    assert sha(frozen) == digest == after['files'][name]
    objects[name] = dict(git_blob=git('rev-parse', SOURCE + ':' + name).decode().strip(),
                         sha256=digest, bytes=len(frozen))
dump(BASE / 'source-git-objects.json', dict(source=SOURCE, files=objects))

root = ET.parse(BASE / 'junit.xml').getroot()
suites = list(root.iter('testsuite'))
cases = list(root.iter('testcase'))
failures = sum(int(v.get('failures', 0)) for v in suites)
errors = sum(int(v.get('errors', 0)) for v in suites)
skipped = sum(int(v.get('skipped', 0)) for v in suites)
proof = dict(
    source=SOURCE,
    rc=int((BASE / 'pytest.exit-code').read_text().strip()),
    tests=len(cases),
    passed=sum(not any(c.find(k) is not None for k in ('failure', 'error', 'skipped')) for c in cases),
    failures=failures, errors=errors, skipped=skipped,
    seconds=sum(float(s.get('time', 0)) for s in suites),
    case_times={c.get('name'): float(c.get('time', 0)) for c in cases},
    identities=[c.get('classname') + '::' + c.get('name') for c in cases],
    new_download_nodes=['download-dual', 'download-report', 'download-use', 'download-fixed'],
    repeat_same_author_nodes=True, additional_unique_nodes=0, attempts_this_source=1,
    overall_review='PASS_WITHIN_EXECUTED_SCOPE' if not failures and not errors and not skipped else 'BLOCKED_OR_INCOMPLETE',
    source_file_count=len(objects), source_after=after,
    static_findings=[dict(stage='initial uncommitted implementation; no dynamic attempt',
        finding='Result controls appended to summary p would invalidate pre-existing exact visible-row comparison.',
        resolution='Frozen code has a visible data-role=dag-result-summary span; assertions retain exact full sid/column/count/sum comparison in that span.',
        status='CLOSED_BEFORE_FROZEN_SOURCE')],
    static_conclusions=[
        'Fresh generic instance/actual-Run GET precedes each successful download; the extracted full history seal is reused.',
        'Run actual ID, typed AppRun ID, instance, result version, record fingerprint, revision/history, own Release, source and derived plan are bound.',
        'Export whitelist includes typed result, controlled output and complete verified aggregate/report step data, excluding the read node/raw CSV.',
        'Each historical record uses its own Run Release; cross-Release switch/history is statically inspected only.',
        'Another historical result download button advances download generation; there is no independent row selection handler.',
        'Selection/connection/workspace/read/download generations suppress stale success/error. Set deduplication is checked before advancing generation.',
        '403 on current download clears protected DAG view; no new executor, Grant or endpoint is introduced.',
    ],
    scenarios={},
)
provenance = {}
for p in sorted((BASE / 'data').glob('*/result.json')):
    if p.parent.is_symlink():
        continue
    raw = json.loads(p.read_text())
    info = json.loads((p.parent / 'info.json').read_text())
    fixture = json.loads((p.parent / 'fixture-proof.json').read_text())
    db_file = p.parent / 'database-proof.json'
    db = json.loads(db_file.read_text()) if db_file.exists() else dict(status='NOT_PRODUCED; driver or post-driver assertions did not finish')
    requests = raw.get('requests', [])
    captures = {}
    for capture in sorted(p.parent.glob('download-blob-*.json')):
        data = capture.read_bytes()
        value = json.loads(data)
        assert data == (json.dumps(value, ensure_ascii=False, indent=2) + '\n').encode()
        captures[str(capture.relative_to(BASE))] = dict(sha256=sha(data), bytes=len(data),
            actual_run_id=value['run_id'], typed_app_run_id=value['app_run_id'],
            result_version=value['result_version'], node_output_ids=list(value['node_outputs']))
    sid = 'download-' + info['scenario']
    exact_prefix = '/api/internal/instances/' + info['instance'] + '/runs/'
    proof['scenarios'][sid] = dict(status=raw['status'], error=raw.get('error'),
        checks=len(raw.get('checks', [])), check_labels=raw.get('checks', []),
        product_http_requests=len(requests), product_posts=sum(r.get('method') == 'POST' for r in requests),
        generic_selected_run_gets=[dict(path=r['path'], status=r.get('status')) for r in requests
            if r.get('method') == 'GET' and r.get('path', '').startswith(exact_prefix)],
        fixture_source_worker_runs=len(fixture['source_worker_run_ids']), database=db,
        info=str((p.parent / 'info.json').relative_to(BASE)), result=str(p.relative_to(BASE)),
        mutations=raw.get('mutations', []), heldWaits=raw.get('heldWaits', []),
        blob_metadata=raw.get('download_blobs', []), anchors=raw.get('download_anchors', []),
        captured_blob_files=captures, boots=raw.get('boots'),
        capture_provenance='Exact Blob.text() UTF-8 payload written by the executed driver after successful anchor capture. Anchor-exception Blob has metadata and cleanup assertions but no raw Blob.text file; not reconstructed.',
        scope=raw.get('scope'))
    for asset in raw.get('assets', []):
        name = 'src/sim2act/web/' + (asset['path'].lstrip('/') or 'index.html')
        data = git('show', SOURCE + ':' + name)
        assert sha(data) == asset['sha256'], name
        out = BASE / 'statics' / name.removeprefix('src/sim2act/web/')
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        value = dict(http_path=asset['path'], sha256=asset['sha256'], copied_file=str(out.relative_to(BASE)))
        assert name not in provenance or provenance[name] == value
        provenance[name] = value

proof['worker_counts'] = dict(
    fixture_source_worker_runs=sum(v['fixture_source_worker_runs'] for v in proof['scenarios'].values()),
    cold_worker_runs_from_directory=sum(v['database'].get('cold_worker_runs_from_directory', 0) for v in proof['scenarios'].values()),
    controlled_real_revocations=sum(v['database'].get('controlled_revocations', 0) for v in proof['scenarios'].values()),
)
proof['not_executed'] = ['cross-Release historical download dynamically', 'old guards/finite/private/recovery matrices',
    'other related pytest nodes', 'PG', 'native browser/Windows', 'real semantics/scenarios', 'real models', 'remote CI/Actions']
proof['mutation_boundary'] = 'Recorded requests retain actual ASGI response bodies/status. Mutations are explicitly synthetic responses after actual HTTP, except the separately recorded real Grant revocation command and resulting actual403.'
dump(BASE / 'static-source-provenance.json', dict(source=SOURCE,
    provenance='Frozen Git source copies matched recorded actual served HTTP-response SHA256; copies are not raw transport bodies or new requests.', files=provenance))
excluded = {'package-evidence.py', 'independent-review.md', 'independent-proof.json', 'raw-manifest.json', 'raw-SHA256SUMS'}
manifest = {}
for p in sorted(BASE.rglob('*')):
    if not p.is_file() or p.is_symlink() or any(parent.is_symlink() for parent in p.parents if parent != BASE):
        continue
    rel = str(p.relative_to(BASE))
    if rel in excluded:
        continue
    data = p.read_bytes()
    manifest[rel] = dict(sha256=sha(data), bytes=len(data))
dump(BASE / 'raw-manifest.json', manifest)
(BASE / 'raw-SHA256SUMS').write_text(''.join(v['sha256'] + '  ' + k + '\n' for k, v in manifest.items()))
proof.update(static_copies=len(provenance), raw_manifest_count=len(manifest),
    raw_manifest_sha256=sha((BASE / 'raw-manifest.json').read_bytes()),
    raw_sums_sha256=sha((BASE / 'raw-SHA256SUMS').read_bytes()))
dump(BASE / 'independent-proof.json', proof)
table = ['| Node | Checks | Product HTTP / POST | Source / cold Worker | Read checkpoints / real revoke | Blob / anchor / captured payload |',
         '|---|---:|---:|---:|---:|---:|']
for name in proof['new_download_nodes']:
    v = proof['scenarios'].get(name)
    if not v:
        continue
    d = v['database']
    table.append(f"| {name} | {v['checks']} | {v['product_http_requests']} / {v['product_posts']} | "
        f"{v['fixture_source_worker_runs']} / {d.get('cold_worker_runs_from_directory', 'incomplete')} | "
        f"{d.get('read_checkpoints', 'incomplete')} / {d.get('controlled_revocations', 'incomplete')} | "
        f"{len(v['blob_metadata'])} / {len(v['anchors'])} / {len(v['captured_blob_files'])} |")
review = f"""Frozen source `{SOURCE}`: independent exact-repeat batch {proof['passed']} PASS, {failures} FAIL, {errors} ERROR, {skipped} SKIP; JUnit {proof['seconds']:.3f}s, process RC {proof['rc']}. Four download nodes are all new in this slice; this independent repetition adds zero unique nodes. One attempt, no rerun or additional matrix.

Static review found no remaining blocker in the frozen implementation. The fresh no-store generic instance/actual-Run GET reauthorizes the request; the shared full seal binds instance, actual Run, typed AppRun, own historical Release/revision, source/derived plan, record fingerprint and result version. The whitelist exports complete controlled aggregate/report data and the original controlled output shape, preserving decimal strings and UNKNOWN/PENDING/unpublished flags. It omits the read-node/raw CSV and authorization data. The initial uncommitted summary/controls assertion mismatch was caught statically and fixed before freeze; no dynamic red was executed for it.

""" + '\n'.join(table) + f"""

The executed page is full served JS in JSDOM with actual ASGI HTTP and synthetic SQLite, using the original controller. Each node includes two explicit directory Run submissions, two cold NoModel Workers, persisted v1/v2 and cold-page readback. Product POST counts in the table are those two normal Run submissions per node; download operations add zero POST. The one real Grant revocation is a separate fixture IPC command and is recorded by the database proof and actual subsequent HTTP403, not hidden in that product POST count.

Dual completes six held-response gates and workspace/project/instance/identity ABA checks, synthetic bound-result rejection, another historical result download button invalidating the older response, stale403 isolation, duplicate clicks, anchor exception cleanup and current real403 clearing. There is no independent row selection handler. Ordinary and fixed report mutations remove the bound report text and are rejected before a Blob. Synthetic mutations retain the actual ASGI response/status separately in result.json. No scenario is classified as exceptional recovery.

The driver preserves actual Blob.text() JSON files for successful anchors and checks exact formatting, MIME, filename and full content binding. Dual's deliberately failing anchor still produces and revokes a Blob URL but has no Blob.text() file; only its metadata/cleanup assertions are retained, without reconstruction. All created URLs are revoked and links removed. JSDOM anchor capture is an adapter, not native browser download acceptance.

All {len(objects)} selected product/backend/driver/fixture files match frozen Git bytes before/after; Git blob IDs and SHA256 are in source-git-objects.json. Complete originals and source/static provenance are indexed by raw-manifest.json ({len(manifest)} files) and raw-SHA256SUMS. Static copies match observed served response hashes and are explicitly not transport captures. The dual fixture intentionally does not perform an authorized final instance GET after real revocation; final SQL row assertions and the read-only checkpoints still complete.

Cross-Release historical download is statically reviewed only; these four fixtures do not switch Release. PG, native browser/Windows, real semantic scenarios, real models, remote CI/Actions, other pytest nodes and old private/recovery matrices are NOT_RUN. No repository writes or new permissions/executor/Grant/endpoint were performed by this reviewer.
"""
(BASE / 'independent-review.md').write_text(review)
print(json.dumps(dict(tests=proof['tests'], passed=proof['passed'], failures=failures, errors=errors,
    skipped=skipped, seconds=proof['seconds'], raw_files=len(manifest), workers=proof['worker_counts'],
    scenarios={k: dict(checks=v['checks'], requests=v['product_http_requests'], posts=v['product_posts'],
        blobs=len(v['blob_metadata']), captures=len(v['captured_blob_files']), anchors=len(v['anchors']))
        for k, v in proof['scenarios'].items()}), indent=2))
