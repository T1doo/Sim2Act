from pathlib import Path
import hashlib, io, json, os, re, subprocess, zipfile
from datetime import datetime, timezone
from xml.etree import ElementTree as ET

repo = Path('/workspace/Sim2Act')
evidence = repo/'docs/evidence/graph-current-real-clock-20261101'
delivery = repo/'deliverables/limited-graph-current-20261101'
source = '35eaa941f544ca016ddeeefb839178d316fc1c6b'
baseline = '27619e9c7d250694a3f614f7960427321e804ca4'
def git(*args):
    return subprocess.check_output(['git', *args], cwd=repo, text=True).strip()
def write(name, value):
    (evidence/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n')
def digest(data):
    return hashlib.sha256(data).hexdigest()
assert git('rev-parse', 'HEAD') == source
assert not git('diff', source, '--', 'src')
assert not git('diff', '--cached', source, '--', 'src')
run_rows = []
for label, expected, calls in [('baseline30', baseline, 6), ('baseline120', baseline, 7),
                                ('candidate30', source, 6), ('candidate120', source, 7), ('cancel', source, 6)]:
    meta = json.loads((evidence/label/'run-run.json').read_text())
    assert meta['source_commit'] == expected
    assert meta['status'] == 'COMPLETED' and meta['returncode'] == 0 and meta['source_unchanged']
    run_rows.append(dict(path=label, source_commit=expected, fixed_mock_requests=calls,
                         real_model_requests=0, command_returncode=0, source_unchanged=True,
                         ordinary30_goal_success=False if label.endswith('30') else None))
test_rows = []
for rel, expected in [('regression/run.xml',189), ('fused-boundaries/run.xml',78), ('ordinary-report-unit.xml',16)]:
    cases = ET.parse(evidence/rel).getroot().findall('.//testcase')
    assert len(cases) == expected
    assert all(not any(c.find(tag) is not None for tag in ('failure','error','skipped')) for c in cases)
    test_rows.append(dict(path=rel, passed=expected, skipped=0))
archive = delivery/'Sim2Act-local-candidate-35eaa941f544.zip'
payload = archive.read_bytes()
assert len(payload) == 3270375 and digest(payload) == '927501b0a87aee143ed152f998073be31631b4104cec642cfe697e8fdd49155b'
with zipfile.ZipFile(io.BytesIO(payload)) as z:
    wheel = z.read('Sim2Act-local-candidate/wheels/sim2act-0.1.0-cp312-cp312-linux_x86_64.whl')
assert len(wheel) == 1788586 and digest(wheel) == 'e5cb821f14f26261ae6a9272608b2ce1d82abd2874ad2f82e87ebec00727f68a'
old = repo/'deliverables/limited-text-candidate-deadline-20261031/Sim2Act-local-candidate-2ad3227621b4.zip'
assert old.stat().st_size == 3188692 and digest(old.read_bytes()) == '6b6e42d909089ad001a6ff889976b7eff0e65ab7e4229fd95f15377b57efe81d'
for doc in [evidence/'README.md', delivery/'README.md', repo/'docs/graph-version-lifecycle.md']:
    for target in re.findall(r'\]\(([^)]+)\)', doc.read_text()):
        if target.startswith(('http:', 'https:', '#', 'mailto:')):
            continue
        assert (doc.parent/target.split('#',1)[0]).exists(), (str(doc), target)
write('identity.json', dict(
    generated_utc=datetime.now(timezone.utc).isoformat(), application_source_commit=source,
    baseline_source_commit=baseline, source_tree=git('rev-parse', source+':src'),
    source_diff_from_frozen_application='', database='test_only file SQLite/WAL',
    clock='real wall and monotonic; passive observer overhead included',
    runs=run_rows, regression=test_rows,
    test_count_note='78 overlaps 189; 16 checks only reporting helper; do not add these counts',
    candidate=dict(file=str(archive.relative_to(repo)), bytes=len(payload), sha256=digest(payload),
                   wheel_bytes=len(wheel), wheel_sha256=digest(wheel), installed_same_wheel=True),
    old_candidate_preserved=True, full_product_acceptance=False,
    remaining=['ordinary30 fails G0 before first DML; G1 not reached',
               'signed120 writer interval remains about 52/56 seconds',
               'no new live model, formal PG, Windows or unrestricted goal acceptance'],
))
extra = [repo/p for p in ['README.md','docs/graph-version-lifecycle.md',
          'scripts/diagnose_ordinary_thirty.py','tests/test_ordinary_thirty_diagnostic.py']]
def files():
    return sorted(set([p for root in (evidence, delivery) for p in root.rglob('*') if p.is_file()] + extra))
secret_keys = ('INTERN_API_TOKEN','SIM2ACT_INTERN_TOKEN','GH_TOKEN','GITHUB_TOKEN')
secrets = [os.environ[k].encode() for k in secret_keys if os.environ.get(k)]
def check_bytes(data):
    assert not any(value in data for value in secrets), 'Injected secret detected; no value emitted'
def check_zip(data):
    count = 0
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for item in z.infolist():
            if item.is_dir(): continue
            body = z.read(item)
            check_bytes(body)
            count += 1
            if item.filename.endswith(('.zip','.whl')):
                count += check_zip(body)
    return count
nested = 0
for path in files():
    data = path.read_bytes(); check_bytes(data)
    assert path.suffix not in ('.db','.sqlite','.sqlite3','.env'), str(path)
    if path.suffix in ('.zip','.whl'): nested += check_zip(data)
write('privacy-check.json', dict(status='PASS', scan='exact nonempty configured injected secret values; no values emitted',
    nested_archive_entries_checked=nested, raw_database_or_env_file_present=False,
    scope='new evidence, candidate, README/protocol and report-helper changes; includes decompressed ZIP/wheel',
    limitation='Exact configured-secret scan is not proof of all possible private information; synthetic provenance separately reviewed'))
manifest = [dict(path=str(p.relative_to(repo)), bytes=p.stat().st_size, sha256=digest(p.read_bytes()))
            for p in files() if p != evidence/'artifact-manifest.json']
write('artifact-manifest.json', dict(application_source_commit=source, algorithm='SHA256',
    excludes=['docs/evidence/graph-current-real-clock-20261101/artifact-manifest.json'], files=manifest))
for path in files(): check_bytes(path.read_bytes())
assert not git('diff', source, '--', 'src')
print(json.dumps(dict(status='PASS', application_source_commit=source, manifest_files=len(manifest),
    nested_archive_entries_checked=nested, local_links='PASS', configured_secret_scan='PASS',
    source_unchanged=True, old_candidate_preserved=True)))
