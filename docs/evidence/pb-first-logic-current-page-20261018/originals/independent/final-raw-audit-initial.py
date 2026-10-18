"""Independent pure-file/Git audit; no product imports, DB opens, HTTP or model."""
from pathlib import Path
from collections import Counter
import ast, base64, copy, hashlib, json, subprocess, xml.etree.ElementTree as ET
R=Path('/workspace/pb-first-logic-current-page-evidence-20261018')
C=R/'actual-tmp/test_first_pb_local_logic_chan0'
O=Path('/workspace/pb-first-logic-current-page-independent-20261018')
REPO=Path('/workspace/Sim2Act')
FREEZE='459abcce146ed877ed8f893f3b06d10362cc7237'
BASE='e73004e3529ebfdc27e0105a33f888dbcf042543'
OLD='2fa76ff2458d3b732f1c18c000a51b4e9171d87b'
def load(p):return json.loads(p.read_text())
def sha(b):return hashlib.sha256(b).hexdigest()
def canonical(v):return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
def fp(v):return sha(canonical(v))
def git(*args):return subprocess.check_output(['git','-c','core.fsmonitor=false',*args],cwd=REPO)
def one(values,label):
 assert len(values)==1,(label,len(values))
 return values[0]
def newrows(before,after,table):
 assert all(row in after[table] for row in before[table]),table
 return [row for row in after[table] if row not in before[table]]
def pairs(before,after,expected):
 rows=newrows(before,after,'delivery_graph_requests')
 assert len(rows)==len(expected)*2
 assert {(r['app_id'],r['kind'],r['request_key']) for r in rows}=={(a,k+s,q) for a,k,q in expected for s in ('','_seal')}
 for a,k,q in expected:
  left=one([r for r in rows if (r['app_id'],r['kind'],r['request_key'])==(a,k,q)],'metadata')
  right=one([r for r in rows if (r['app_id'],r['kind'],r['request_key'])==(a,k+'_seal',q)],'seal')
  assert left['snapshot']==right['snapshot']
  assert left['fingerprint']==right['fingerprint']==fp(left['snapshot'])
  assert left['request_fingerprint']==right['request_fingerprint']==fp(left['snapshot']['request'])
 return rows
before=load(R/'inputs-fourth-before.json');after=load(R/'inputs-after.json');oldinputs=load(R/'inputs-before.json')
assert before['head']==after['head']==FREEZE and before['inputs']==after['inputs']
assert before['input_count']==len(before['inputs'])==691
prod={p:v for p,v in before['inputs'].items() if p.startswith('src/')}
assert len(prod)==before['production_count']==133
assert git('rev-parse','HEAD').decode().strip()==FREEZE
for p,v in before['inputs'].items():
 b=(REPO/p).read_bytes();assert {'bytes':len(b),'sha256':sha(b)}==v,p
for p,v in prod.items():
 for revision in (BASE,OLD,FREEZE):
  b=git('show',revision+':'+p);assert {'bytes':len(b),'sha256':sha(b)}==v,(revision,p)
changed=sorted(p for p in before['inputs'] if before['inputs'][p]!=oldinputs['inputs'][p])
assert changed==['tests/test_pa_natural_spec_ui.py','tests/test_pb_first_logic_current_page_ui.py']
direct=load(C/'source-before.json');assert direct==load(C/'source-after.json') and len(direct)==141
assert all(before['inputs'][p]==v for p,v in direct.items())
a=ast.parse(git('show',OLD+':tests/test_pb_first_logic_current_page_ui.py'))
b=ast.parse((REPO/'tests/test_pb_first_logic_current_page_ui.py').read_text())
asserts=lambda tree:[ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,ast.Assert)]
assert asserts(a)==asserts(b)
execution=load(R/'execution.json');rootxml=ET.parse(R/'actual-junit.xml').getroot();cases=rootxml.findall('.//testcase')
assert execution['head']==FREEZE and execution['exit_code']==0 and '1500s' in execution['command']
assert len(cases)==1 and cases[0].get('name')=='test_first_pb_local_logic_change_checks_then_versions_and_uses_third_on_current_page'
assert not cases[0].findall('failure') and not cases[0].findall('error') and not cases[0].findall('skipped')
page=load(C/'page-result.json');proof=load(C/'proof.json');wire=load(C/'page-http.json');events=[json.loads(x) for x in (C/'progress.jsonl').read_text().splitlines()]
assert page['status']==proof['status']=='PASS' and not page['error'] and not page['page_errors']
assert len(page['checks'])==92 and len(page['actions'])==36 and len(page['requests'])==119 and len(wire)==173
assert page['boots']==2 and len(page['static_resource_loads'])==54
assert page['downloads']==page['owner_decision']==0 and not page['fault_injections']
assert proof['real_model_requests']==0 and proof['product_clock_lease_deadline_budget_mutations']==0
responses=[e for e in events if e['kind']=='http_response_saved'];assert len(responses)==204
for e in responses:
 raw=(C/e['response_file']).read_bytes();assert len(raw)==e['response_bytes'] and sha(raw)==e['response_sha256']
