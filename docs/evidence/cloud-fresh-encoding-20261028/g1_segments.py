"""Diagnostic virtual clock; no acceptance, HTTP or production authority."""
import json,time
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace
from collections import defaultdict
import pytest
ROOT=Path('/workspace/scratch/g1-segments');ROOT.mkdir(exist_ok=True)
@pytest.fixture(autouse=True)
def diagnostic(monkeypatch):
 from cold_semantic_clock import SemanticClock
 from sim2act import natural_spec_runtime as r,model_settlement as lease,pa_spec_apps as spec,pa_trial_dispatch as trial
 clock=SemanticClock(monkeypatch)
 # Explicit diagnostic only: do not treat this as a real monotonic lease test.
 monkeypatch.setattr(lease,'time',SimpleNamespace(time=clock.now,monotonic=clock.now))
 monotonic=time.monotonic
 state={'active':False};records=[];totals=defaultdict(lambda:dict(calls=0,seconds=0,bytes=0))
 def flush():
  (ROOT/'segments.json').write_text(json.dumps(dict(classification='DIAGNOSTIC_VIRTUAL_BUSINESS_AND_LEASE_CLOCK_NOT_ACCEPTANCE',records=records,totals=totals),indent=2)+'\n')
 def observe(owner,name,label):
  old=getattr(owner,name)
  def measured(*args,**kwargs):
   if not state['active']:return old(*args,**kwargs)
   start=monotonic()
   try:
    value=old(*args,**kwargs)
    if name=='_cold_graph_bytes':totals[label]['bytes']+=len(value)
    return value
   finally:
    totals[label]['calls']+=1;totals[label]['seconds']+=monotonic()-start
  monkeypatch.setattr(owner,name,measured)
 for owner,name,label in [(r._ColdTrialGraph,'commit','post_graph.commit'),(r,'_cold_binding_limits_facet','post_binding'),(spec,'_cold_receipts','receipts'),(trial,'_graph_journal_chain','journal_chain'),(r,'_model_inputs','model_inputs'),(r,'_cold_graph_bytes','graph_bytes'),(r._ModelSettlementRead,'check','proof.check')]:observe(owner,name,label)
 live=r._ModelSettlementRead.live
 def lived(self):
  start=monotonic();rec=dict(kind='proof.live',state=self.state,complete=False)
  try:value=live(self);rec['complete']=True;return value
  finally:rec['seconds']=monotonic()-start;records.append(rec);flush()
 monkeypatch.setattr(r._ModelSettlementRead,'live',lived)
 old=r._model_settlement_read
 @contextmanager
 def after(*args,**kwargs):
  state['active']=True;start=monotonic();selected=False
  try:
   with old(*args,**kwargs) as value:
    selected=value[2] is not None
    yield value
   if selected:
    records.append(dict(kind='G1_complete',seconds=monotonic()-start));flush()
    raise KeyboardInterrupt('OWNED DIAGNOSTIC STOP after first complete virtual-clock G1; not acceptance')
  finally:
   state['active']=False;flush()
 monkeypatch.setattr(r,'_model_settlement_read',after)
 yield
 flush()
