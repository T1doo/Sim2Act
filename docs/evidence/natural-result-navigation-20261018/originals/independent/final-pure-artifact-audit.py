"""Stdlib-only closed-file audit. No app imports, HTTP, worker, model or SQL."""
import ast, base64, collections, hashlib, json, re, subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
R=Path('/workspace/Sim2Act'); E=Path('/workspace/natural-result-navigation-evidence-20261018'); O=Path(__file__).parent
P=E/'actual-complete-tmp/test_same_pb_instance_navigate0'; SHA='ba6e1e06babdf591cbd439ee769b1c2a9cd0aa98'
def read(p): return json.loads(p.read_text())
def sha(b): return hashlib.sha256(b).hexdigest()
def canon(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def fp(v): return sha(canon(v))
def git(*a): return subprocess.check_output(['git','-c','core.fsmonitor=false',*a],cwd=R)
def one(rows,pred):
 out=[x for x in rows if pred(x)]; assert len(out)==1,len(out); return out[0]
assert git('rev-parse','HEAD').decode().strip()==SHA
baseline=read(E/'inputs-final-source.json'); ending=read(E/'inputs-after-final.json'); assert baseline['inputs']==ending['inputs']
assert len(baseline['inputs'])==687 and sum(p.startswith('src/sim2act/') for p in baseline['inputs'])==133
for p,m in baseline['inputs'].items():
 raw=(R/p).read_bytes();assert m==dict(bytes=len(raw),sha256=sha(raw))
direct=read(P/'source-after.json');assert len(direct)==141
for p,m in direct.items():assert baseline['inputs'][p]==m
assert set(read(P/'source-before.json'))=={'job','binding','clock','claims'}
for a,b in [('inputs-before.json','inputs-after-actual.json'),('inputs-second-source.json','inputs-after-second-actual.json')]:assert read(E/a)['inputs']==read(E/b)['inputs']
page=read(P/'page-result.json');proof=read(P/'proof.json');info=read(P/'info.json');http=read(P/'page-http.json')
assert page['status']==proof['status']=='PASS';assert not page['page_errors'] and page['worker_calls']==1
assert (len(page['checks']),len(page['actions']),len(page['requests']),len(page['static_resource_loads']),page['boots'],len(page['downloads']),len(http))==(93,29,72,54,2,4,126)
for row in http:
 rb=row['response_text'].encode(); assert row['response_bytes']==len(rb) and row['response_sha256']==sha(rb)
 body=(row.get('body_text') or '').encode(); assert row['body_bytes']==len(body) and row['body_sha256']==sha(body)
raw_http=[]
for q in sorted((P/'http').glob('*-metadata.json')):
 m=read(q);raw=(P/m['response_file']).read_bytes();assert len(raw)==m['response_bytes'] and sha(raw)==m['response_sha256']
 b=read(q.with_name(q.name.replace('-metadata.json','-request-bytes.json')));wire=(P/b['path']).read_bytes();assert len(wire)==b['bytes'] and sha(wire)==b['sha256'];raw_http.append(m)
assert len(raw_http)==160
for req in page['requests']:
 row=one(http,lambda x:x['rpc_id']==req['rpc_id']);assert row['method']==req['method'] and row['path']==req['path'] and row['status']==req['status'] and row['response_sha256']==req['response_text_utf8_sha256']
posts=[x for x in page['requests'] if x['method']=='POST'];assert len(posts)==2 and {x['path'].split('/')[-1] for x in posts}=={'pb-use-reviews','pb-use-runs'}
assets=page['static_resource_loads'];expected={'/','/app.css',*re.findall(r'<script[^>]+src="([^"]+)"',(R/'src/sim2act/web/index.html').read_text())};assert len(expected)==27
for boot in [1,2]: assert {x['path'] for x in assets if x['boot']==boot}==expected and sum(x['boot']==boot for x in assets)==27
for a in assets:
 raw=(R/'src/sim2act/web'/(a['path'].lstrip('/') or 'index.html')).read_bytes(); assert a['status']==200 and a['sha256']==sha(raw) and a['bytes']==len(raw)
downloads=[]
assert {(x['run_id'],x['result_version'],x['format']) for x in page['downloads']}=={(page['v1_run'],1,'json'),(page['v1_run'],1,'md'),(page['v2_run'],2,'json'),(page['v2_run'],2,'md')}
for d in page['downloads']:
 row=one(http,lambda x:x['rpc_id']==d['artifact_rpc_id']);a=row['response']; req=page['requests'][d['artifact_request_index']]
 assert row['method']=='GET' and row['status']==200 and req['rpc_id']==row['rpc_id'] and row['path']==d['artifact_path']==f"/api/internal/app-run-jobs/{d['run_id']}/spec-artifact"
 assert row['response_sha256']==d['artifact_get_sha256'] and a['run_id']==d['run_id'] and a['result_version']==d['result_version'] and a['instance_id']==info['instance'] and a['app_id']==info['app'] and a['release_id']==info['release']
 assert a['resource']['resource_id']==d['resource_id'] and a['owner_acceptance']=='PENDING' and a['semantic_status']=='UNKNOWN' and a['semantic_goal_acceptance']=='NOT_RUN' and not a['formal_publication_enabled']
 content=a['resource']['content'] if d['format']=='json' else a['markdown_view'];raw=content.encode(); assert bytes.fromhex(d['blob_utf8_hex'])==raw and d['blob_bytes']==len(raw) and d['blob_utf8_sha256']==sha(raw)
 assert (P/'page-result.json.downloads'/d['name']).read_bytes()==raw
 resource=a['resource']['content'].encode();assert d['resource_content_sha256']==sha(resource); payload=json.loads(resource)
 assert resource==canon(payload) and payload['owner_acceptance']=='PENDING' and payload['semantic_goal_acceptance']=='NOT_RUN'
 assert payload['source_content']==info['v1_content' if d['result_version']==1 else 'v2_content'] and payload['source']['resource_id']==info['v1_resource' if d['result_version']==1 else 'v2_resource']
 assert payload['source_content'] in a['markdown_view'] and d['type']==('application/json;charset=utf-8' if d['format']=='json' else 'text/markdown;charset=utf-8')
 downloads.append(dict(name=d['name'],run_id=d['run_id'],result_version=d['result_version'],format=d['format'],bytes=len(raw),sha256=sha(raw),artifact_response_sha256=row['response_sha256']))
assert read(P/'page-result.json.downloads.json')==page['downloads']
workers=read(P/'business-workers.json');wires=read(P/'stage-wires.json');assert {k:len(v) for k,v in wires.items()}=={'generation':3,'source':1,'pb-v1':1,'pb-v2':1}
assert len(workers)==3 and {x['phase'] for x in workers}=={'source','pb-v1','pb-v2'}
for w in workers:
 assert w['claims']==w['worker_calls']==w['mock_requests']==1 and w['status']=='SUCCEEDED' and w['accepted_clock_unchanged'] and w['test_clock_or_lease_mutations']==0
 h=read(P/(w['phase']+'-claims-finally.json'));assert len(h['claims'])==1 and h['claims'][0]['kind']=='CLAIMED'
 assert h['claims'][0]['run_id']==w['run_id']
initial=read(P/'v2-before-page.json');completed=read(P/'v2-after-worker.json');final=read(P/'final-rows.json');assert final==completed
allowed={'runs','run_contracts','internal_app_runs','internal_run_bindings','delivery_graph_requests','events','grants','resources','internal_instances','internal_instance_data','operations','operation_intents','local_effects','attempts','reservations','heartbeats'}
def added(t):
 assert all(x in final[t] for x in initial[t]),t
 return [x for x in final[t] if x not in initial[t]]
for t in initial:
 if t not in allowed:assert initial[t]==final[t],t
for t in allowed-{'internal_instances'}:added(t)
old={x['id']:x for x in initial['internal_instances']};assert len(final['internal_instances'])==len(old)
for x in final['internal_instances']:assert x==({**old[x['id']],'data_version':2} if x['id']==info['instance'] else old[x['id']])
rid=page['v2_run'];run=added('runs');assert len(run)==1 and run[0]['id']==rid and run[0]['status']=='SUCCEEDED'
for t,n in [('internal_app_runs',1),('run_contracts',1),('internal_run_bindings',1),('internal_instance_data',1),('resources',1),('grants',3),('operations',4),('operation_intents',4),('local_effects',1),('attempts',1),('reservations',1),('heartbeats',1),('delivery_graph_requests',10)]:assert len(added(t))==n,(t,len(added(t)))
typed=added('internal_instance_data')[0];assert typed['version']==2 and typed['instance_id']==info['instance'] and typed['fingerprint']==fp(typed['data'])
artifact=added('resources')[0];assert artifact['format']=='json' and sha(artifact['content'].encode())==artifact['hash']
g=added('grants');assert {(x['principal_id'],x['resource_id'],x['tool_ref'],x['revoked']) for x in g}=={(info['runtime'],info['v2_resource'],'resource.read',False),(info['runtime'],artifact['id'],'resource.read',False),(info['principal'],artifact['id'],'resource.read',False)}
ops=added('operations');assert all(x['run_id']==rid and x['status']=='VERIFIED' for x in ops);assert {x['operation_id'] for x in added('operation_intents')}=={x['id'] for x in ops}
events=added('events');assert all(x['run_id']==rid for x in events)
at=added('attempts')[0];aid=at['id'];assert at['run_id']==rid and at['status']=='VERIFIED';journal=added('delivery_graph_requests');use=one(journal,lambda x:x['kind']=='pb_natural_use');key=use['request_key']
expected={(info['instance'],info['principal'],k,key) for k in ['pb_natural_use','pb_natural_use_seal']}|{(rid,info['principal'],k,'accepted') for k in ['pa_spec_run_scope','pa_spec_run_scope_seal','pb_natural_use_scope','pb_natural_use_scope_seal']}|{(rid,info['principal'],k,aid) for k in ['natural_source_request_body.v1','natural_source_request_body.v1_seal','natural_source_response_body.v1','natural_source_response_body.v1_seal']}
assert {(x['app_id'],x['principal_id'],x['kind'],x['request_key']) for x in journal}==expected
for x in journal:assert x['fingerprint']==fp(x['snapshot']) and x['request_fingerprint']==fp(x['snapshot']['request'])
for kind in ['pa_spec_run_scope','pb_natural_use_scope','pb_natural_use','natural_source_request_body.v1','natural_source_response_body.v1']:
 pair=[x for x in journal if x['kind'] in [kind,kind+'_seal']];assert len(pair)==2 and pair[0]['snapshot']==pair[1]['snapshot']
for kind,phase,ev in [('natural_source_request_body.v1','RESERVED_REQUEST','NS_WIRE_ARCHIVED'),('natural_source_response_body.v1','RECEIVED_DECODED_BODY','NS_BODY_ARCHIVED')]:
 body=one(journal,lambda x:x['kind']==kind)['snapshot'];assert body['request']==body['response'];body=body['request']
 assert set(body)=={'version','run_id','attempt_id','principal_id','project_id','runtime_id','phase','provenance','byte_count','sha256','received_complete','extent','omission','body_b64','canonical_sha256'}
 assert body['version']=='natural-source-body-archive.v1' and body['run_id']==rid and body['attempt_id']==aid and body['principal_id']==info['principal'] and body['project_id']==info['project'] and body['runtime_id']==info['runtime'] and body['phase']==phase and body['provenance']=='OFFLINE_MOCKTRANSPORT' and body['received_complete'] is True and body['extent']=='COMPLETE_BODY' and body['omission']=='NONE'
 raw=base64.b64decode(body['body_b64'],validate=True);assert 0<len(raw)==body['byte_count']<=32768 and sha(raw)==body['sha256'] and base64.b64encode(raw).decode()==body['body_b64']
 if phase=='RESERVED_REQUEST':assert at['parameters']['natural_spec_wire']==dict(sha256=sha(raw),bytes=len(raw),characters=len(raw.decode())) and json.loads(raw)==wires['pb-v2'][0]
 else:
  canonical=json.dumps(json.loads(raw),ensure_ascii=True,allow_nan=False,separators=(',',':')).encode('ascii');assert canonical==at['response']['received_raw'].encode('ascii') and at['response']['raw_evidence']==dict(status='COMPLETE',bytes=len(canonical),sha256=sha(canonical)) and body['canonical_sha256']==sha(canonical)
 assert [x['data'] for x in events if x['kind']==ev and x['data'].get('attempt_id')==aid]==[dict(attempt_id=aid,archive_fingerprint=fp(body))]
v1=[x['response'] for x in http if x['path'].endswith('/'+page['v1_run']+'/spec-owner-review') and x['status']==200 and x['after_page_worker']];v2=[x['response'] for x in http if x['path'].endswith('/'+rid+'/spec-owner-review') and x['status']==200 and x['after_page_worker']]
assert v1 and v2 and all(x['owner_acceptance']=='STALE' and not x['content_access'] and not x.get('current') and not x.get('record') and x['history']==info['v1_history'] for x in v1)
assert all(x['owner_acceptance']=='PENDING' and x['content_access'] and x['sequence']==0 and x['history']==[] and x['current']['run_id']==rid and x['current']['source_goal']['card_id']==info['v2_goal'] for x in v2)
late=page['late_run_switch'];h=one(http,lambda x:x['rpc_id']==late['held_rpc_id']);assert h['status']==200 and h['response_sha256']==late['held_http_body_sha256'] and late['held_run']==page['v1_run'] and late['selected_run']==rid and late['owner1_reads_before']==late['owner1_reads_after']
assert len(read(P/'checkpoints.json'))==6 and all(x['all_expected_rows_verified'] for x in read(P/'checkpoints.json'))
junit=[]
for n in ['actual','actual-final','actual-complete','synthetic','synthetic-final']:
 c=list(ET.parse(E/(n+'-junit.xml')).getroot().iter('testcase'));assert len(c)==1;failed=c[0].find('failure') is not None or c[0].find('error') is not None;junit.append(dict(name=n,node=c[0].attrib,status='FAIL' if failed else 'PASS'))
assert [x['status'] for x in junit]==['FAIL','FAIL','PASS','FAIL','PASS']
result=dict(status='LIMITED_INDEPENDENT_FILE_AUDIT_PASS',source=SHA,reviewer_product_execution=0,db_queries=0,inputs=687,production=133,all_three_actual_runs_zero_input_drift=True,direct_source_after_subset=141,source_before_collision='Preserved Run header; pre-execution 687 map is independent authority',junit=junit,actual_counts=dict(checks=93,actions=29,pageAPI=72,assets=54,boots=2,pageHTTP=126,allHTTP=160,pagePOST=2),download_bytes=downloads,model_mock_requests={k:len(v) for k,v in wires.items()},business_workers=workers,page_worker=1,real_model=0,all_original_rows_preserved_except_instance_data_version=True,new_events=dict(count=len(events),kinds=dict(collections.Counter(x['kind'] for x in events))),new_journal=10,all_event_run_ids_exact=True,owner_v1='STALE_METADATA_ONLY',owner_v2='PENDING_SEQUENCE0_NO_INHERITANCE',late_response='ACTUAL_GET200_CONTROLLED_CLIENT_DELIVERY_NO_REPAINT',artifact_hashes={str(q.relative_to(E)):dict(bytes=q.stat().st_size,sha256=sha(q.read_bytes())) for q in sorted(E.rglob('*')) if q.is_file() and not q.is_symlink() and q.suffix!='.db' and not any(x.is_symlink() for x in q.parents if x!=E)})
(O/'final-pure-artifact-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['artifact_hashes','business_workers','junit']},ensure_ascii=False,indent=2))
