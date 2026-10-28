"""Passive full-chain timing; no gate, clock, transport or result substitutions."""
import json,time,threading
from pathlib import Path
from contextlib import contextmanager
records=[]

def pytest_configure(config):
    from sim2act import natural_spec_runtime as r
    before,commit,after=r._cold_model_before,r._ColdTrialGraph.commit,r._model_settlement_read
    local=threading.local()
    @contextmanager
    def observed(*args,**kwargs):
        rec=dict(kind='G0',started_at=time.time(),completed=False,commits=[])
        started=time.monotonic();local.current=rec
        try:
            with before(*args,**kwargs) as trial:
                rec['selected']=trial is not None
                yield trial
            rec['completed']=True
        except BaseException as error:
            rec['error']=error.public() if hasattr(error,'public') else type(error).__name__
            raise
        finally:
            rec['wall_seconds']=time.monotonic()-started
            records.append(rec);local.current=None
    def committed(self,prefix):
        rec=getattr(local,'current',None);started=time.monotonic()
        item=dict(key=prefix.key,returned=False)
        try:
            value=commit(self,prefix);item['returned']=True;return value
        finally:
            item['wall_seconds']=time.monotonic()-started
            if rec is not None:rec['commits'].append(item)
    @contextmanager
    def settled(*args,**kwargs):
        rec=dict(kind='G1',completed=False);started=time.monotonic()
        try:
            with after(*args,**kwargs) as result:yield result
            rec['completed']=True
        finally:
            rec['wall_seconds']=time.monotonic()-started;records.append(rec)
    r._cold_model_before=observed;r._ColdTrialGraph.commit=committed;r._model_settlement_read=settled

def pytest_sessionfinish(session,exitstatus):
    Path('/workspace/Sim2Act/docs/evidence/cloud-core-20261028/full-timings.json').write_text(json.dumps(dict(exitstatus=int(exitstatus),records=records),indent=2)+'\n')
