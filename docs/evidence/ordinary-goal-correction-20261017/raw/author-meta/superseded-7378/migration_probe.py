import hashlib,json,subprocess,sys
from pathlib import Path
from sqlalchemy import inspect,select
root=Path('/workspace/Sim2Act');out=Path('/workspace/ordinary-goal-correction-evidence-20261017');data=Path('/tmp/ordinary-correction-migration-probe-7378b97e-20261017');data.mkdir(exist_ok=False);sys.path.insert(0,str(root/'tests'))
import conftest
from test_ordinary_corrections import rejected,preview,correction_body,post
from sim2act.db import fingerprint,meta,ordinary_correction_links
fixture=conftest.env.__wrapped__(data);env=next(fixture)
try:
 _,_,parent,result,_=rejected(env)
 store=env[0]
 def snapshot():
  with store.tx() as c:
   return {name:sorted([dict(r) for r in c.execute(select(table)).mappings()],key=fingerprint) for name,table in meta.tables.items() if name!='ordinary_correction_links'}
 before=snapshot();names=inspect(store.engine).get_table_names()
 with store.tx() as c:assert not c.execute(select(ordinary_correction_links)).first()
 ordinary_correction_links.drop(store.engine)
 assert 'ordinary_correction_links' not in inspect(store.engine).get_table_names()
 store.initialize()
 after=snapshot();assert before==after and inspect(store.engine).get_table_names()==names
 assert env[2].get('/api/runs/'+parent).json()==result
 value=preview(env,parent);body=correction_body(value,'after-additive-migrate');made=post(env,parent,body);assert made.status_code==202,made.text
 assert post(env,parent,body).json()==made.json()
 (data/'before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2)+'\n');(data/'after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2)+'\n')
 proof=dict(source='7378b97ec0d85f821c9830290d5075e831270e33',old_tables=len(before),all_old_rows_exactly_unchanged=True,old_data_fingerprint=fingerprint(before),new_table='ordinary_correction_links',only_fixture_known_empty_new_table_dropped=True,old_parent_run=parent,new_child_run=made.json()['run_id'],post_migration_same_key_idempotent=True,real_model_calls=0,fixture_model='ScriptedMd only; no child execution',pg='NOT_RUN',pg_role_permissions='NOT_RUN',database=str(data/'fixture.db'))
 (out/'migration-proof.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2)+'\n');print(json.dumps(proof,ensure_ascii=False))
finally:
 try:next(fixture)
 except StopIteration:pass
