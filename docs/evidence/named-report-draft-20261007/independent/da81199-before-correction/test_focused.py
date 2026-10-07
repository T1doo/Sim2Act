import copy,json,socket,subprocess,threading,time,os
from pathlib import Path
import pytest,uvicorn
from sqlalchemy import select,update
from basis import env,actual_source
import test_conditional_run_bindings as plumbing
from sim2act.conditional_runs import candidate_for
from sim2act.db import app_drafts,app_previews,task_extractions,fingerprint,principals,grants,protocol_jobs
OUT=Path('/tmp/named-report-draft-independent-review')

def saved(env,tmp_path):
 rid,actual,check,wires,_=actual_source(env,tmp_path)
 response=env[2].post(plumbing.base(env)+'/extract',json=plumbing.extract_body(rid,actual,check));assert response.status_code==202,response.text
 eid=response.json()['run_id']
 with env[0].tx() as c: snapshot=c.execute(select(protocol_jobs.c.accepted_snapshot).where(protocol_jobs.c.run_id==eid)).scalar_one()
 plumbing.work(env,tmp_path,[plumbing.envelope(candidate_for(snapshot['contract'],env[6]))],wires)
 plan=plumbing.get(env,eid)['result']['compiled_plan'];body={'extraction_run_id':eid,'expected_plan_fingerprint':plan['plan_fingerprint'],'expected_check_fingerprint':check['fingerprint'],'target_resource_id':env[7],'expected_target_hash':snapshot['contract']['source_hash'],'name':'Independent named hypothetical draft','request_key':'independent-save'}
 path=f'/api/projects/{env[5]}/conditional-apps';r=env[2].post(path,json=body);assert r.status_code==201,r.text
 return path,r.json(),body,wires

def request(draft,key):return {'expected_app_fingerprint':draft['fingerprint'],'scenario':plumbing.facts(500),'request_key':key}
def authority(env):
 with env[0].tx() as c:return fingerprint([[dict(r) for r in c.execute(select(t)).mappings()] for t in [principals,grants]])

def test_history_same_payload_run_and_row_key(env,tmp_path):
 path,draft,_,wires=saved(env,tmp_path);history=path+'/'+draft['id']+'/history';runpath=path+'/'+draft['id']+'/runs';before=authority(env)
 a=env[2].post(runpath,json=request(draft,'a')).json()['run_id'];b=env[2].post(runpath,json=request(draft,'b')).json()['run_id'];assert a!=b
 with env[0].tx() as c: row=dict(c.execute(select(app_previews).where(app_previews.c.app_id==draft['id'],app_previews.c.request_key=='a')).mappings().one());c.execute(update(app_previews).where(app_previews.c.id==row['id']).values(output={'namespace':'bounded-conditional-app.v1','run_id':b}))
 swap=env[2].get(history);assert swap.status_code==409,swap.text
 with env[0].tx() as c:c.execute(update(app_previews).where(app_previews.c.id==row['id']).values(output=row['output'],request_key='row-key-forged'))
 key=env[2].get(history);assert key.status_code==409,key.text
 assert authority(env)==before and len(wires)==3
 (OUT/'history-attacks.json').write_text(json.dumps({'same_payload_another_run_http':swap.status_code,'row_key_http':key.status_code,'source_extract_mock_calls':len(wires),'authority_unchanged':True},indent=2))

def test_coherent_wrapper_bool_and_origin_missing(env,tmp_path):
 path,draft,_,_=saved(env,tmp_path)
 with env[0].tx() as c: row=dict(c.execute(select(app_drafts).where(app_drafts.c.id==draft['id'])).mappings().one());marker=dict(c.execute(select(task_extractions).where(task_extractions.c.app_id==draft['id'])).mappings().one())
 outcomes={}
 for damage in ['bool_version','missing_origin']:
  bad=copy.deepcopy(row['candidate'])
  if damage=='bool_version':bad['version']=True
  else:del bad['origin']['expected_check_fingerprint']
  fp=fingerprint(bad)
  with env[0].tx() as c:
   c.execute(update(app_drafts).where(app_drafts.c.id==draft['id']).values(candidate=bad,fingerprint=fp));c.execute(update(task_extractions).where(task_extractions.c.app_id==draft['id']).values(snapshot={'kind':'bounded-conditional-app.v1','wrapper':bad,'wrapper_fingerprint':fp}))
  r=env[2].get(path+'/'+draft['id']);assert r.status_code==409,r.text;outcomes[damage]=r.status_code
  with env[0].tx() as c:c.execute(update(app_drafts).where(app_drafts.c.id==draft['id']).values(candidate=row['candidate'],fingerprint=row['fingerprint']));c.execute(update(task_extractions).where(task_extractions.c.app_id==draft['id']).values(snapshot=marker['snapshot']))
 (OUT/'wrapper-attacks.json').write_text(json.dumps(outcomes,indent=2))

def test_closed_client_payload_and_current_authority(env,tmp_path):
 path,draft,body,wires=saved(env,tmp_path);outcomes={};baseline=authority(env)
 for extra in ['candidate','replay']:
  a=env[2].post(path,json={**body,extra:{}});b=env[2].post(path+'/'+draft['id']+'/runs',json={**request(draft,'closed'),extra:{}});assert a.status_code==b.status_code==422;outcomes[extra]=[a.status_code,b.status_code]
 for i in [6,7]:
  with env[0].tx() as c: rows=[dict(r) for r in c.execute(select(grants).where(grants.c.resource_id==env[i])).mappings()];c.execute(update(grants).where(grants.c.resource_id==env[i]).values(revoked=True))
  statuses=[env[2].get(path+'/'+draft['id']).status_code,env[2].get(path+'/'+draft['id']+'/history').status_code,env[2].post(path+'/'+draft['id']+'/runs',json=request(draft,'revoked')).status_code];assert statuses==[403]*3;outcomes['source' if i==6 else 'target']=statuses
  with env[0].tx() as c:
   for row in rows:c.execute(update(grants).where(grants.c.id==row['id']).values(revoked=row['revoked']))
 assert authority(env)==baseline and len(wires)==3
 (OUT/'authority-attacks.json').write_text(json.dumps(outcomes,indent=2))

def test_actual_named_reply_loss_then_retry422(env,tmp_path):
 path,draft,_,wires=saved(env,tmp_path);before=authority(env)
 with socket.socket() as sock:sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
 info={'base':f'http://127.0.0.1:{port}','project':env[5],'draft':draft['id']};(OUT/'ui-info.json').write_text(json.dumps(info))
 server=uvicorn.Server(uvicorn.Config(env[2].app,host='127.0.0.1',port=port,log_level='error'));thread=threading.Thread(target=server.run,daemon=True);thread.start()
 try:
  end=time.time()+10
  while not server.started:
   assert thread.is_alive() and time.time()<end;time.sleep(.01)
  child=subprocess.run(['node',str(OUT/'actual-unknown422.cjs')],env={**os.environ,'NODE_PATH':'/workspace/browser-tools/node_modules'},capture_output=True,text=True,timeout=20);(OUT/'actual-unknown422.log').write_text(child.stdout+child.stderr);assert child.returncode==0,child.stdout+child.stderr
  result=json.loads((OUT/'actual-unknown422-result.json').read_text());assert authority(env)==before and len(wires)==3
  assert result['afterRetry']['pending'] is True and result['afterRetry']['disabled'] is True,result
 finally:server.should_exit=True;thread.join(10);assert not thread.is_alive()