for row in wire:
 raw=(row.get('body_text') or '').encode();assert len(raw)==row['body_bytes'] and sha(raw)==row['body_sha256']
 if row.get('body_text') is not None:assert json.loads(raw)==row['body']
 raw=row['response_text'].encode();assert len(raw)==row['response_bytes'] and sha(raw)==row['response_sha256']
 assert one([e for e in responses if e['rpc_id']==row['rpc_id'] and e['path']==row['path'] and e['method']==row['method']],'wire receipt')['response_sha256']==row['response_sha256']
for row in page['requests']:
 actual=one([x for x in wire if x['rpc_id']==row['rpc_id']],'page API actual')
 assert (actual['method'],actual['path'],actual['status'])==(row['method'],row['path'],row['status'])
 assert sha(row['response_text'].encode())==row['response_text_utf8_sha256']==actual['response_sha256']
assets=page['static_resource_loads'];assert Counter(x['boot'] for x in assets)=={1:27,2:27}
for asset in assets:
 raw=(REPO/'src/sim2act/web'/(asset['path'].lstrip('/') or 'index.html')).read_bytes()
 assert asset['status']==200 and len(raw)==asset['bytes'] and sha(raw)==asset['sha256']
 actuals=[x for x in wire if x['path']==asset['path'] and x['response_sha256']==asset['sha256']]
 assert len(actuals)==2
posts=[x for x in wire if x['method']=='POST'];assert len(posts)==7
assert [x['status'] for x in posts]==[201,202,201,200,201,200,202]
assert [x['path'].rsplit('/',1)[-1] for x in posts]==['previews','checks','version-approvals','commit','instances','pb-use-reviews','pb-use-runs']
assert len(list(C.glob('after-page-post-*.json')))==7
checkpoints=load(C/'checkpoints.json');assert len(checkpoints)==7
initial=load(C/'page-seed-baseline.json');final=load(C/'final-rows.json');snapshots=[]
for cp in checkpoints:
 snapshot=load(C/('checkpoint-'+cp['phase']+'-rows.json'));snapshots.append(snapshot)
 assert cp['all_expected_rows_verified'] is True and fp(snapshot)==cp['full_table_fingerprint']
 assert snapshot.keys()==initial.keys() and all(all(row in snapshot[t] for row in rows) for t,rows in initial.items())
assert snapshots[0]==initial and snapshots[-1]==snapshots[-2]==final
assert len(initial)==55
for post in posts:
 snapshot=load(C/('after-page-post-'+str(post['rpc_id'])+'.json'))
 assert all(all(row in snapshot[t] for row in rows) for t,rows in initial.items())
