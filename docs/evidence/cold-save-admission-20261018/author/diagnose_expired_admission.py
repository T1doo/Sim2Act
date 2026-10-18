"""Read-only component diagnosis. Never revive or execute the expired SAVE Run."""
import cProfile
import collections
from contextlib import nullcontext
import functools
import hashlib
import io
import json
from pathlib import Path
import pstats
import socket
import subprocess
import sys
import time
import traceback

import httpx
from sqlalchemy import event,select
from sim2act import natural_live_admission as gate, pa_trial_dispatch as dispatch
from sim2act import production_trial_policy as policy, pa_spec_apps as spec
from sim2act.db import Store, runs, delivery_graph_requests as rows
from sim2act.model import InternModel,MockModel
from sim2act.pb_natural_specs import _source_reads

out=Path('/workspace/cold-save-admission-20261018')
path=Path('/workspace/production-trial-stages-20261018/run-8-chain/actual-tmp/actual-prefix0/fixture.db')
def blocked(*args,**kwargs):
    raise AssertionError('No model/network call permitted in read-only component diagnosis')
InternModel.request=InternModel.request_serialized=InternModel.request_serialized_captured=blocked
MockModel.request=blocked
httpx.HTTPTransport.handle_request=httpx.AsyncHTTPTransport.handle_async_request=blocked
socket.create_connection=blocked
source=subprocess.check_output(['git','-c','core.fsmonitor=false','rev-parse','HEAD'],cwd='/workspace/Sim2Act',text=True).strip()
before=hashlib.sha256(path.read_bytes()).hexdigest()
store=Store('sqlite:///file:'+str(path)+'?mode=ro&uri=true',test_only=True)
queries=collections.Counter();spans=[];active=[];metrics={"sql_seconds":0.0}
def sql_before(c,cursor,statement,params,context,many):
    verb=statement.lstrip().split(None,1)[0].upper()
    if verb not in ('SELECT','BEGIN','PRAGMA'):
        raise AssertionError('No fixture writes permitted: '+verb)
    queries[verb]+=1
    context._cold_diagnostic_start=time.perf_counter()
def sql_after(c,cursor,statement,params,context,many):
    elapsed=time.perf_counter()-context._cold_diagnostic_start
    metrics['sql_seconds']+=elapsed
    if statement.startswith('BEGIN'):
        spans.append({'name':'BEGIN_IMMEDIATE','seconds':elapsed,'phase':active[0] if active else 'setup'})
event.listen(store.engine,'before_cursor_execute',sql_before)
event.listen(store.engine,'after_cursor_execute',sql_after)
with store.tx() as c:
    scope=c.execute(select(rows.c.snapshot).where(rows.c.kind==gate.SCOPE)).scalar_one()
    phase=c.execute(select(rows.c.snapshot).where(rows.c.kind==gate.PHASE,rows.c.request_key=='cold')).scalar_one()
contract=gate.parse_contract(scope['request'])
consent=gate.StageApproveInput.model_validate(phase['request'])
with store.tx() as c:
    job=dict(c.execute(select(runs).where(runs.c.id==consent.authority.run_id)).mappings().one())
assert job['status']=='RUNNING' and job['result'] is None
assert time.time()>job['lease_until']
originals=[]
for module,names in [(gate,['_approved','_run_context','_stage_current','_stage_current_read','_stage_current_bound','_generation_accounted']), (dispatch,['_journal_state','_journal_slot','_journal_chain','journal_stage_accounted']), (spec,['bound','audit_fingerprint','job_scope_gate'])]:
    for name in names:
        original=getattr(module,name)
        def wrap(original=original,label=module.__name__+'.'+name):
            @functools.wraps(original)
            def observed(*args,**kwargs):
                mark=time.perf_counter();cpu=time.process_time();sql_time=metrics["sql_seconds"];q=sum(queries.values());depth=len(active)
                caller=sys._getframe(1);where={"file":caller.f_code.co_filename,"line":caller.f_lineno,"function":caller.f_code.co_name}
                active.append(label);error=None
                try:return original(*args,**kwargs)
                except BaseException as exc:
                    error={'type':type(exc).__name__,'code':getattr(exc,'code',None)}
                    raise
                finally:
                    active.pop();spans.append({'name':label,'phase':active[0] if active else None,'depth':depth,'caller':where,'seconds':time.perf_counter()-mark,'cpu_seconds':time.process_time()-cpu,'sql_seconds':metrics['sql_seconds']-sql_time,'lease_remaining_at_end':job['lease_until']-time.time(),'sql':sum(queries.values())-q,'error':error})
            return observed
        originals.append((module,name,original));setattr(module,name,wrap())
