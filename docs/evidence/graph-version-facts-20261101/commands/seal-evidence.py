from pathlib import Path
import hashlib,json,os,re,subprocess
from xml.etree import ElementTree as ET
repo=Path('/workspace/Sim2Act');out=repo/'docs/evidence/graph-version-facts-20261101'
app='97f4c0af7932c21cb21b6498b642b1639ab050ca';baseline='2c54f5fef7918f8cf5364eda651477f47cf10c0d'
def git(*args):return subprocess.check_output(['git',*args],cwd=repo,text=True).strip()
def sha(data):return hashlib.sha256(data).hexdigest()
def write(name,value):(out/name).write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')
assert git('rev-parse','HEAD')==app and not git('diff',app,'--','src')
cases=[]
for label in ('baseline30','baseline120','candidate30','candidate120','cancel'):
    meta=json.loads((out/label/'run-run.json').read_text())
    assert meta['source_unchanged'] and meta['status']=='COMPLETED' and meta['returncode']==0
    assert meta['source_commit']==(baseline if label.startswith('baseline') else app)
    cases.append(dict(path=label,source=meta['source_commit'],observer=meta['observer_sha256'],
        returncode=0,source_unchanged=True,real_model_requests=0,
        fixed_mock_requests=7 if label.endswith('120') else 6))
    if label.endswith('30'):
        profile=json.loads((out/label/'graph-version-real-clock-profile.json').read_text())
        assert len(profile['epochs'])==1 and profile['epochs'][0]['final_phase']=='G0'
        assert profile['epochs'][0]['g1_phase_entered'] is False
for rel,count in [('regressions/graph-dict-version-final-regression-20261101.xml',310),
                  ('regressions/graph-dict-version-real-signals-final-20261101.xml',3)]:
    tests=ET.parse(out/rel).getroot().findall('.//testcase')
    assert len(tests)==count and all(not any(t.find(x) is not None for x in ('failure','error','skipped')) for t in tests)
paired=[]
for label in ('baseline120','candidate120'):
    data=json.loads((out/label/'snapshot-writer-timings.json').read_text())['records']
    assert len(data)==2 and all(r['outcome']=='COMMITTED' for r in data)
    for i,row in enumerate(data,1):paired.append(dict(source=baseline if label=='baseline120' else app,ordinal=i,**row))
reopen=[json.loads((out/name).read_text()) for name in (
    'graph-metadata-signed120-2c54f5fe-first-reopen-20261101.json',
    'graph-dictionary-signed120-97f4c0af-first-reopen-20261101.json')]
assert all(r['status']=='PASS' and r['database_content_unchanged'] for r in reopen)
convergence=json.loads((out/'cancel/convergence-result.json').read_text())
assert convergence['status']=='PASS' and convergence['final']=='CANCELLED' and convergence['new_model_attempts']==0
old=repo/'deliverables/limited-graph-current-20261101/Sim2Act-local-candidate-35eaa941f544.zip'
assert old.stat().st_size==3270375 and sha(old.read_bytes())=='927501b0a87aee143ed152f998073be31631b4104cec642cfe697e8fdd49155b'
for target in re.findall(r'\]\(([^)]+)\)',(out/'README.md').read_text()):
    if not target.startswith(('http:','https:','#')):assert (out/target).exists(),target
write('identity.json',dict(application_source=app,baseline_source=baseline,source_tree=git('rev-parse',app+':src'),
    cases=cases,paired_signed120=paired,ordinary30='FAILED_G0_BEFORE_DML_NO_G1',
    end_to_end_net_improvement=False,latest_installed_candidate_source='35eaa941f544ca016ddeeefb839178d316fc1c6b',
    old_candidate_bytes=old.stat().st_size,old_candidate_sha256=sha(old.read_bytes()),
    new_installer_generated=False,regression310='WIP execution; exact application bytes then frozen unchanged',
    real_model_requests_this_phase=0,formal_pg=False,new_windows=False,main_changed=False,release=False))
secrets=[os.environ[k].encode() for k in ('GH_TOKEN','GITHUB_TOKEN','INTERN_API_TOKEN','SIM2ACT_INTERN_TOKEN') if os.environ.get(k)]
extras=[repo/'README.md',repo/'docs/graph-version-lifecycle.md']
files=sorted([p for p in out.rglob('*') if p.is_file()]+extras)
for p in files:
    assert p.suffix not in ('.db','.sqlite','.sqlite3','.env')
    assert not any(s in p.read_bytes() for s in secrets),'Configured secret detected; no value emitted'
write('privacy-check.json',dict(status='PASS',scope='New evidence plus root README and protocol update; exact configured nonempty secret values, no values emitted',
    raw_db_or_env=False,body_archive_included=False,limitations='Not a proof against all conceivable private information; fixture provenance separately reviewed'))
files=sorted([p for p in out.rglob('*') if p.is_file() and p.name!='artifact-manifest.json']+extras)
write('artifact-manifest.json',dict(application_source=app,algorithm='SHA256',excludes_self=True,
    files=[dict(path=str(p.relative_to(repo)),bytes=p.stat().st_size,sha256=sha(p.read_bytes())) for p in files]))
print(json.dumps(dict(status='PASS',application_source=app,files=len(files),source_unchanged=True,configured_secret_scan='PASS',old_installer_unchanged=True)))
