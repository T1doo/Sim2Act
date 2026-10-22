"""Read sealed synthetic prefix once; no Store/API/Worker/sender/HTTP."""
from pathlib import Path
import hashlib,json,sqlite3,statistics,time
from sim2act import _cold_base_segment as segment
from sim2act import _cold_policy_segment as schema
from sim2act import natural_live_admission as gate
from sim2act import production_trial_policy as policy
from sim2act import pb_natural_specs as pb
from sim2act import pb_natural_uses as use
from sim2act._cold_typed_stream import _Comparison
from sim2act.contracts import FrozenRunContract

source=Path('/workspace/sim2act-row-pair-20261022/window1/run/test_final_row_native_pair0/prefix/fixture.db')
out=Path('/workspace/sim2act-base-qualification-20261022/final')
before=hashlib.sha256(source.read_bytes()).hexdigest(); connection=sqlite3.connect('file:'+str(source)+'?mode=ro&immutable=1',uri=True)
models=[]; origins=[]
def add(kind, raw, origin):
 model=kind.model_validate_json(json.dumps(raw)); models.append((kind,model,model.model_dump(warnings=False)));origins.append(dict(origin=origin,kind=kind.__name__,source_json_bytes=len(json.dumps(raw))))
try:
 for kind,snapshot in connection.execute("select kind,snapshot from delivery_graph_requests where kind in ('natural-live-trial.v1.scope','uninstalled-production-trial-journal.v1','pb_natural_spec_extract','pb_natural_use') order by kind"):
  value=json.loads(snapshot)
  if kind=='natural-live-trial.v1.scope': add(gate.PBTrialContract,value['request'],kind)
  elif kind=='uninstalled-production-trial-journal.v1': add(policy.Ledger,value['response']['ledger'],kind)
  elif kind=='pb_natural_spec_extract':add(pb.ExtractInput,value['request'],kind)
  else:add(use.CommitInput,value['request'],kind)
 for rid,snapshot in connection.execute('select run_id,snapshot from run_contracts order by run_id'):
  add(FrozenRunContract,json.loads(snapshot),'run_contracts:'+rid)
finally:connection.close()
assert before==hashlib.sha256(source.read_bytes()).hexdigest()
def old():
 comparison=_Comparison(gate._trial_typed_nested_classes())
 for _,model,_ in models:comparison.validate_model(model)
 kinds={type(m) for m,_,_ in comparison.models.values()}
 return comparison.standard_serializers() and all(schema._fixed_schema(kind) for kind in kinds)
def candidate():return segment.fixed_serializers(models) and segment.serializers_current()
assert old() and candidate()
gate._trial_typed_values(models)
samples=[[],[]]
for turn in range(8):
 for index in ((0,1) if turn%2==0 else (1,0)):
  start=time.thread_time()
  for _ in range(40):assert (old if index==0 else candidate)()
  samples[index].append(time.thread_time()-start)
assert before==hashlib.sha256(source.read_bytes()).hexdigest()
result=dict(scope='actual prior complete configured prefix model cohort; qualifier only, not G0, not full tail',source_sha256=before,source_unchanged=True,origins=origins,models=len(models),kinds=len(segment._model_kinds(models)),iterations_per_round=40,rounds=8,old=samples[0],candidate_including_catalog_guard=samples[1],old_median=statistics.median(samples[0]),candidate_median=statistics.median(samples[1]),model_calls=0,Mock=0,Worker=0,business_http=0)
(out/'sealed-qualification-cpu.json').write_text(json.dumps(result,indent=2)+'\n'); print(json.dumps(result,indent=2))
