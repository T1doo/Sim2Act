from pathlib import Path
import datetime, hashlib, json, shutil, subprocess, xml.etree.ElementTree as ET

ROOT=Path('/workspace/Sim2Act')
OUT=Path(__file__).parent
OLD=OUT.parent
sha=lambda b:hashlib.sha256(b).hexdigest()

def save(name,value):
    p=OUT/name
    assert not p.exists(),p
    p.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n')

def count(name):
    tree=ET.parse(OUT/name).getroot();cases=list(tree.iter('testcase'));named=[c for c in cases if c.get('name')]
    return {'file':name,'named_nodes':len(named),'passed':sum(all(c.find(t) is None for t in ['failure','error','skipped']) for c in named),'failed':sum(c.find('failure') is not None for c in named),'errors':sum(c.find('error') is not None for c in named),'skipped':sum(c.find('skipped') is not None for c in named),'anonymous_records_excluded':len(cases)-len(named),'seconds':tree.find('testsuite').get('time')}

def pages(folder):
    rows=[]
    for file in sorted((OUT/folder).glob('*.json')):
        if file.name.endswith('-private.json'):continue
        obj=json.loads(file.read_text());assets=obj['static_resource_loads'];bad=[]
        for a in assets:
            data=(ROOT/'src/sim2act/web'/(a['path'].lstrip('/') or 'index.html')).read_bytes()
            mime={'/':'text/html; charset=utf-8','/app.css':'text/css; charset=utf-8'}.get(a['path'],'text/javascript; charset=utf-8')
            if a['status']!=200 or a['content_type']!=mime or a['bytes']!=len(data) or a['sha256']!=sha(data):bad.append(a)
        gestures=[a for a in obj['actions'] if a.get('event')=='DOM dispatch' and a.get('visible') is True and a.get('enabled') is True]
        post=lambda suffix:sum(r['method']=='POST' and r['path'].split('?')[0].endswith(suffix) for r in obj['requests'])
        rows.append({'path':str(file.relative_to(OUT)),'status':obj['status'],'scenario':obj['scenario'],'phase':obj.get('phase'),'process_id':obj.get('process_id'),'checks':len(obj['checks']),'visible_enabled_dom_dispatch_gestures':len(gestures),'other_action_records':len(obj['actions'])-len(gestures),'boots':len(set(a['boot'] for a in assets)),'actual_http_assets':len(assets),'asset_status_mime_bytes_sha_mismatches':bad,'prepare_posts':post('/extraction-requests'),'extract_posts':post('/extract'),'close_posts':post('/extraction-request-close'),'storage_attempts':obj.get('storage_attempts'),'controlled_other_actor_requests':len(obj.get('other_actor_requests',[]))})
    assert all(r['status']=='PASS' and not r['asset_status_mime_bytes_sha_mismatches'] for r in rows)
    pairs=[]
    if rows and all(r['phase'] for r in rows):
        for scenario in sorted(set(r['scenario'] for r in rows)):
            pair=[r for r in rows if r['scenario']==scenario]
            assert len(pair)==2 and set(r['phase'] for r in pair)=={'first','cold'} and len(set(r['process_id'] for r in pair))==2
            pairs.append({'scenario':scenario,'distinct_processes':True,'process_ids':[r['process_id'] for r in pair]})
    return {'folder':folder,'outputs':len(rows),'checks':sum(r['checks'] for r in rows),'gestures':sum(r['visible_enabled_dom_dispatch_gestures'] for r in rows),'other_action_records':sum(r['other_action_records'] for r in rows),'boots':sum(r['boots'] for r in rows),'actual_http_assets':sum(r['actual_http_assets'] for r in rows),'all_status_mime_bytes_sha_match':True,'pairs':pairs,'rows':rows}

