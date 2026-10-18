import cProfile
import hashlib
import io
import json
import pstats
import time
from pathlib import Path

import httpx
from sqlalchemy import select

from sim2act import natural_live_admission as gate, production_trial_policy as policy
from sim2act.db import Store, runs, delivery_graph_requests as rows
from sim2act.model import InternModel, MockModel

root=Path('/workspace/production-trial-stages-20261018')
path=root/'run-7-chain/actual-tmp/actual-prefix0/fixture.db'
before=hashlib.sha256(path.read_bytes()).hexdigest()
store=Store('sqlite:///'+str(path),test_only=True)
with store.tx() as c:
    scope=c.execute(select(rows.c.snapshot).where(rows.c.kind==gate.SCOPE)).scalar_one()
    phase=c.execute(select(rows.c.snapshot).where(rows.c.kind==gate.PHASE,rows.c.request_key=='cold')).scalar_one()
contract=gate.parse_contract(scope['request'])
consent=gate.StageApproveInput.model_validate(phase['request'])
with store.tx() as c:
    job=c.execute(select(runs).where(runs.c.id==consent.authority.run_id)).mappings().one()
    approval=gate._saved(c,contract.principal_id,gate.entity(contract),gate.APPROVE,'approve',gate.Approval)
def blocked(*a,**k):raise AssertionError('Readonly profile must never request a model or network')
InternModel.request=InternModel.request_serialized=InternModel.request_serialized_captured=blocked
MockModel.request=blocked
httpx.HTTPTransport.handle_request=httpx.AsyncHTTPTransport.handle_async_request=blocked
profile=cProfile.Profile();start=time.monotonic();error=None
try:
    profile.enable()
    with store.tx() as c:
        policy.check_run(store,c,contract.principal_id,contract,approval.request.request_key,'cold',job['id'],job['version'],job['fence'],job['worker_id'])
except Exception as e:
    error={'type':type(e).__name__,'code':getattr(e,'code',None)}
finally:
    profile.disable()
elapsed=time.monotonic()-start
stream=io.StringIO();pstats.Stats(profile,stream=stream).sort_stats('cumtime').print_stats(45)
(root/'readonly-cold-context-expired-profile.txt').write_text(stream.getvalue())
store.engine.dispose()
after=hashlib.sha256(path.read_bytes()).hexdigest()
record={'elapsed_seconds':elapsed,'error':error,'db_bytes_sha_before':before,'db_bytes_sha_after':after,
        'db_bytes_unchanged':before==after,'profile_only_no_sends_no_retry':True,'expected_expired_lease_is_not_bypassed':True}
(root/'readonly-cold-context-expired-profile.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record));print(stream.getvalue())
