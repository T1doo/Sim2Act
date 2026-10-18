"""Old failed synthetic Run must remain unsavable after a source change.
No old trial binding is installed: its software fingerprint correctly rejects.
"""
from datetime import datetime,timezone
import hashlib,json,shutil,socket,sys,time
from pathlib import Path
import httpx,pytest
from sqlalchemy import select
sys.path.insert(0,'/workspace/Sim2Act/tests')
from test_spec_app_operations import snapshot
from sim2act import natural_live_admission as gate,pa_spec_apps as spec
from sim2act.config import Settings
from sim2act.db import Store,runs,delivery_graph_requests as rows
from sim2act.errors import DomainError
from sim2act.model import InternModel,MockModel
from sim2act.pb_natural_specs import _source_reads
from sim2act.worker import Worker

root=Path('/workspace/cold-save-admission-20261018/expired-lease-regression');root.mkdir(exist_ok=False)
original=Path('/workspace/production-trial-stages-20261018/run-8-chain/actual-tmp/actual-prefix0/fixture.db')
expected='c234d6fd4134cb2e41c6483bfc21024fbeda2dea78940d45e09e09e2f4db21e9'
assert hashlib.sha256(original.read_bytes()).hexdigest()==expected
path=root/'synthetic-derivative.db';shutil.copyfile(original,path)
called=[]
def blocked(*args,**kwargs):
 called.append('FORBIDDEN');raise AssertionError('No dispatch or network in expired lease regression')
InternModel.request=InternModel.request_serialized=InternModel.request_serialized_captured=blocked
MockModel.request=blocked
httpx.HTTPTransport.handle_request=httpx.AsyncHTTPTransport.handle_async_request=blocked
socket.create_connection=blocked
url='sqlite:///'+str(path);store=Store(url,test_only=True)
with store.tx() as c:
 contract=gate.parse_contract(c.execute(select(rows.c.snapshot).where(rows.c.kind==gate.SCOPE)).scalar_one()['request'])
 consent=gate._saved(c,contract.principal_id,gate.entity(contract),gate.PHASE,'cold',gate.StageApproveInput)
 cold=dict(c.execute(select(runs).where(runs.c.id==consent.authority.run_id)).mappings().one())
 bound=spec.bound(store,c,contract.principal_id,cold,gate._limits(contract))
 checked=spec.receipts(store,c,cold,bound)
settings=Settings(url,root,mode='mock',quota_subject=contract.quota_subject)
worker=Worker(store,settings,goal_planner_transport=httpx.MockTransport(blocked))
assert worker.pa_trial is None
assert time.time()>cold['lease_until'] and cold['status']=='RUNNING' and cold['result'] is None
base=snapshot(store);errors=[]
for name in ('original_SAVE_entry','fresh_source_read_segment_guard'):
 with pytest.raises(DomainError,match='Stale worker lease') as rejected:
  with store.tx() as c:
   if name=='original_SAVE_entry':spec._advance_local(worker,c,cold,cold,b=bound,checked=checked)
   else:
    with _source_reads(store,c):spec.commit_guard(worker,c,cold,bound,1)
 assert rejected.value.code=='VERSION_CONFLICT' and snapshot(store)==base
 errors.append({'case':name,'code':rejected.value.code,'message':str(rejected.value),'all_55_tables_unchanged':True})
store.engine.dispose();assert called==[]
assert hashlib.sha256(original.read_bytes()).hexdigest()==expected
proof_path=Path('/workspace/cold-save-admission-20261018/targeted-regression/fresh-proof-rejections.json')
proof=json.loads(proof_path.read_text());assert len(proof['cases'])==9
record={'status':'TARGETED_COMPONENT_WINDOWS_AND_EXPIRED_LEASE_PASS_NOT_FRESH_CHAIN','utc':datetime.now(timezone.utc).isoformat(),
 'derivative_provenance':'COPY_OF_SEALED_FAILED_SYNTHETIC_RUN8_ONLY','original_fixture_sha_before':expected,
 'original_fixture_sha_after':hashlib.sha256(original.read_bytes()).hexdigest(),'original_fixture_unchanged':True,
 'generation_nine_windows_proof':str(proof_path),'generation_nine_windows_proof_sha256':hashlib.sha256(proof_path.read_bytes()).hexdigest(),
 'generation_nine_windows_rerun_in_this_command':False,'expired_lease_rejections':errors,'old_run_id':cold['id'],
 'old_lease_until_unchanged':cold['lease_until'],'old_trial_binding_installed':False,
 'worker':'legitimate generic original Worker; changed-software old trial remains uninstalled/rejected',
 'real_model_calls':0,'historical_request_resends':0,'new_qualification_claim':False}
(root/'expired-lease-regression.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'status':record['status'],'old_lease_rejections':len(errors),'nine_windows_reused_not_rerun':True,'original_fixture_unchanged':True,'real_model_calls':0}))
