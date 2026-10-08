import json
from pathlib import Path
from conftest import env
from test_natural_activation_flow import setup,approved,submit
from sim2act import natural_activations as a
from sim2act.db import meta,fingerprint
from sqlalchemy import select

def test_stable_history_json_and_header_are_readonly(env,monkeypatch,tmp_path):
 v=setup(env);s,_,cl,*_=v;session,_=approved(v);rid=submit(v,session).json()['run_id'];clock=[a.now()];monkeypatch.setattr(a,'now',lambda:clock[0])
 def fp():
  with s.tx() as c:return fingerprint({t.name:[dict(x) for x in c.execute(select(t)).mappings()] for t in meta.sorted_tables})
 before=fp();first=cl.get('/api/runs/'+rid);clock[0]+=1;second=cl.get('/api/runs/'+rid)
 assert first.status_code==second.status_code==200 and first.json()==second.json();assert set(first.json()['natural_deadline'])=={'accepted_at','expires_at','run_seconds'};assert float(second.headers['X-Sim2Act-Server-Time'])==float(first.headers['X-Sim2Act-Server-Time'])+1;assert fp()==before
 sample={'list':cl.get(f'/api/projects/{v[5]}/natural-activations').json(),'card':v[-1]['read_preview'],'session_id':session['id']}
 Path('/tmp/natural-activation-ui-independent/8cfdb14/trusted-sample.json').write_text(json.dumps(sample))
 (tmp_path/'header.json').write_text(json.dumps({'before_fp':before,'after_fp':fp(),'stable_json':True,'header_delta':1,'deadline_keys':list(first.json()['natural_deadline'])}))