# Preview changes only a metadata pair; no execution/publication or business row.
previewafter=load(C/('after-page-post-'+str(posts[0]['rpc_id'])+'.json'))
assert all(initial[t]==previewafter[t] for t in initial if t!='delivery_graph_requests')
preview=page['preview'];key=page['logic_key'];info=load(C/'info.json');state=load(C/'bridge-state.json')
pairs(initial,previewafter,{(info['old_instance'],'natural-local-logic.v1.preview',key)})
assert preview['preview_fingerprint']==fp({k:v for k,v in preview.items() if k!='preview_fingerprint'})
assert preview['effective_fingerprint']==fp(preview['effective_candidate'])
effective=preview['effective_candidate'];original=info['original_candidate']
assert effective['manifest']['revision']==2 and effective['actions'][2]['revision']==2
assert len(effective['actions'])==6 and len(preview['preserved_action_definitions'])==5
assert [x['action_id'] for x in effective['actions']]==[x['action_id'] for x in original['actions']]
assert all(effective['actions'][i]==original['actions'][i] for i in [0,1,3,4,5])
recipe=copy.deepcopy(effective['spec_recipe']);oldrecipe=original['spec_recipe'];changedstep=recipe['steps'][2];prior=recipe['steps'][1]
assert changedstep['inputs'].pop('prior_items')=={'source':'step','ref':prior['step_id'],'field':'items'}
assert changedstep['inputs'].pop('prior_feedback')=={'source':'step','ref':prior['step_id'],'field':'feedback'}
changedstep['depends_on']=oldrecipe['steps'][2]['depends_on'];assert recipe==oldrecipe
assert preview['impact']['revalidation_scope']=='APP' and preview['semantic_status']=='UNKNOWN' and preview['owner_acceptance']=='PENDING'
assert page['approval']['snapshot']==page['new_release']['snapshot']
assert page['new_release']['snapshot']['draft']==info['original_release_value']['snapshot']['draft']
assert page['new_release']['fingerprint']==fp(page['new_release']['snapshot'])
assert page['new_release']['snapshot']['natural_logic_source']['namespace']=='natural-local-logic.v1'
assert page['new_release']['snapshot']['natural_logic_source']['preview_key']==key
# Pure saved-row validation of queue6, completed14 including exact sealed durable bodies.
wires=load(C/'stage-wires.json');assert {k:len(v) for k,v in wires.items()}=={'generation':3,'source-original':2,'pb-original':2,'logic-check':2,'logic-use':2}
workers=load(C/'business-workers.json');assert len(workers)==4
body_archives=0
for kind,postindex in [('check',1),('use',6)]:
 phase='logic-'+kind;queued=load(C/('after-page-post-'+str(posts[postindex]['rpc_id'])+'.json'));pre=state[kind+'_before'];completed=load(C/(kind+'-after-worker.json'))
 expected={tuple(x) for x in state[kind+'_queue_expected']};assert len(pairs(pre,queued,expected))==6
 rid=state[kind+'_accepted']['run_id'];attempts=sorted(newrows(pre,completed,'attempts'),key=lambda row:row['parameters']['natural_spec']['ordinal'])
 assert len(attempts)==2 and all(x['run_id']==rid and x['status']=='VERIFIED' for x in attempts)
 archivekinds=['natural_source_request_body.v1','natural_source_response_body.v1']
 allpairs=expected|{(rid,k,a['id']) for k in archivekinds for a in attempts}
 rows=pairs(pre,completed,allpairs);assert len(rows)==14
 for index,attempt in enumerate(attempts):
  for ak in archivekinds:
   row=one([x for x in rows if x['kind']==ak and x['request_key']==attempt['id']],'archive');v=row['snapshot']['request']
   assert v==row['snapshot']['response'] and v['version']=='natural-source-body-archive.v1'
   assert v['run_id']==rid and v['attempt_id']==attempt['id'] and v['provenance']=='OFFLINE_MOCKTRANSPORT'
   assert v['received_complete'] and v['extent']=='COMPLETE_BODY' and v['omission']=='NONE'
   raw=base64.b64decode(v['body_b64'],validate=True);assert len(raw)==v['byte_count'] and sha(raw)==v['sha256']
   if ak==archivekinds[0]:assert json.loads(raw)==wires[phase][index] and v['sha256']==attempt['parameters']['natural_spec_wire']['sha256']
   else:
    encoded=json.dumps(json.loads(raw),ensure_ascii=True,allow_nan=False,separators=(',',':')).encode('ascii')
    assert encoded==attempt['response']['received_raw'].encode('ascii') and sha(encoded)==v['canonical_sha256']
   body_archives+=1
 operations=newrows(pre,completed,'operations');requirements=one([x for x in operations if x['tool_ref']=='model.spec.requirements'],'actual prior receipt')
 current=json.loads(wires[phase][1]['messages'][1]['content'])['current_inputs']
 assert current['prior_items']==requirements['receipt']['data']['items'] and current['prior_feedback']==requirements['receipt']['data']['feedback']
 assert current['content']==(info['old_content'] if kind=='check' else info['target_content'])
# The first successful CHECK read is the sole intervening sealed metadata pair.
pairs(load(C/'check-after-worker.json'),snapshots[2],{(info['old_instance'],'natural-local-logic.v1.checked',key)})
for worker in workers:
 phase=worker['phase'];start=load(C/(phase+'-before.json'));end=load(C/(phase+'-finally.json'))
 assert worker['worker_calls']==worker['claims']==1 and worker['mock_requests']==2 and worker['status']=='SUCCEEDED'
 assert start['job']['status']=='QUEUED' and end['job']['status']=='SUCCEEDED' and start['clock']==end['clock']
 assert start['job']['created_at']==end['job']['created_at'] and end['clock']['deadline']-start['job']['created_at']==300
 assert worker['test_clock_lease_deadline_mutations']==0
# Typed projections and instance identities are distinct; all are result version1.
dimensions=page['run_dimensions'];assert len({x['instance_id'] for x in dimensions.values()})==len({x['run_id'] for x in dimensions.values()})==3
for dimension in dimensions.values():
 typed=one([x for x in final['internal_instance_data'] if x['instance_id']==dimension['instance_id']],'typed projection')
 assert typed['version']==dimension['result_version']==1 and typed['release_id']==dimension['release_id']
