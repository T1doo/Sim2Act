"""Closed run6 readonly proof-component timing, never an admission or success test."""
import hashlib,json,time
from pathlib import Path
import httpx
from sqlalchemy import select
from sim2act import natural_live_admission as gate, pa_spec_apps as spec
from sim2act.db import Store,runs,delivery_graph_requests as rows
from sim2act.model import InternModel,MockModel
from sim2act.pb_natural_specs import _source_reads
root=Path('/workspace/production-trial-stages-20261018')
path=root/'run-6-chain/actual-tmp/actual-prefix0/fixture.db'
def blocked(*a,**k): raise AssertionError('No models/network in readonly component timing')
for name in ('request','request_serialized','request_serialized_captured'):
 setattr(InternModel,name,blocked)
MockModel.request=blocked
httpx.HTTPTransport.handle_request=blocked
httpx.AsyncHTTPTransport.handle_async_request=blocked
before=hashlib.sha256(path.read_bytes()).hexdigest()
store=Store('sqlite:///'+str(path),test_only=True)
steps=[];error=None
try:
 with store.tx() as c:
  scope=c.execute(select(rows.c.snapshot).where(rows.c.kind==gate.SCOPE)).scalar_one()
  phase=c.execute(select(rows.c.snapshot).where(rows.c.kind==gate.PHASE)).scalar_one()
  contract=gate.parse_contract(scope['request'])
  rid=phase['request']['authority']['run_id']
  job=c.execute(select(runs).where(runs.c.id==rid)).mappings().one()
  for group,names in (('prewrite',('bound','stage','stage')),('postwrite',('stage','bound','stage','stage'))):
   with _source_reads(store,c):
    for name in names:
     start=time.monotonic()
     if name=='bound': spec.bound(store,c,contract.principal_id,job,gate._limits(contract))
     else: gate._stage_current(store,c,contract.principal_id,contract,'source',rid)
     steps.append(dict(group=group,component=name,seconds=time.monotonic()-start))
except Exception as exc:
 error=dict(type=type(exc).__name__,code=getattr(exc,'code',None),message=str(exc))
finally:store.engine.dispose()
after=hashlib.sha256(path.read_bytes()).hexdigest()
value=dict(profile_only_no_lease_or_admission_qualification=True,real_model_requests=0,
           error=error,steps=steps,total_seconds=sum(s['seconds'] for s in steps),
           db_sha256_before=before,db_sha256_after=after,db_bytes_unchanged=before==after)
(root/'controller-read-components.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps(value))
assert before==after