manifest_path=ROOT/'docs/evidence/pb-cold-recovery-20261011/candidate4-source-freeze.json'
m=json.loads(manifest_path.read_text());actual={n:sha((ROOT/n).read_bytes()) for n in m['sha256']};diff=[n for n in actual if actual[n]!=m['sha256'][n]]
assert len(actual)==369 and not diff
save('source-after.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'count':369,'manifest_file_sha256':sha(manifest_path.read_bytes()),'source_map_sha256':m['source_map_sha256'],'differences':diff,'sha256':actual})

old_manifest_path=OLD/'archive-manifest.json';old_manifest=json.loads(old_manifest_path.read_text());old_diff=[r['path'] for r in old_manifest['files'] if sha((OLD/r['path']).read_bytes())!=r['sha256']]
assert len(old_manifest['files'])==733 and not old_diff
save('candidate3-withdrawn733-preservation.json',{'status':'PRESERVED_WITHDRAWN_CANDIDATE3','file_count':733,'manifest_sha256':sha(old_manifest_path.read_bytes()),'differences':old_diff,'reason':'The original LIMITED_PASS sealed before the real65-source budget red is withdrawn for acceptance. All prior results, failed histories, fixture overwrite/restoration, and source snapshots remain immutable; final acceptance derives from candidate4 only.','budget_red':'../budget-new/budget-red-review.json','original_report':'../FINAL_REVIEW.md'})

groups=[pages(name) for name in ['cold-pages','existing-pages','extra-cold-pages','extra-latest-pages']]
assert [g['outputs'] for g in groups]==[36,9,2,2]
save('http-page-metrics.json',{'groups':groups,'classification':'Actual SQLite/FastAPI TestClient IPC HTTP assets and APIs/new JSDOM; synthetic upstream fixture LIVE0; native browser NOT_RUN. External digest interleaving is controlled with actual native SHA and actual API new prepare.','cross_device_atomic_installation_claim':False})

results=[count(name+'.xml') for name in ['new','existing','extra','budget']]
assert [r['named_nodes'] for r in results]==[39,43,6,1]
assert all(r['named_nodes']==r['passed'] and not r['failed'] and not r['errors'] and not r['skipped'] for r in results)
save('actual-test-counts.json',{'final_groups':results,'do_not_add_withdrawn_runs_to_final':True,'root_related_suite':'RUNNING at independent seal; not part of independent coverage until separately reported.'})

raw=OUT/'pytest-raw-json-proofs';raw.mkdir(exist_ok=False);copies=[]
for d in sorted(OUT.glob('*-db')):
    for f in sorted(d.rglob('*.json')):
        if f.is_symlink() or not f.is_file():continue
        target=raw/f.relative_to(OUT);target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,target);assert f.read_bytes()==target.read_bytes()
        copies.append({'original':str(f.relative_to(OUT)),'copy':str(target.relative_to(OUT)),'bytes':len(f.read_bytes()),'sha256':sha(f.read_bytes())})
save('pytest-raw-json-proofs.json',{'purpose':'Original raw JSON/info/SQL proof copies outside excluded basetemp databases; no DB/cache copied or deleted.','count':len(copies),'files':copies})

budget=json.loads((OUT/'budget/actual65-budget-proof.json').read_text())
assert budget['succeeded_source_runs']==budget['distinct_run_ids']==65 and budget['source65_prepare_status']==400 and budget['source65_index_status']==200 and budget['records'][-1]['all_tables_unchanged']
save('budget-green-summary.json',{'classification':'ACTUAL65_SUCCEEDED_APPRUNS_WITH_NORMAL_LITERAL_WORKER_AND_HTTP','actual65_successful_sources':65,'same_instance':budget['instance'],'attempts_per_literal_run':0,'typed_record_and_verified_operation_per_run':1,'source64_index_status':budget['source64_index_status'],'source65_prepare_status':budget['source65_prepare_status'],'source65_index_status':budget['source65_index_status'],'source65_index_items':len(budget['records'][-1]['project_index']['body']['items']),'source65_prepare_all_tables_unchanged':budget['records'][-1]['all_tables_unchanged'],'existing_source_at64':[{'action':r['action'],'status':r['status']} for r in budget['existing_source_actions_at_cap']],'synthetic_upstream_fixture_only':True,'actual_model_requests_for65_literal_runs':0,'red_history':'../budget-new/actual65-budget-proof.json'})

active=[]
for line in subprocess.check_output(['ps','-eo','pid,args'],text=True).splitlines():
    if str(OUT) in line and ('-m pytest' in line or 'node ' in line) and 'ps -eo' not in line:active.append(line.strip())
assert not active,active
save('health.json',{'utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'active_owned_pytest_node':active,'groups':[json.loads((OUT/(kind+'-process.json')).read_text()) for kind in ['new','existing','extra','budget']]})
print(json.dumps({'counts':results,'source369_differences':diff,'prior733_differences':old_diff,'pages':[{k:g[k] for k in ['folder','outputs','checks','gestures','boots','actual_http_assets']} for g in groups],'raw_json_copies':len(copies),'active':active},indent=2))