results=[]
try:
    for name,reuse in [('post_write_no_read_segment',False),('fresh_same_transaction_read_segment',True)]:
        active.append(name);q=queries.copy();start=time.perf_counter();cpu=time.process_time();sql_time=metrics["sql_seconds"];prof=cProfile.Profile();error=None
        try:
            with store.tx() as c:
                assert c.info.get('pb_source_reads') is None
                prof.enable()
                with (_source_reads(store,c) if reuse else nullcontext()):
                    policy.check_run(store,c,contract.principal_id,contract,consent.approval_key,'cold',job['id'],job['version'],job['fence'],job['worker_id'])
        except Exception as exc:
            error={'type':type(exc).__name__,'code':getattr(exc,'code',None),'traceback':traceback.format_exc()}
        finally:
            prof.disable();active.pop()
        elapsed=time.perf_counter()-start
        stream=io.StringIO();stats=pstats.Stats(prof,stream=stream).sort_stats('cumtime');stats.print_stats(65)
        (out/(name+'.profile.txt')).write_text(stream.getvalue())
        statrows=[{'file':f,'line':line,'function':fn,'primitive_calls':v[0],'calls':v[1],'self_seconds':v[2],'cumulative_seconds':v[3]} for (f,line,fn),v in stats.stats.items()]
        (out/(name+'.profile.json')).write_text(json.dumps(sorted(statrows,key=lambda x:-x['cumulative_seconds']),indent=2)+'\n')
        result={'name':name,'seconds':elapsed,'cpu_seconds':time.process_time()-cpu,'sql_seconds':metrics['sql_seconds']-sql_time,'lease_remaining_at_end':job['lease_until']-time.time(),'sql':dict(queries-q),'error':error,'expired_lease_not_bypassed':error is not None and error['code']=='VERSION_CONFLICT'}
        results.append(result);print(json.dumps({k:v for k,v in result.items() if k!='error'}),flush=True)
        assert result['expired_lease_not_bypassed']
finally:
    for module,name,original in originals:setattr(module,name,original)
    store.engine.dispose()
after=hashlib.sha256(path.read_bytes()).hexdigest()
record={'source_sha':source,'fixture':str(path),'fixture_sha_before':before,'fixture_sha_after':after,'fixture_unchanged':before==after,'kind':'READ_ONLY_ADMISSION_COMPONENT_DIAGNOSIS_NOT_FULL_SAVE_NOT_QUALIFICATION','no_clock_or_lease_changed':True,'no_old_request_resend':True,'model_or_network_calls':0,'old_run_id':job['id'],'old_run_lease_until':job['lease_until'],'results':results,'spans':spans,'limitations':['Historical original guard did not capture outer SAVE line 1220 versus 1257','Cannot enter expired SAVE to measure full guard or write transaction; both paths intentionally retain original VERSION_CONFLICT','Fresh read segment is isolated to a single original read-only transaction, not retained across writes','Profile timings include observer/cProfile overhead and are not completion guarantees']}
(out/'expired-admission-diagnosis.json').write_text(json.dumps(record,indent=2)+'\n')
assert before==after
print(json.dumps({'fixture_unchanged':before==after,'source_sha':source,'kind':record['kind']}),flush=True)
