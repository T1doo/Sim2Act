"""Stdlib-only closed artifact audit; no application imports, SQL, HTTP or workers."""
import base64,collections,hashlib,json,re,subprocess
import xml.etree.ElementTree as ET
from pathlib import Path
R=Path('/workspace/Sim2Act');E=Path('/workspace/pa-current-unseen-flow-evidence-20261018');O=Path(__file__).parent;P=E/'actual-tmp/test_pa_saved_unseen_input_aft0';REV='fddccd09a72d628cdb0ea382009c84545a29cb9f'
def read(q):return json.loads(q.read_text())
def sha(x):return hashlib.sha256(x).hexdigest()
def canonical(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def fp(x):return sha(canonical(x))
def one(rows,test):
 matches=[x for x in rows if test(x)];assert len(matches)==1,len(matches);return matches[0]
before=read(E/'inputs-before.json');after=read(E/'inputs-after.json');assert before['inputs']==after['inputs'] and len(before['inputs'])==689
assert before['head']==REV and sum(x.startswith('src/sim2act/') for x in before['inputs'])==133
for name,m in before['inputs'].items():
 raw=(R/name).read_bytes();assert m==dict(bytes=len(raw),sha256=sha(raw))
source_before=read(P/'source-before.json');source_after=read(P/'source-after.json');assert source_before==source_after and len(source_after)==141
for name,m in source_after.items():assert before['inputs'][name]==m
xml=ET.parse(E/'actual-junit.xml');cases=list(xml.getroot().iter('testcase'));assert len(cases)==1 and cases[0].find('failure') is None and cases[0].find('error') is None
execution=read(E/'execution.json');assert execution['head']==REV and execution['exit_code']==0
page=read(P/'page-result.json');info=read(P/'info.json');proof=read(P/'proof.json');http=read(P/'page-http.json');workers=read(P/'business-workers.json');wires=read(P/'stage-wires.json')
assert page['status']==proof['status']=='PASS' and not page['page_errors'] and page['downloads']=='NOT_EXERCISED' and page['fault_injections']=='NONE'
assert (len(page['checks']),len(page['actions']),len(page['requests']),len(page['static_resource_loads']),page['boots'],len(http),page['worker_calls'])==(86,71,72,54,2,126,1)
for h in http:
 body=(h.get('body_text') or '').encode();assert h['body_bytes']==len(body) and h['body_sha256']==sha(body) and h['response_sha256']==sha(h['response_text'].encode())
for h in page['requests']:
 raw=one(http,lambda x:x['rpc_id']==h['rpc_id']);assert raw['method']==h['method'] and raw['path']==h['path'] and raw['status']==h['status'] and raw['response_sha256']==h['response_text_utf8_sha256']
raw_http=[]
for q in sorted((P/'http').glob('*-metadata.json')):
 m=read(q);raw=(P/m['response_file']).read_bytes();assert len(raw)==m['response_bytes'] and sha(raw)==m['response_sha256']
 b=read(q.with_name(q.name.replace('-metadata.json','-request-bytes.json')));raw=(P/b['path']).read_bytes();assert len(raw)==b['bytes'] and sha(raw)==b['sha256'];raw_http.append(m)
assert len(raw_http)==148
assets=page['static_resource_loads'];expected={'/','/app.css',*re.findall(r'<script[^>]+src="([^"]+)"',(R/'src/sim2act/web/index.html').read_text())};assert len(expected)==27
for boot in [1,2]:assert len([x for x in assets if x['boot']==boot])==27 and {x['path'] for x in assets if x['boot']==boot}==expected
for x in assets:
 raw=(R/'src/sim2act/web'/(x['path'].lstrip('/') or 'index.html')).read_bytes();assert x['status']==200 and x['bytes']==len(raw) and x['sha256']==sha(raw)
posts=[x for x in http if x['method']=='POST'];assert len(posts)==5
owner_path=f"/api/internal/instances/{info['instance']}/runs/{info['v1_run']}/spec-owner-review";owner_posts=[x for x in posts if x['path']==owner_path+'-requests'];assert len(owner_posts)==2
owner=read(P/'simulated-owner-evidence.json');initial=read(P/'page-initial-rows.json');accepted=read(P/'v1-accepted-rows.json');queued=read(P/'v2-before-worker.json');completed=read(P/'v2-after-worker.json');final=read(P/'final-rows.json');assert completed==final
for table in initial:
 if table not in {'natural_owner_records','natural_owner_seals'}:assert initial[table]==accepted[table],table
assert not initial['natural_owner_records'] and not initial['natural_owner_seals'];assert len(accepted['natural_owner_records'])==len(accepted['natural_owner_seals'])==2
previous=''
for sequence,command,status in [(1,'PREPARE','PENDING'),(2,'DECIDE','ACCEPTED')]:
 row=one(accepted['natural_owner_records'],lambda x:x['sequence']==sequence);wire=one(owner_posts,lambda x:x['body']['command']==command)
 assert wire['status']==201 and wire['body']==owner['requests'][command] and row['request_fingerprint']==fp(wire['body']) and row['kind']==command and row['status']==status and row['previous_fingerprint']==previous
 assert row['run_id']==info['v1_run'] and row['instance_id']==info['instance'] and row['principal_id']==info['principal'] and row['project_id']==info['project']
 payload=row['payload'];assert payload['request']==wire['body'] and payload['contract']==owner['contract'] and row['fingerprint']==fp(payload)
 assert payload['metadata']=={k:v for k,v in row.items() if k not in {'payload','fingerprint'}}
 seal=one(accepted['natural_owner_seals'],lambda x:x['record_id']==row['id']);assert seal['run_id']==info['v1_run'] and seal['payload_fingerprint']==row['fingerprint'] and seal['metadata_fingerprint']==fp({k:v for k,v in row.items() if k!='payload'})
 previous=row['fingerprint']
decision=one(owner_posts,lambda x:x['body']['command']=='DECIDE')['body'];items=owner['contract']['items'];assert len(items)==len(decision['choices'])==20
assert [x['item_id'] for x in decision['choices']]==[x['id'] for x in items]
assert all(x['decision']=='ACCEPT' and x['reason']=='SIMULATED_TEST_ONLY: automated fixture gesture, NOT a real human semantic judgment; criterion '+x['item_id'] for x in decision['choices'])
assert page['simulated_owner_choices']==decision['choices'] and page['v1_accepted_history']==owner['history']
bad=one(posts,lambda x:x['path'].endswith('/pa-use-reviews') and x['body']['resource_id']==info['bad_resource']);assert bad['status']==400 and bad['response']['error']['code']=='INVALID_INPUT' and '2048' in bad['response']['error']['message']
assert len(info['bad_content'].encode())==2049 and info['bad_content'].isascii() and sha(info['bad_content'].encode())==info['bad_hash']
assert bad['body']['card_id']==info['bad_goal'] and bad['body']['expected_source_hash']==info['bad_hash']
badgoal=one(initial['goal_card_versions'],lambda x:x['card_id']==info['bad_goal'] and x['version']==bad['body']['expected_goal_version']);assert badgoal['snapshot']['content']['resource_refs']==[info['bad_resource']] and fp(badgoal['snapshot'])==bad['body']['expected_goal_fingerprint']
badproof=read(P/'oversized-preview-proof.json');assert badproof['request']==bad['body'] and badproof['response']==bad['response'] and badproof['status']==400 and badproof['all_tables_unchanged'] and badproof['new_mock_requests']==0
assert {k:len(v) for k,v in wires.items()}=={'generation':3,'pa-v1':1,'pa-v2':1}
assert len(workers)==2 and {x['phase'] for x in workers}=={'pa-v1','pa-v2'}
for x in workers:
 assert x['claims']==x['worker_calls']==x['mock_requests']==1 and x['status']=='SUCCEEDED' and x['accepted_clock_unchanged'] and x['test_clock_or_lease_mutations']==0
 h=read(P/(x['phase']+'-claims-finally.json'));assert len(h['claims'])==1 and h['claims'][0]['kind']=='CLAIMED' and h['claims'][0]['run_id']==x['run_id']
allowed={'runs','run_contracts','internal_app_runs','internal_run_bindings','delivery_graph_requests','events','grants','resources','internal_instances','internal_instance_data','operations','operation_intents','local_effects','attempts','reservations','heartbeats'}
def added(t,endpoint=final):
 assert all(x in endpoint[t] for x in accepted[t]),t
 return [x for x in endpoint[t] if x not in accepted[t]]
for t in accepted:
 if t not in allowed:assert final[t]==accepted[t],t
for t in allowed-{'internal_instances'}:added(t)
old={x['id']:x for x in accepted['internal_instances']};assert len(final['internal_instances'])==len(old)
for x in final['internal_instances']:assert x==({**old[x['id']],'data_version':2} if x['id']==info['instance'] else old[x['id']])
rid=page['v2_run'];run=added('runs');assert len(run)==1 and run[0]['id']==rid and run[0]['status']=='SUCCEEDED'
for t,n in [('internal_app_runs',1),('run_contracts',1),('internal_run_bindings',1),('internal_instance_data',1),('resources',1),('grants',3),('operations',4),('operation_intents',4),('local_effects',1),('attempts',1),('reservations',1),('heartbeats',1),('delivery_graph_requests',10)]:assert len(added(t))==n,(t,len(added(t)))
assert len(added('delivery_graph_requests',queued))==6
artifact=added('resources')[0];typed=added('internal_instance_data')[0];assert typed['version']==2 and typed['instance_id']==info['instance'] and typed['fingerprint']==fp(typed['data']) and typed['data']['result']['resource_id']==artifact['id']
assert json.loads(artifact['content'])['source_content']==info['v2_content'] and sha(artifact['content'].encode())==artifact['hash']
assert {(x['principal_id'],x['resource_id'],x['tool_ref'],x['revoked']) for x in added('grants')}=={(info['runtime'],info['v2_resource'],'resource.read',False),(info['runtime'],artifact['id'],'resource.read',False),(info['principal'],artifact['id'],'resource.read',False)}
assert all(x['run_id']==rid and x['status']=='VERIFIED' for x in added('operations'))
events=added('events');assert all(x['run_id']==rid for x in events)
at=added('attempts')[0];assert at['run_id']==rid and at['status']=='VERIFIED';aid=at['id'];journal=added('delivery_graph_requests');use=one(journal,lambda x:x['kind']=='pa_natural_use');key=use['request_key']
expected={(info['instance'],info['principal'],k,key) for k in ['pa_natural_use','pa_natural_use_seal']}|{(rid,info['principal'],k,'accepted') for k in ['pa_spec_run_scope','pa_spec_run_scope_seal','pa_natural_use_scope','pa_natural_use_scope_seal']}|{(rid,info['principal'],k,aid) for k in ['natural_source_request_body.v1','natural_source_request_body.v1_seal','natural_source_response_body.v1','natural_source_response_body.v1_seal']}
assert {(x['app_id'],x['principal_id'],x['kind'],x['request_key']) for x in journal}==expected
for x in journal:assert x['fingerprint']==fp(x['snapshot']) and x['request_fingerprint']==fp(x['snapshot']['request'])
for kind in ['pa_spec_run_scope','pa_natural_use_scope','pa_natural_use','natural_source_request_body.v1','natural_source_response_body.v1']:
 pair=[x for x in journal if x['kind'] in [kind,kind+'_seal']];assert len(pair)==2 and pair[0]['snapshot']==pair[1]['snapshot']
for kind,phase,ev in [('natural_source_request_body.v1','RESERVED_REQUEST','NS_WIRE_ARCHIVED'),('natural_source_response_body.v1','RECEIVED_DECODED_BODY','NS_BODY_ARCHIVED')]:
 d=one(journal,lambda x:x['kind']==kind)['snapshot'];assert d['request']==d['response'];d=d['request'];raw=base64.b64decode(d['body_b64'],validate=True)
 assert d['run_id']==rid and d['attempt_id']==aid and d['principal_id']==info['principal'] and d['project_id']==info['project'] and d['runtime_id']==info['runtime'] and d['phase']==phase and d['provenance']=='OFFLINE_MOCKTRANSPORT' and d['received_complete'] is True and d['extent']=='COMPLETE_BODY' and d['omission']=='NONE'
 assert 0<len(raw)==d['byte_count']<=32768 and sha(raw)==d['sha256'] and base64.b64encode(raw).decode()==d['body_b64']
 if phase=='RESERVED_REQUEST':assert at['parameters']['natural_spec_wire']==dict(sha256=sha(raw),bytes=len(raw),characters=len(raw.decode())) and json.loads(raw)==wires['pa-v2'][0] and d['canonical_sha256'] is None
 else:
  c=json.dumps(json.loads(raw),ensure_ascii=True,allow_nan=False,separators=(',',':')).encode('ascii');assert c==at['response']['received_raw'].encode('ascii') and at['response']['raw_evidence']==dict(status='COMPLETE',bytes=len(c),sha256=sha(c)) and d['canonical_sha256']==sha(c)
 assert [x['data'] for x in events if x['kind']==ev and x['data'].get('attempt_id')==aid]==[dict(attempt_id=aid,archive_fingerprint=fp(d))]
owner1=[x['response'] for x in http if x['path'].split('?',1)[0]==owner_path and x['status']==200 and x['after_page_worker']];owner2=[x['response'] for x in http if x['path'].split('?',1)[0]==f"/api/internal/instances/{info['instance']}/runs/{rid}/spec-owner-review" and x['status']==200 and x['after_page_worker']]
assert owner1 and owner2 and all(x['owner_acceptance']=='STALE' and not x['content_access'] and not x.get('current') and not x.get('record') and x['history']==owner['history'] for x in owner1)
assert all(x['owner_acceptance']=='PENDING' and x['content_access'] and x['sequence']==0 and not x['history'] and x['current']['run_id']==rid for x in owner2)
views=page['viewed_results'];assert len(views)==2 and {(x['run_id'],x['result_version']) for x in views}=={(info['v1_run'],1),(rid,2)}
for v in views:
 h=one(http,lambda x:x['rpc_id']==v['artifact_rpc_id']);d=h['response'];record=one(final['internal_instance_data'],lambda x:x['instance_id']==info['instance'] and x['version']==v['result_version']);output=record['data']['result']
 assert h['method']=='GET' and h['status']==200 and h['path']==f"/api/internal/app-run-jobs/{v['run_id']}/spec-artifact" and h['response_sha256']==v['artifact_get_sha256']
 assert d['run_id']==v['run_id'] and d['result_version']==v['result_version'] and d['instance_id']==info['instance'] and d['app_id']==info['app'] and d['release_id']==info['release'] and d['output_fingerprint']==v['output_fingerprint']==fp(output)
 assert d['resource']['content'].encode()==canonical(output['checklist']) and d['resource']['hash']==v['resource_content_sha256']==sha(d['resource']['content'].encode()) and output['checklist']['source_content']==info['v1_content' if v['result_version']==1 else 'v2_content'] and d['owner_acceptance']=='PENDING' and d['semantic_status']=='UNKNOWN' and not d['formal_publication_enabled']
phases=read(P/'checkpoints.json');assert len(phases)==7 and all(x['all_expected_rows_verified'] for x in phases)
assert {x['phase'] for x in phases}=={'seed-readonly','v1-simulated-owner-accepted','oversized-preview-rejected','v2-queued-before-worker','v2-complete-after-manual-refresh','cold-two-versions-readonly','final-readonly'}
result=dict(status='LIMITED_INDEPENDENT_CLOSED_FILE_AUDIT_PASS',freeze=REV,reviewer_product_execution=0,sql=0,pytest_identities=1,executions=1,failed_executions=0,junit=cases[0].attrib,outer_seconds=execution['duration_seconds'],inputs=689,production=133,direct_source_manifest=141,input_drift=0,actual_counts=dict(checks=86,actions=71,pageAPI=72,pageHTTP=126,assets=54,boots=2,allHTTP=148,pagePOST=5),owner_delta=dict(records=2,seals=2,choices=20,classification='SIMULATED_TEST_ONLY_NOT_REAL_SEMANTICS'),bad_input=dict(actual_bytes=2049,status=400,code='INVALID_INPUT',matching_saved_goal=True,actual_snapshot_equality_assertion_passed=True,independent_bad_before_after_snapshots='NOT_SEPARATELY_SERIALIZED; do not claim an independent pair of seven full raw snapshots'),models={k:len(v) for k,v in wires.items()},business_workers=workers,cold_artifact_views=views,new_events=dict(count=len(events),kinds=dict(collections.Counter(x['kind'] for x in events))),all_preserved_rows_exact=True,seven_actual_snapshot_checkpoint_assertions=phases,download_count=0,fault_injections='NONE',raw_file_inventory={str(q.relative_to(E)):dict(bytes=q.stat().st_size,sha256=sha(q.read_bytes())) for q in sorted(E.rglob('*')) if q.is_file() and not q.is_symlink() and q.suffix!='.db' and not any(z.is_symlink() for z in q.parents if z!=E)})
(O/'final-pa-pure-artifact-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['raw_file_inventory','business_workers']},ensure_ascii=False,indent=2))
