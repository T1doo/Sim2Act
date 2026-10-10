from pathlib import Path
import hashlib,json,re,base64,datetime
R=Path('/tmp/sim2act-report-dag-terminal-publication-independent-20261010');repo=Path('/workspace/Sim2Act');P=repo/'docs/evidence/csv-report-dag-reuse-20261010/native-final';SHA='50b10417a99a070f6bcd614471cc00ec102b7836'
load=lambda p:json.loads(p.read_text());h=lambda b:hashlib.sha256(b).hexdigest()
w=load(P/'COPY_WHITELIST.json');src=Path(w['artifact_root']);assert w['count']==len(w['files'])==17
for x in w['files']:
 b=(P/x['path']).read_bytes();assert b==(src/x['path']).read_bytes() and len(b)==x['bytes'] and h(b)==x['sha256']
assert {str(p.relative_to(P)) for p in P.rglob('*') if p.is_file()}=={x['path'] for x in w['files']}|{'COPY_WHITELIST.json'}
raw=(src/'native-final-full.log').read_bytes();assert len(raw)==4811976 and h(raw)==w['raw_log']=='9f4951d31759eb99f710b80c6370e4f969d4b15f7c0cb66f06421c4789355cc7'
events=[];full={};metas={};chunk={};summaries=[];positions=[]
for idx,line in enumerate(raw.decode().splitlines()):
 text=re.sub(r'^\d{4}-\d\d-\d\dT\S+ ','',line)
 for prefix,kind in [('SIM2ACT_CI_DIAGNOSTIC ','event'),('SIM2ACT_CI_FULL_COLLECTION ','full'),('SIM2ACT_BROWSER_FILE ','file'),('Engineering diagnostics: ','summary')]:
  if text.startswith(prefix):
   d=json.loads(text[len(prefix):]);positions.append((idx,kind))
   if kind=='event':events.append(d)
   elif kind=='full':assert d['offset'] not in full;full[d['offset']]=d['nodes']
   elif kind=='file':assert d['name'] not in metas;metas[d['name']]=d
   else:summaries.append(d)
 for name,index,b64 in re.findall(r'SIM2ACT_BROWSER_CHUNK ([^\s]+) (\d+) ([A-Za-z0-9+/=]+)',text):
  table=chunk.setdefault(name,{});assert int(index) not in table;table[int(index)]=b64
assert events==load(P/'native-final-events.json') and len(summaries)==1 and summaries[0]==load(P/'native-final-summary.json')
nodes=[n for offset in sorted(full) for n in full[offset]];assert sorted(full)==list(range(0,2270,20)) and len(nodes)==len(set(nodes))==2270 and nodes==load(P/'native-final-collection.json')
required=load(repo/'scripts/native-remaining11.json');assert len(required)==len(set(required))==11 and set(required)<=set(nodes)
assert len(events)==59 and len({e['pid'] for e in events})==1 and type(events[0]['pid']) is int and events[0]['pid']>0
assert [e['event'] for e in events[:3]]==['session_start','selection','collection_summary'] and events[0]['requested_scope']=='DIAGNOSTIC_ONLY_REMAINING11' and events[0]['required_nodes']==required
assert events[1]['required_nodes']==required and events[1]['scope']=='DIAGNOSTIC_ONLY_REMAINING11' and events[1]['full_count']==2270 and events[1]['full_nodes_sha256']==h(json.dumps(nodes).encode())
assert all(p[0]<next(p[0] for p in positions if p[1]=='event' and p[0]>positions[0][0]) for p in positions if p[1]=='full')
for i,node in enumerate(required):
 a=events[3+i*5:8+i*5];assert [e['event'] for e in a]==['node_start','node_report','node_report','node_report','node_finish'] and all(e['nodeid']==node for e in a)
 assert [e['phase'] for e in a[1:4]]==['setup','call','teardown'] and all(e['outcome']=='passed' for e in a[1:4])
assert events[-1]['event']=='session_finish' and events[-1]['exitstatus']==0
s=summaries[0];assert s['suite_complete'] and s['selection_verified'] and s['required_targets_complete'] and s['exitstatuses']==[0] and s['failure_reports']==0 and not s['incomplete_tail'] and s['deselected_count']==2259
assert s['junit'][0]['tests']=='11' and all(s['junit'][0][k]=='0' for k in ['failures','errors','skipped']) and s['junit'][0]['time']=='91.405'
proofs=[];assert len(metas)==len(chunk)==9
for name,m in metas.items():
 t=chunk[name];assert sorted(t)==list(range(m['chunks']));b=base64.b64decode(''.join(t[i] for i in sorted(t)),validate=True);assert h(b)==m['sha256'] and len(b)==m['bytes'] and b==(P/'native-final-browser'/name).read_bytes()
 if name.endswith('.json'):
  j=json.loads(b);assert j['status']=='PASS' and all(c['status']=='PASS' for c in j['checks']) and j['win11']=='NOT_RUN';proofs.append({'name':name,'checks':len(j['checks']),'visualReview':j.get('visualReview','author not reviewed')})
assert {x['name']:x['checks'] for x in proofs}=={'browser-results.json':69,'agent-results.json':33,'protocol-results.json':26}
run=load(P/'native-final-run.json');job=load(P/'native-final-jobs.json')['jobs'][0];assert run['id']==job['run_id']==38035830928 and job['id']==114165927573 and run['attempt']==1 and run['head_sha']==job['head_sha']==SHA and all(x['status']=='completed' and x['conclusion']=='success' for x in [run,job]) and all(x['conclusion']=='success' for x in job['steps'])
dt=lambda s:datetime.datetime.fromisoformat(s.replace('Z','+00:00'));secs=lambda a,b:(dt(b)-dt(a)).total_seconds()
assert secs(job['started_at'],job['completed_at'])==312
steps={x['name']:secs(x['started_at'],x['completed_at']) for x in job['steps']};assert steps['Engineering or explicitly marked remaining11 diagnostics']==103 and steps['Protected installed Edge real internal UI (synthetic, same runner)']==127
f=load(P/'source-after-native.json');assert f['source_sha']==SHA and f['source_unchanged'] and len(f['files'])==365
for path,d in f['files'].items():assert h((repo/path).read_bytes())==d
result={'verdict':'LIMITED_PASS_TERMINAL_PUBLICATION','source_sha':SHA,'run':run['id'],'job':job['id'],'attempt':1,'exact17private_copy':True,'raw_utf8_bytes':len(raw),'raw_sha256':h(raw),'full_nodes':2270,'selected':11,'deselected':2259,'passed_phases':33,'semantic_order_events':59,'full_collection_chunks':len(full),'browser_files9_exact_reassembled':True,'browser_check_layers':proofs,'job_seconds':312,'engineering_seconds':103,'Edge_seconds':127,'JUnit_seconds':91.405,'source365_unchanged':True,'newfeature20_notselected':True,'full_Windows_Win11_owner_semantic_acceptance':False,'historical_timeouts':'OPEN','tests_CI_PG_executed_in_audit':0,'rootmanifest':'awaiting_final_snapshot'}
(R/'TERMINAL_AUDIT.json').write_text(json.dumps(result,indent=2));(R/'NATIVE_WHITELIST_SNAPSHOT.json').write_bytes((P/'COPY_WHITELIST.json').read_bytes());print(json.dumps(result,indent=2))
