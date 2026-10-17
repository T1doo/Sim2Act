import hashlib, json, subprocess, xml.etree.ElementTree as ET
from pathlib import Path
BASE=Path('/tmp/csv-dag-directory-dual-fixed-independent-b670cb0c-20261017')
REPO=Path('/workspace/Sim2Act')
SOURCE='b670cb0c2a25dc363ffdaa0ea8d8a1d747c99d39'
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
failed=sum(int(v.get('failures',0))+int(v.get('errors',0)) for v in suites)
result=dict(source=SOURCE,rc=int(bool(failed)),tests=len(cases),passed=sum(not any(c.find(k) is not None for k in ('failure','error','skipped')) for c in cases),
            failures=sum(int(v.get('failures',0)) for v in suites),errors=sum(int(v.get('errors',0)) for v in suites),skipped=sum(int(v.get('skipped',0)) for v in suites),
            seconds=sum(float(v.get('time',0)) for v in suites),identities=[v.get('classname')+'::'+v.get('name') for v in cases],
            repeat_same_author_nodes=True,additional_unique_nodes=0,attempts_this_source=1,
            overall_review='PASS_WITHIN_EXECUTED_SCOPE' if not failed else 'BLOCKED_BY_INDEPENDENT_FAILURE',
            new_scenarios=['dual','fixed'],related_scenarios=['use','report'],
            static_findings=[],old_c628_findings_closed_in_review=['authoritative nonfirst selection plus selectedIndex checks','exact visible node labels','per-version complete visible row mappings'],
            scenarios={},source_after=after)
provenance={}
for p in sorted((BASE/'data').glob('*/result.json')):
    if p.parent.is_symlink(): continue
    v=json.loads(p.read_text()); dbpath=p.parent/'database-proof.json'; db=json.loads(dbpath.read_text()) if dbpath.exists() else {'completion_status':'NOT_PRODUCED: failed before post-driver database assertions'}
    key=('literal-' if 'literal' in p.parent.name else 'dag-')+v.get('scenario','use')
    req=v.get('requests',[])
    result['scenarios'][key]=dict(status=v['status'],checks=len(v['checks']) if isinstance(v['checks'],list) else v['checks'],
        database=db,product_http_requests=len(req),product_posts=sum(r.get('method')=='POST' for r in req),mutations=v.get('mutations',[]),
        info=str((p.parent/'info.json').relative_to(BASE)),result=str(p.relative_to(BASE)),error=v.get('error'),heldWaits=v.get('heldWaits',[]))
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
for scenario in result['scenarios'].values():
    directory=BASE/scenario['info']; info=json.loads(directory.read_text()); raw=json.loads((BASE/scenario['result']).read_text())
    fixture=json.loads((directory.parent/'fixture-proof.json').read_text())
    lists=[r['response']['items'] for r in raw['requests'] if r['path']==f"/api/internal/apps/{info['app']}/dag-instances" and r.get('status')==200]
    scenario['fixture_source_worker_runs']=len(fixture['source_worker_run_ids'])
    scenario['actual_authoritative_first_instance']=lists[0][0]['id'] if lists and lists[0] else None
    scenario['selected_instance']=info['instance']
    scenario['selected_is_authoritative_first']=scenario['selected_instance']==scenario['actual_authoritative_first_instance']
    scenario['authoritative_selection_listing_saved']=fixture.get('authoritative_selection_listing') is not None
    scenario['ui_nonfirst_assertion_completed']='directory explicitly selects the non-first authoritative instance' in raw['checks']
    scenario['visible_label_assertion_completed']='each visible input label names its own stable aggregate node ID' in raw['checks']
    scenario['visible_version_assertions_completed']=[v for v in raw['checks'] if 'visible version row' in v or 'cold visible history' in v]
    scenario['dom_evidence_provenance']='Completed real JSDOM assertions retained in raw checks and frozen driver; no separate DOM text snapshot recorded.'
    if info['scenario'] in ('dual','fixed') and raw['status']=='PASS':
        assert scenario['selected_is_authoritative_first'] is False
        assert fixture['authoritative_selection_listing']['items'][1]['id']==info['instance']
        assert scenario['ui_nonfirst_assertion_completed'] and len(scenario['visible_version_assertions_completed'])==3
        if info['scenario']=='dual': assert scenario['visible_label_assertion_completed']
result['directory_e2e_versions']=['internal.csv-read-two-sums.v1','internal.project-csv-read-sum-report.v1','internal.csv-read-sum.v1','internal.csv-read-sum-report.v1']
result['guard_and_finite_branch_scenarios']='NOT_RUN'
result['worker_counts']={}
for group,names in [('new',['dag-dual','dag-fixed']),('related',['dag-use','dag-report'])]:
    result['worker_counts'][group]=dict(source_worker_runs=sum(result['scenarios'][n]['fixture_source_worker_runs'] for n in names),
        cold_worker_runs_from_directory=sum(result['scenarios'][n]['database'].get('cold_worker_runs_from_directory',0) for n in names))
result['not_executed']=['guards/finite branches','other related nodes','PG','native browser','Windows','real semantic scenarios','real models','remote CI','additional lost/recovery or private matrices']
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