assert dimensions['original_business']['release_id']==dimensions['isolated_check']['release_id']!=dimensions['new_logic_business']['release_id']
assert len(page['viewed_results'])==2
coldviews=[]
for view in page['viewed_results']:
 row=one([x for x in wire if x['rpc_id']==view['artifact_rpc_id']],'cold actual HTTP')
 pr=page['requests'][view['artifact_request_index']];value=row['response']
 assert pr['rpc_id']==row['rpc_id'] and pr['boot']==2 and row['cold_readonly'] and row['status']==200 and row['method']=='GET'
 assert row['path']=='/api/internal/app-run-jobs/'+view['run_id']+'/spec-artifact' and row['response_sha256']==view['artifact_get_sha256']
 assert all(value[k]==view[k] for k in ('instance_id','run_id','release_id','result_version','output_fingerprint'))
 resource=value['resource'];assert resource['resource_id']==view['resource_id'] and sha(resource['content'].encode())==view['resource_content_sha256']
 checklist=json.loads(resource['content']);assert checklist['source']['resource_id']==view['source_resource_id']
 assert checklist['source_content']==(info['old_content'] if view['run_id']==info['old_run'] else info['target_content'])
 coldviews.append({k:view[k] for k in ('run_id','instance_id','release_id','result_version','artifact_rpc_id','artifact_get_sha256','resource_content_sha256')})
owner=[x for x in wire if x['path'].endswith('/spec-owner-review')]
assert owner and all(x['method']=='GET' and x['response']['sequence']==0 and x['response']['owner_acceptance']=='PENDING' and x['response']['latest'] is None for x in owner)
assert not final['natural_owner_records'] and not final['natural_owner_seals']
newgrants=newrows(initial,final,'grants');assert len(newgrants)==5 and all(x['tool_ref']=='resource.read' for x in newgrants)
assert initial['app_drafts']==final['app_drafts'] and initial['principals']==final['principals']
assert len(newrows(initial,final,'internal_releases'))==1 and len(newrows(initial,final,'internal_instances'))==2
assert events[-1]['kind']=='test_end' and events[-1]['passed'] is True and events[-1]['watchdog_fired'] is False and events[-1]['node_exit_code']==0
assert one([e for e in events if e['kind']=='test_start'],'test start')['watchdog_seconds']==1200
# Prior attempts already independently audited; do not repeat their products or old matrix.
prior_reports=[load(O/n) for n in ['first-interruption-review.json','second-timeout-review.json','third-watchdog-review.json']]
summary=load(R/'qualification-summary.json')
assert summary['unique_pytest_nodes']==1 and summary['executions']==4 and summary['successful_executions']==1
assert summary['junit_completed_executions']==2 and summary['exited_executions']==3 and summary['failed_executions']==2
assert summary['all_rounds_mock_requests']==9+11+11+sum(map(len,wires.values()))==42
result={'status':'PASS_LIMITED_INDEPENDENT_PURE_FILE_AUDIT','product_execution_by_reviewer':False,'database_open_or_sql':False,'http_model_network':False,
 'source':FREEZE,'baseline':BASE,'production_git_blob_checks':len(prod)*3,'production_files':len(prod),'execution_inputs':len(before['inputs']),'direct_inputs':len(direct),'input_drift':[], 'cross_freeze_changed_inputs':changed,'unchanged_business_assert_asts':len(asserts(a)),
 'junit':{'unique_node':cases[0].get('name'),'pass':1,'seconds':float(cases[0].get('time'))},'execution_exit':0,'execution_seconds':execution['duration_seconds'],
 'counts':{'checks':len(page['checks']),'actions':len(page['actions']),'api':len(page['requests']),'page_http':len(wire),'all_http_response_raw_hashes_verified':len(responses),'assets':len(assets),'boots':page['boots'],'posts':len(posts),'full_table_checkpoints':len(checkpoints),'snapshot_table_count':len(initial),'saved_durable_request_response_bodies_verified':body_archives,'mock_wires':sum(map(len,wires.values())),'business_stages':len(workers),'business_claims':sum(x['claims'] for x in workers),'page_worker_commands':page['worker_calls']},
 'post_statuses':[x['status'] for x in posts],'model_mock_counts':{k:len(v) for k,v in wires.items()},'run_dimensions':dimensions,'cold_artifact_views':coldviews,
 'all_seed_rows_preserved_at_all_checkpoints_and_posts':True,'cold_full_table_unchanged':True,'queue_journal_rows_each':6,'completed_journal_rows_each':14,'first_check_success_get_adds_metadata_rows':2,'owner_get_count':len(owner),'owner_state':'PENDING sequence0, no DECIDE/PREPARE','derived_read_grants':len(newgrants),
 'attempts':{'unique':1,'attempts':4,'successful':1,'junit_terminal':2,'known_exit':3,'environment_unknown':1,'timeout_exit124':1,'broken_pipe_exit1':1,'all_saved_mock_wires':42},
 'scope':'Independent non-author source review and immutable file/Git recalculation, not independently executed product qualification. One finite first P-B dependency adjustment; no general R0/R1/R2 or whole AT qualification uplift.'}
(O/'final-raw-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result,ensure_ascii=False,indent=2))
