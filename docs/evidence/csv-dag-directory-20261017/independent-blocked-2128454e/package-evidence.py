import hashlib, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path('/tmp/csv-dag-directory-independent-2128454e-20261017')
REPO=Path('/workspace/Sim2Act')
SOURCE='2128454e6b8c38408c3463d03f3632ac91f11301'
def sha(data): return hashlib.sha256(data).hexdigest()
def git(*args): return subprocess.check_output(['git',*args],cwd=REPO)
def dump(path,value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
before=json.loads((BASE/'source-before.json').read_text())
files={name:sha((REPO/name).read_bytes()) for name in before['files']}
after=dict(source=SOURCE,head_after=git('rev-parse','HEAD').decode().strip(),files=files,
           source_tests_match_frozen_git=all(files[name]==expected==sha(git('show',SOURCE+':'+name)) for name,expected in before['files'].items()),
           git_status_after=git('status','--porcelain').decode())
if (BASE/'source-after.json').exists():
    after=json.loads((BASE/'source-after.json').read_text())
else:
    dump(BASE/'source-after.json',after)
assert after['source_tests_match_frozen_git']
root=ET.parse(BASE/'junit.xml').getroot()
suites=list(root.iter('testsuite'))
cases=list(root.iter('testcase'))
result=dict(source=SOURCE,rc=0,tests=len(cases),passed=sum(not any(c.find(k) is not None for k in ('failure','error','skipped')) for c in cases),
            failures=sum(int(s.get('failures',0)) for s in suites),errors=sum(int(s.get('errors',0)) for s in suites),skipped=sum(int(s.get('skipped',0)) for s in suites),
            seconds=sum(float(s.get('time',0)) for s in suites),identities=[c.get('classname')+'::'+c.get('name') for c in cases],
            repeat_same_author_nodes=True,additional_unique_nodes=0,attempts_this_source=1,
            overall_review='BLOCKED_BY_OPTIONAL_SCRIPT_COMPATIBILITY_DESPITE_SPECIFIED_DYNAMIC_PASS',
            old_static_findings={'TEMP_DELIVERY_FENCE':'fixed in reviewed source and literal navigation read repeated','SAVED_DAG_AUTH_REFRESH_CACHE':'fixed in reviewed source and real directory-refresh403 repeated'},
            static_findings=[dict(id='OPTIONAL_DAG_GLOBALS',status='BLOCK',files=['src/sim2act/web/use.js:28','src/sim2act/web/use.js:86','src/sim2act/web/app.js:565'],
                evidence='Optional script component tests load app/internal/protocol/use only. Optional chaining does not guard an undeclared csvDagContext or deliveryContext identifier.',
                parent_reported_related_actual_failure='Existing CSV component scenario timed out waiting for saved instance list; parent observed and accepted minimal typeof guards.',
                related_failure_independently_executed=False)],scenarios={},source_after=after)
provenance={}
for p in sorted((BASE/'data').glob('*/result.json')):
    if p.parent.is_symlink(): continue
    v=json.loads(p.read_text()); db=json.loads((p.parent/'database-proof.json').read_text())
    key=('literal-' if 'literal' in p.parent.name else 'dag-')+v.get('scenario','use')
    req=v.get('requests',[])
    result['scenarios'][key]=dict(status=v['status'],checks=len(v['checks']) if isinstance(v['checks'],list) else v['checks'],
        database=db,product_http_requests=len(req),product_posts=sum(r.get('method')=='POST' for r in req),mutations=v.get('mutations',[]),
        info=str((p.parent/'info.json').relative_to(BASE)),result=str(p.relative_to(BASE)))
    for a in v['assets']:
        name='src/sim2act/web/'+(a['path'].lstrip('/') or 'index.html')
        data=git('show',SOURCE+':'+name)
        assert sha(data)==a['sha256'],name
        out=BASE/'statics'/name.removeprefix('src/sim2act/web/')
        out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(data)
        value=dict(http_path=a['path'],sha256=a['sha256'],copied_file=str(out.relative_to(BASE)))
        assert name not in provenance or provenance[name]==value
        provenance[name]=value
result['finite_branch_cases']=2
result['finite_branch_is_recovery']=False
result['directory_e2e_versions']=['internal.csv-read-sum.v1','internal.csv-read-sum-report.v1']
result['dual_and_fixed_directory_e2e']='NOT_RUN'
result['not_executed']=['CSV optional-script component failure independently (parent-reported only)','other related nodes','PG','native browser','Windows','real semantic scenarios','real models','remote CI','dual/fixed directory E2E','old lost/recovery or private matrices']
dump(BASE/'static-source-provenance.json',dict(source=SOURCE,provenance='Frozen source copies matched to recorded actual HTTP-response SHA256, not raw transport-stream capture or new requests.',files=provenance))
excluded={'package-evidence.py','independent-review.md','independent-proof.json','raw-manifest.json','raw-SHA256SUMS'}
manifest={}
for p in sorted(BASE.rglob('*')):
    if not p.is_file() or p.is_symlink() or any(parent.is_symlink() for parent in p.parents if parent!=BASE): continue
    rel=str(p.relative_to(BASE))
    if rel in excluded: continue
    data=p.read_bytes(); manifest[rel]=dict(sha256=sha(data),bytes=len(data))
dump(BASE/'raw-manifest.json',manifest)
(BASE/'raw-SHA256SUMS').write_text(''.join(v['sha256']+'  '+k+'\n' for k,v in manifest.items()))
result.update(static_copies=len(provenance),raw_manifest_count=len(manifest),raw_manifest_sha256=sha((BASE/'raw-manifest.json').read_bytes()),raw_sums_sha256=sha((BASE/'raw-SHA256SUMS').read_bytes()))
dump(BASE/'independent-proof.json',result)
print(json.dumps(dict(tests=result['tests'],passed=result['passed'],failures=result['failures'],errors=result['errors'],skipped=result['skipped'],seconds=result['seconds'],source_after_match=after['source_tests_match_frozen_git'],raw_files=len(manifest),scenarios={k:dict(checks=v['checks'],requests=v['product_http_requests'],posts=v['product_posts']) for k,v in result['scenarios'].items()}),indent=2))
