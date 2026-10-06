import hashlib,json,sys
from datetime import datetime
from pathlib import Path
import httpx
from sim2act.db import fingerprint
from sim2act.tools import definitions
p=Path('/workspace/Sim2Act-pb/docs/evidence/AT02-dual-live-20261006')
load=lambda name:json.loads((p/name).read_text())
r=load('results.json');w=load('wire.json');pre=load('preflight.json');fixture=load('fixture.json');t=r['final_trace'];start=pre['starting_fixture'];checks=[]
def check(name,ok):
 assert ok,name
 checks.append(name)
check('archived terminal and four send slots',r['status']=='PASS_BOUNDED_DUAL_LIVE_SLICE' and r['actual_send_slots']==4 and r['unused_authorized_slots']==0)
check('wire archive identical embedded ledger',w==r['wire'])
check('sequential AABB / no blocks or unknown sends', [x['sequence'] for x in w['requests']]==[1,2,3,4] and [x['group'] for x in w['requests']]==['A','A','B','B'] and not w['blocked'] and not w['halted'])
check('two owner/project/runtime identities',all(len({g[key] for g in fixture['groups']})==2 for key in ['owner_id','project_id','runtime_id','resource_id']))
check('no credentials archived in principal rows',all('token_hash' not in x for x in t['principals']))
check('grants and resource rows exactly unchanged',t['grants']==start['grants'] and t['resources']==start['resources'])
active=[x for x in t['grants'] if not x['revoked']]
check('only four resource-read grants',len(active)==4 and all(x['tool_ref']=='resource.read' for x in active))
check('preflight zero-send minimum role',pre['external_requests']==0 and pre['status']=='PASS' and not any(pre['minimum_role_flags'].values()))
check('all eight archived preflight cross-scope HTTP denials',len(pre['negative_http'])==8 and all(x['status']==403 for x in pre['negative_http']))
check('two runs four attempts two operations four reservations',len(t['runs'])==2 and len(t['attempts'])==4 and len(t['operations'])==2 and len(t['reservations'])==4)
check('single account quota intersection',len(t['quotas'])==1 and {x['subject'] for x in t['reservations']}=={t['quotas'][0]['subject']})
usage={k:0 for k in ['prompt_tokens','completion_tokens','total_tokens']}
for n,entry in enumerate(w['requests']):
 check(f'wire {n+1} received semantic valid bounded',entry['outcome']=='RESPONSE_RECEIVED' and entry['http_status']==200 and entry['semantic_valid'] and entry['requested_model']=='intern-s2' and entry['response_model']=='Intern-S2' and entry['max_tokens']==512 and entry['stream'] is False and entry['input_characters']<=2000)
 check(f'wire {n+1} usage complete',entry['usage']['status']=='known' and entry['usage']['tokens']['total_tokens']==entry['usage']['tokens']['prompt_tokens']+entry['usage']['tokens']['completion_tokens'] and entry['usage']['tokens']['completion_tokens']<=512)
 for k in usage:usage[k]+=entry['usage']['tokens'][k]
 if n:
  check(f'wire {n+1} elapsed wall >=6 seconds',(datetime.fromisoformat(entry['start_utc'])-datetime.fromisoformat(w['requests'][n-1]['end_utc'])).total_seconds()>=6 and entry['seconds_since_previous_response']>=6)
