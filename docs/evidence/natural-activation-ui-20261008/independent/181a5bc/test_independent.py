import copy,json
from pathlib import Path
from conftest import env
from sqlalchemy import select,update
from test_natural_activation_flow import setup,approved,submit
from sim2act import natural_activations as a
from sim2act.db import meta,natural_activations,resources,fingerprint

def snap(s):
 with s.tx() as c:return {t.name:sorted([dict(r) for r in c.execute(select(t)).mappings()],key=lambda x:json.dumps(x,sort_keys=True,default=str)) for t in meta.sorted_tables}
def save(tmp_path,name,data): (tmp_path/(name+'.json')).write_text(json.dumps(data,indent=2))
def test_resource_change_is_readonly_ineligible_not_approved_send(env,tmp_path):
 v=setup(env);s,_,cl,*_=v;session,_=approved(v)
 with s.tx() as c:c.execute(update(resources).where(resources.c.id==v[-2]).values(content='item,quantity_z\naltered,999\n'))
 before=snap(s);r=cl.get(f'/api/projects/{v[5]}/natural-activations');assert r.status_code==200
 item=r.json()['items'][0];assert item['submission_available'] is False and item['blocked_reason']=='VERIFICATION_FAILED';assert snap(s)==before
 save(tmp_path,'source-change',{'status':r.status_code,'blocked':item['blocked_reason'],'full_before_fp':fingerprint(before),'full_after_fp':fingerprint(snap(s))})
def test_coherent_scope_rpm_boolean_fails_without_writes(env,tmp_path):
 v=setup(env);s,_,cl,*_=v;session,_=approved(v)
 with s.tx() as c:
  row=dict(c.execute(select(natural_activations)).mappings().one());scope=copy.deepcopy(row['scope']);scope['caps']['rpm']=True;c.execute(update(natural_activations).values(scope=scope,scope_fingerprint=fingerprint(scope)))
 before=snap(s);r=cl.get(f'/api/projects/{v[5]}/natural-activations');assert r.status_code==400;assert snap(s)==before
 save(tmp_path,'coherent-shape',{'status':r.status_code,'code':r.json()['error']['code'],'full_before_fp':fingerprint(before),'full_after_fp':fingerprint(snap(s))})
def test_expired_session_cold_run_read_original_deadline_and_original_key(env,monkeypatch,tmp_path):
 v=setup(env);s,_,cl,*_=v;session,_=approved(v);accepted=submit(v,session,key='ind-original-key');assert accepted.status_code==202;rid=accepted.json()['run_id'];original=cl.get('/api/runs/'+rid).json();deadline=original['natural_deadline']['expires_at'];monkeypatch.setattr(a,'now',lambda:session['approval']['expires_at']+1)
 before=snap(s);history=cl.get('/api/runs/'+rid);assert history.status_code==200;assert history.json()['natural_deadline']['expires_at']==deadline
 lst=cl.get(f'/api/projects/{v[5]}/natural-activations').json()['items'][0];assert not lst['submission_available'] and not lst['approved_not_expired'];replay=submit(v,session,key='ind-original-key');assert replay.status_code==403 and replay.json()['error']['code']=='PERMISSION_DENIED';assert snap(s)==before
 save(tmp_path,'expired-history',{'cold_status':history.status_code,'replay':replay.status_code,'unchanged_deadline':deadline,'full_before_fp':fingerprint(before),'full_after_fp':fingerprint(snap(s))})
def test_foreign_project_list_cannot_relabel_scope_and_old_key_is_readonly(env,tmp_path):
 v=setup(env);s,_,cl,*_=v;session,_=approved(v);foreign=s.project(v[3],'independent-empty');before=snap(s)
 own=cl.get(f'/api/projects/{foreign}/natural-activations');assert own.status_code==200 and own.json()['items']==[]
 cl.headers['Authorization']='Bearer synthetic-test-B';denied=cl.get(f'/api/projects/{v[5]}/natural-activations');assert denied.status_code==403;assert snap(s)==before
 save(tmp_path,'project-owner',{'foreign_items':0,'other_owner_status':denied.status_code,'full_before_fp':fingerprint(before),'full_after_fp':fingerprint(snap(s))})
