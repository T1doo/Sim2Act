from pathlib import Path
import hashlib,json,sqlite3,statistics,time
from sim2act import natural_live_admission as gate,natural_spec_runtime as r,_cold_typed_native_candidate as native
from sim2act.spec_production import ProductionTrialBinding
roots={p.resolve() for p in Path('/workspace/scratch/expected-post-actual-shadow-8c794051-20261031').glob('*/prefix/fixture.db')};assert len(roots)==1;db=roots.pop();digest=hashlib.sha256(db.read_bytes()).hexdigest()
with sqlite3.connect(db.as_uri()+'?mode=ro',uri=True) as c:
 c.execute('PRAGMA query_only=ON');body,=c.execute('SELECT snapshot FROM delivery_graph_requests WHERE kind=? AND request_key=?',(gate.SCOPE,'scope')).fetchall()
contract=gate.PBTrialContract.model_validate(json.loads(body[0])['request']);binary,=Path('/workspace/scratch/typed-slice-native-20261031').glob('*.so');backend=native.load_candidate(binary);assert backend is not None
plain=object.__new__(r._ColdGraphRead);plain.binding=ProductionTrialBinding(contract,'synthetic-data-only','synthetic-pb-production-shape');plain._accounted_frontier=None;plain.phase='post';plain.role_limits={'trial':gate._limits(contract)};plain.inputs={'raw_caps':contract.caps.__dict__,'raw_key':next(iter(contract.__dict__))};plain._typed_native_candidate=None
selected=object.__new__(r._ColdGraphRead);vars(selected).update(vars(plain));selected._typed_native_candidate=backend
assert plain.input_bytes()==selected.input_bytes();assert backend.native_calls>0
records=[]
for pair in range(6):
 for name,graph in ((('python',plain),('candidate',selected)) if pair%2==0 else (('candidate',selected),('python',plain))):
  a=time.monotonic_ns();cpu=time.thread_time_ns()
  for _ in range(1000):graph.input_bytes(_snapshot_values=True)
  records.append(dict(pair=pair,name=name,wall_ns=time.monotonic_ns()-a,thread_ns=time.thread_time_ns()-cpu))
 assert plain.input_bytes()==selected.input_bytes()
ratios=[]
for pair in range(6):
 b=next(x for x in records if x['pair']==pair and x['name']=='python');a=next(x for x in records if x['pair']==pair and x['name']=='candidate');ratios.append(dict(pair=pair,wall_ratio=a['wall_ns']/b['wall_ns'],cpu_ratio=a['thread_ns']/b['thread_ns'],wall_saved_ns_per_call=(b['wall_ns']-a['wall_ns'])/1000))
assert hashlib.sha256(db.read_bytes()).hexdigest()==digest
out=Path('/workspace/scratch/contract-slice-pair-20261031.json');out.write_text(json.dumps(dict(classification='ACTUAL_SYNTHETIC_PB_CONTRACT_PURE_INPUT_BYTES_METHOD_NO_GRAPH_GUARD_OR_G1',records=records,pairs=ratios,median_wall_ratio=statistics.median(x['wall_ratio'] for x in ratios),median_cpu_ratio=statistics.median(x['cpu_ratio'] for x in ratios),median_saved_ns_per_call=statistics.median(x['wall_saved_ns_per_call'] for x in ratios),native_calls=backend.native_calls,python_fallbacks=backend.python_calls,reasons=backend.reasons,contract_model_dump_bytes=len(json.dumps(contract.model_dump())),private_database_sha256=digest,private_database_unchanged=True,mock_calls=0,real_model_calls=0,binary_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),limits='Fixed original data method, alternating real-clock pairs. Pure graph data shell has no Worker/Graph guard/SQL/authority; no whole G1 extrapolation. Complete old C pickle bytes checked before/after each pair including surrounding raw caps/key aliases. All dynamic validation remains outside this slice.'),indent=2)+'\n');print(out.read_text())
