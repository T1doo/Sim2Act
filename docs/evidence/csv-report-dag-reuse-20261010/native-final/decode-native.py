import sys,json,re,hashlib,base64,datetime
from pathlib import Path
root=Path(sys.argv[1]);tag=sys.argv[2];sha=sys.argv[3]
raw=(root/(tag+'-full.log')).read_bytes();lines=raw.decode().splitlines();events=[];chunks={};meta={};bc={};summary=None
for line in lines:
 t=re.sub(r'^\d{4}-\d\d-\d\dT\S+ ', '',line)
 if t.startswith('SIM2ACT_CI_DIAGNOSTIC '):events.append(json.loads(t.split(' ',1)[1]))
 elif t.startswith('SIM2ACT_CI_FULL_COLLECTION '):d=json.loads(t.split(' ',1)[1]);assert d['offset'] not in chunks;chunks[d['offset']]=d['nodes']
 elif t.startswith('Engineering diagnostics: '):assert summary is None;summary=json.loads(t[len('Engineering diagnostics: '):])
 elif t.startswith('SIM2ACT_BROWSER_FILE '):d=json.loads(t.split(' ',1)[1]);assert d['name'] not in meta;meta[d['name']]=d
for name,index,data in re.findall(r'SIM2ACT_BROWSER_CHUNK ([^\s]+) (\d+) ([A-Za-z0-9+/=]+)',raw.decode()):
 table=bc.setdefault(name,{});assert int(index) not in table;table[int(index)]=data
nodes=[n for off in sorted(chunks) for n in chunks[off]];assert sorted(chunks)==list(range(0,len(nodes),20));assert len(nodes)==len(set(nodes))
expected=json.loads(Path('scripts/native-remaining11.json').read_text());assert len(expected)==11
assert summary['suite_complete'] and summary['selection_verified'] and summary['required_targets_complete'] and summary['collected']==summary['finished']==summary['started']==11 and summary['failure_reports']==0 and summary['exitstatuses']==[0]
assert summary['full_collection_count']==len(nodes) and summary['deselected_count']==len(nodes)-11
assert summary['full_collection_sha256']==hashlib.sha256(json.dumps(nodes).encode()).hexdigest()
assert summary['junit'][0]['tests']=='11' and summary['junit'][0]['errors']==summary['junit'][0]['failures']==summary['junit'][0]['skipped']=='0'
reports=[r for r in events if r['event']=='node_report'];assert len(reports)==33 and all(r['outcome']=='passed' for r in reports);assert set(r['nodeid'] for r in reports)==set(expected)
browser=root/(tag+'-browser');browser.mkdir(exist_ok=True);proofs=[];assert len(meta)==len(bc)==9
for name,m in meta.items():
 assert '/' not in name and '\\' not in name
 table=bc[name];assert sorted(table)==list(range(m['chunks']));data=base64.b64decode(''.join(table[i] for i in sorted(table)),validate=True);assert len(data)==m['bytes'] and hashlib.sha256(data).hexdigest()==m['sha256'];(browser/name).write_bytes(data)
 proof={**m,'exact_reassembly':True}
 if name.endswith('.json'):
  d=json.loads(data);assert d['status']=='PASS' and all(c['status']=='PASS' for c in d['checks']);proof['check_count']=len(d['checks']);proof['win11']=d['win11'];proof['visualReview']=d.get('visualReview','author not reviewed');assert d['win11']=='NOT_RUN'
  if name=='browser-results.json':assert d['commit']==sha and d['inventory']['runner']=='windows-2025' and d['inventory']['signature']=='Valid' and d['chromiumSandbox'] and d['modelRequests']==0
  if name=='protocol-results.json':assert d['networkProviderRequests']==d['browserReviewRequests']==0 and not d['formalPublication'] and d['ownerSemanticAcceptance']=='PENDING'
 proofs.append(proof)
jobs=json.loads((root/(tag+'-jobs.json')).read_text());job=jobs['jobs'][0];assert job['head_sha']==sha and job['status']=='completed' and job['conclusion']=='success' and all(s['conclusion']=='success' for s in job['steps'])
def duration(a,b):return (datetime.datetime.fromisoformat(b.replace('Z','+00:00'))-datetime.datetime.fromisoformat(a.replace('Z','+00:00'))).total_seconds()
result=dict(source_sha=sha,run=job['run_id'],job=job['id'],scope='DIAGNOSTIC_ONLY_REMAINING11',full_collection=len(nodes),deselected=len(nodes)-11,passed=11,failed=0,skipped=0,node_reports=33,job_seconds=duration(job['started_at'],job['completed_at']),step_seconds={s['name']:duration(s['started_at'],s['completed_at']) for s in job['steps']},JUnit_seconds=float(summary['junit'][0]['time']),raw_utf8_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),browser_files=proofs,LIVE=0,real_model_requests=0,full_engineering_acceptance='NOT_ACCEPTED',new_report_feature_nodes_not_in_fixed11=True)
for suffix,data in [('summary',summary),('events',events),('collection',nodes),('result',result)]: (root/(tag+'-'+suffix+'.json')).write_text(json.dumps(data,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='browser_files'}))
