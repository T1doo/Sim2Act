"""Synthetic derivative of the sealed failed fixture; no historical send/recovery."""
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import shutil
import socket
import sys
import time

import httpx
import pytest
from sqlalchemy import select

sys.path.insert(0,'/workspace/Sim2Act/tests')
from test_production_trial_stages import _generation_proof_rejections
from test_spec_app_operations import snapshot
from sim2act import natural_live_admission as gate, pa_spec_apps as spec, pa_trial_dispatch as bridge
from sim2act.config import Settings
from sim2act.db import Store,attempts,runs,delivery_graph_requests as rows
from sim2act.errors import DomainError
from sim2act.model import InternModel,MockModel
from sim2act.worker import Worker

root=Path('/workspace/cold-save-admission-20261018/targeted-regression')
root.mkdir(exist_ok=False)
original=Path('/workspace/production-trial-stages-20261018/run-8-chain/actual-tmp/actual-prefix0/fixture.db')
original_sha=hashlib.sha256(original.read_bytes()).hexdigest()
path=root/'synthetic-derivative.db';shutil.copyfile(original,path)
called=[]
def blocked(*args,**kwargs):
    called.append('FORBIDDEN_MODEL_OR_NETWORK_ATTEMPT')
    raise AssertionError('Targeted regression has no dispatch, model or network')
InternModel.request=InternModel.request_serialized=InternModel.request_serialized_captured=blocked
MockModel.request=blocked
httpx.HTTPTransport.handle_request=httpx.AsyncHTTPTransport.handle_async_request=blocked
socket.create_connection=blocked
url='sqlite:///'+str(path);store=Store(url,test_only=True)
with store.tx() as c:
    contract=gate.parse_contract(c.execute(select(rows.c.snapshot).where(rows.c.kind==gate.SCOPE)).scalar_one()['request'])
    approval=gate._saved(c,contract.principal_id,gate.entity(contract),gate.APPROVE,'approve',gate.Approval)
    generation=c.execute(select(runs.c.id).where(runs.c.request_key==contract.stage_keys.generate,runs.c.principal_id==contract.principal_id)).scalar_one()
    marker=c.execute(select(attempts.c.parameters).where(attempts.c.run_id==generation)).scalars().first()['pa_trial_binding']
    consent=gate._saved(c,contract.principal_id,gate.entity(contract),gate.PHASE,'cold',gate.StageApproveInput)
    cold=dict(c.execute(select(runs).where(runs.c.id==consent.authority.run_id)).mappings().one())
binding=bridge.JournalTrialBinding(contract,approval.request.request_key,marker['account_id'])
base=snapshot(store)
start=time.perf_counter()
_generation_proof_rejections(dict(data=(store,None,None,contract.principal_id),binding=binding,
    generation=generation,out=root,proof_source='SEALED_FAILED_PREFIX_COMPONENT_REGRESSION_NOT_FRESH_QUALIFICATION',clones_or_old_db_used=True))
assert snapshot(store)==base
settings=Settings(url,root,mode='mock',quota_subject=contract.quota_subject)
worker=Worker(store,settings,pa_trial=binding,goal_planner_transport=httpx.MockTransport(blocked))
with store.tx() as c:
    bound=spec.bound(store,c,contract.principal_id,cold,gate._limits(contract))
    checked=spec.receipts(store,c,cold,bound)
assert time.time()>cold['lease_until'] and cold['status']=='RUNNING' and cold['result'] is None
errors=[]
for name in ('original_SAVE_entry','fresh_read_segment_guard'):
    with pytest.raises(DomainError,match='Stale worker lease') as rejected:
        with store.tx() as c:
            if name=='original_SAVE_entry':
                spec._advance_local(worker,c,cold,cold,b=bound,checked=checked)
            else:
                with bridge._journal_reads(worker,c):
                    spec.commit_guard(worker,c,cold,bound,1)
    assert rejected.value.code=='VERSION_CONFLICT'
    assert snapshot(store)==base
    errors.append({'case':name,'code':rejected.value.code,'message':str(rejected.value),'all_55_tables_unchanged':True})
store.engine.dispose()
assert hashlib.sha256(original.read_bytes()).hexdigest()==original_sha
assert called==[]
proof=json.loads((root/'fresh-proof-rejections.json').read_text());assert len(proof['cases'])==9
record={'status':'TARGETED_COMPONENT_REGRESSION_PASS_NOT_FRESH_CHAIN','recorded_utc':datetime.now(timezone.utc).isoformat(),
    'seconds':time.perf_counter()-start,'original_fixture_sha_before':original_sha,'original_fixture_sha_after':hashlib.sha256(original.read_bytes()).hexdigest(),
    'original_fixture_unchanged':True,'derivative_db':str(path),'derivative_provenance':'COPY_OF_SEALED_FAILED_SYNTHETIC_RUN8_ONLY',
    'generation_windows':proof['cases'],'old_expired_run_id':cold['id'],'old_lease_until_unchanged':cold['lease_until'],
    'expired_SAVE_rejections':errors,'model_or_network_attempts':called,'old_request_resends':0,'new_qualification_claim':False}
(root/'targeted-regression.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'status':record['status'],'seconds':record['seconds'],'generation_windows':len(proof['cases']),'expired_SAVE_rejections':len(errors),'original_fixture_unchanged':True,'model_or_network_attempts':0}),flush=True)