for g,gr in zip(fixture['groups'],r['group_results']):
 label=g['label'];run=next(x for x in t['runs'] if x['id']==gr['run_id']);messages=run['context']['messages'];resource=next(x for x in t['resources'] if x['id']==g['resource_id']);contract=gr['readback']['contract']['snapshot'];attempts=sorted([x for x in t['attempts'] if x['run_id']==run['id']],key=lambda x:x['created_at']);ops=[x for x in t['operations'] if x['run_id']==run['id']];ww=[x for x in w['requests'] if x['group']==label]
 check(label+' exact accepted owner/project/runtime/source',run['project_id']==g['project_id'] and run['principal_id']==g['owner_id'] and run['runtime_id']==g['runtime_id'] and run['resource_refs']==[g['resource_id']] and contract['runtime_id']==g['runtime_id'] and contract['goal']['owner_id']==g['owner_id'] and contract['goal']['project_id']==g['project_id'] and contract['goal']['resource_refs']==[g['resource_id']])
 check(label+' owner/runtime resource grant intersection',all(any(x['principal_id']==principal and x['project_id']==g['project_id'] and x['resource_id']==g['resource_id'] and x['tool_ref']=='resource.read' for x in active) for principal in [g['owner_id'],g['runtime_id']]))
 check(label+' PARTIAL/semantic NOT_RUN remains explicit',run['status']==gr['readback']['status']=='PARTIAL' and run['result']==gr['readback']['result'] and run['result']['answer'].strip()==g['expected_answer'] and run['result']['goal_acceptance']=='NOT_RUN' and run['result']['mode']=='LIVE')
 check(label+' fixed limits no repair/tool expansion',contract['limits']=={'max_requests':2,'max_tools':1,'max_repairs':0,'max_total_tokens':5000,'max_output_tokens':512,'run_seconds':300} and run['context']['requests']==2 and run['context']['tools']==1 and run['context']['repairs']==0)
 check(label+' public context role sequence',[m['role'] for m in messages]==['system','user','assistant','tool','assistant'])
 other=next(x for x in fixture['groups'] if x['label']!=label)
 check(label+' no foreign resource in entire public context',other['resource_id'] not in json.dumps(messages))
 check(label+' resource fingerprint equals actual synthetic bytes',resource['content']==g['expected_answer'] and resource['hash']==hashlib.sha256(resource['content'].encode()).hexdigest() and contract['resources'][0]['content_hash']==resource['hash'])
 check(label+' only own resource-read VERIFIED receipt',len(ops)==1 and ops[0]['status']=='VERIFIED' and ops[0]['tool_ref']=='resource.read' and ops[0]['receipt']['data']=={'resource_id':g['resource_id'],'content':resource['content'],'hash':resource['hash'],'format':'txt'})
 feedback=json.loads(messages[3]['content']);call=messages[2]['tool_calls'][0]
 check(label+' tool feedback exactly ledger receipt and call',feedback==ops[0]['receipt'] and feedback['operation_id']==ops[0]['id'] and messages[3]['tool_call_id']==ops[0]['call_id']==call['id'] and call['function']['name']=='resource.read' and json.loads(call['function']['arguments'])=={'resource_id':g['resource_id']} and run['result']['receipts']==[feedback])
 for i,a in enumerate(attempts):
  sent=messages[:2 if i==0 else 4];body={'model':'intern-s2','messages':sent,'tools':definitions(),'stream':False,'max_tokens':512};req=httpx.Request('POST','https://example.invalid',json=body)
  check(f'{label} round{i+1} reconstruct exact complete send bytes',hashlib.sha256(req.content).hexdigest()==ww[i]['request_sha256'] and len(req.content)==ww[i]['utf8_bytes'] and len(req.content.decode())==ww[i]['input_characters'])
  check(f'{label} round{i+1} request fingerprint binds messages/tools/model',a['parameters']['request_fingerprint']==fingerprint({'messages':sent,'tools':definitions(),'model':'intern-s2'}))
  check(f'{label} round{i+1} actual response identity/usage/context',a['status']=='RECEIVED' and a['mode']=='LIVE' and a['request_model']=='intern-s2' and a['response_model']=='Intern-S2' and a['usage']==ww[i]['usage'] and a['response']==messages[2 if i==0 else 4] and a['parameters']['model_identity']['enforced'] and a['parameters']['model_identity']['verdict']=='ACCEPTED')
 ev=[x for x in t['events'] if x['run_id']==run['id']];verified=next(x for x in ev if x['kind']=='TOOL_VERIFIED');reserved=[x for x in ev if x['kind']=='MODEL_RESERVED']
 check(label+' verified read before second reservation and send',verified['created_at']<reserved[1]['created_at']<datetime.fromisoformat(ww[1]['start_utc']).timestamp())
 check(label+' cold-store and HTTP403 assertions recorded by inspected controller',all(name+' '+label in r['checks'] for name in ['cold-store persistent result','other owner denied completed run','other owner denied completed history']))
check('cleanup all recorded successful',all(r['cleanup'][k] is True for k in ['api_exited','container_stopped','container_removed','owned_temp_removed']) and r['cleanup']['worker_returncodes']==[0,0])
check('formal signoff/weights unknown preserved',r['formal_F1_signoff'] is False and r['weight_version']=='unknown')
report={'status':'PASS_ARCHIVED_EVIDENCE_INDEPENDENT_ASSERTIONS','assertions':len(checks),'checks':checks,'usage_sum':usage,'external_requests_by_reviewer':0,'input_sha256':{name:hashlib.sha256((p/name).read_bytes()).hexdigest() for name in ['results.json','wire.json','preflight.json','fixture.json','controller.py','send_guard.py']},'boundaries':['Only archived evidence independently checked; removed PostgreSQL not re-queried and LIVE not repeated.','Cold Store and live HTTP403 execution confirmed through inspected controller and archived checks, not independently re-executed.','Both runs remain PARTIAL; semantic goal acceptance NOT_RUN; no formal F1/whole AT02 signoff or model weight identity.','Earlier AT02/V5/AT05 failure history not superseded.']}
Path('/tmp/at02-dual-independent-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['status','assertions','usage_sum','external_requests_by_reviewer','input_sha256']}))
