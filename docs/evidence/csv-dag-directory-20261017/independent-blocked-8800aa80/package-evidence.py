import hashlib, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path('/tmp/csv-dag-directory-independent-8800aa80-20261017')
REPO=Path('/workspace/Sim2Act')
SOURCE='8800aa800d71a2d389a4283796e8a62271e06b4d'
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
result=dict(source=SOURCE,rc=1,tests=len(cases),passed=sum(not any(c.find(k) is not None for k in ('failure','error','skipped')) for c in cases),
            failures=sum(int(s.get('failures',0)) for s in suites),errors=sum(int(s.get('errors',0)) for s in suites),skipped=sum(int(s.get('skipped',0)) for s in suites),
            seconds=sum(float(s.get('time',0)) for s in suites),identities=[c.get('classname')+'::'+c.get('name') for c in cases],
            repeat_same_author_nodes=True,additional_unique_nodes=0,attempts_this_source=1,
            overall_review='BLOCKED_BY_INDEPENDENT_GUARDS_SYNCHRONIZATION_FAILURE',
            old_static_findings={'TEMP_DELIVERY_FENCE':'fixed; exact single-aggregate condition retained',
                'SAVED_DAG_AUTH_REFRESH_CACHE':'static fix retained unchanged; this guards attempt stopped before revoke; actual refresh403 was repeated in prior212 source',
                'OPTIONAL_DAG_GLOBALS':'fixed with three typeof checks; unchanged original failing CSV component repeated'},
            static_findings=[],independent_failure=dict(scenario='DAG guards',action='Second late-error opening waits for exact instance read gate',observed='bounded wait exceeded 12-second total window; seven prior checks passed; last actual request is target instance GET200; mutations empty; late-error/revoke checks not completed',attribution='Unresolved synchronization deadline; insufficient evidence to determine scheduling cause or product correctness beyond completed checks'),scenarios={},source_after=after)
provenance={}
for p in sorted((BASE/'data').glob('*/result.json')):
    if p.parent.is_symlink(): continue
    v=json.loads(p.read_text()); dbpath=p.parent/'database-proof.json'; db=json.loads(dbpath.read_text()) if dbpath.exists() else {'completion_status':'NOT_PRODUCED: failed before post-driver database assertions'}
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
for p in sorted((BASE/'data').glob('*/results.json')):
    if p.parent.is_symlink(): continue
    v=json.loads(p.read_text())
    result['scenarios']['csv-component-use']=dict(status=v['status'],checks=len(v['checks']),
        actual_transport='loopback HTTP via existing uvicorn test fixture',posts=v['posts'],lifecycle=v['lifecycle'],
        runtime_model_calls=v['real_model_requests'],partial_script_list=['app.js','internal.js','protocol.js','use.js'],
        info=str((p.parent/'info.json').relative_to(BASE)),result=str(p.relative_to(BASE)),
        database_python_assertions='principals/grants unchanged; internal_app_runs=3; internal_instance_data=2',
        component_transport_response_bodies='not recorded by this unchanged existing driver')
result['finite_branch_cases']=2
result['finite_branch_is_recovery']=False
result['directory_e2e_versions']=['internal.csv-read-sum.v1','internal.csv-read-sum-report.v1']
result['dual_and_fixed_directory_e2e']='NOT_RUN'
result['not_executed']=['other related nodes','PG','native browser','Windows','real semantic scenarios','real models','remote CI','dual/fixed directory E2E','additional lost/recovery or private matrices']
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
print(json.dumps(dict(tests=result['tests'],passed=result['passed'],failures=result['failures'],errors=result['errors'],skipped=result['skipped'],seconds=result['seconds'],source_after_match=after['source_tests_match_frozen_git'],raw_files=len(manifest),scenarios={k:dict(checks=v['checks'],requests=v.get('product_http_requests','not recorded by unchanged component driver'),posts=v.get('product_posts',v.get('posts'))) for k,v in result['scenarios'].items()}),indent=2))
