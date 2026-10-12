import time,json
from pathlib import Path
from test_pa_spec_apps import setup,prepared,material,COLD,instance,enqueue,claim
from sim2act import pa_spec_apps as spec
from sim2act.worker import Worker
from sim2act.db import select,runs

def test_profile(env,monkeypatch):
    data=setup(env);rid,_,_,_=prepared(data);_,card=material(data[2],data[4],COLD)
    p=spec.options(data[0],data[3],data[4],rid,card['id'],__import__('sim2act.contracts',fromlist=['Limits']).Limits(**{k:getattr(data[1],k) for k in __import__('sim2act.contracts',fromlist=['Limits']).Limits.model_fields}))
    body=spec.BindInput(card_id=card['id'],expected_goal_version=card['version'],expected_goal_fingerprint=card['fingerprint'],expected_source_hash=p['source_hash'],expected_model_candidate_fingerprint=p['model_candidate_fingerprint'],expected_recipe_fingerprint=p['recipe_fingerprint'],name='Profile',consent=spec.CONSENT,request_key='profile')
    r=data[2].post(f'/api/projects/{data[4]}/spec-model-runs/{rid}/bindings',json=body.model_dump());assert r.status_code==201,r.text
    release,inst=instance(data,r.json()['id']);job=enqueue(data,release,inst);records=[]
    for name in ['bound','commit_guard','verify_origin','receipts','advance']:
        original=getattr(spec,name)
        def wrap(*args,_name=name,_original=original,**kwargs):
            start=time.monotonic()
            try:return _original(*args,**kwargs)
            finally:records.append(dict(function=_name,seconds=round(time.monotonic()-start,4)))
        monkeypatch.setattr(spec,name,wrap)
    assert Worker(data[0],data[1]).once()
    Path('/tmp/pa-spec-checklist-author-20261012/profile.json').write_text(json.dumps(records,indent=2))
    with data[0].tx() as c:
        row=c.execute(select(runs).where(runs.c.id==job)).mappings().one();print(row['status'],row['error'])
